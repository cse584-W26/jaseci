"""PostgresBackend bodies.

Postgres L3 anchor store: process-cached pooled connection + 4-table schema
(anchors / anchors_quarantine / schema_meta / aliases, `data JSONB`), mirroring
SqliteMemory/MongoBackend semantics. Reads/CRUD/batch_get (P2), OCC apply()
(P3, carried forward per the locked port's occDecision — the ChangeSet/
WriteIntent/ApplyReport contract this targets is unchanged, so the merge-write
+ read-set-OCC design needs no redesign here, only path adaptation), and the
operator surface (P4: quarantine/alias/recover/fsck) all land together in this
port pass; `_process_cache`-backed pool sharing (perf(pg-l3): process-cache
connection pool per DSN) is folded in from day one, not deferred."""

import atexit;
import threading;
import from jaclang.scale._optdeps.psycopg { ConnectionPool, TransactionStatus, Jsonb }
import from jaclang.runtimelib.exceptions { WriteConflict }

# Guards first-build of a process-cached pool (postinit runs in
# asyncio.to_thread workers; an unguarded check-then-set would leak a
# second open pool on a first-request race).
glob _pg_pool_build_lock = threading.Lock(),
     # Postgres db_format_version — mirrors SqliteMemory's SQLITE_DB_FORMAT_VERSION.
     PG_DB_FORMAT_VERSION: int = 1,
     # Columns read on every anchor load, in a fixed order shared by all read paths.
     _READ_COLS: str = "type, arch_module, arch_type, fingerprint, data, format_version";

"""SQL to create the 4 tables (idempotent). Mirrors SqliteMemory's schema with
`data JSONB` and a `reason_code` column on quarantine (Mongo vocabulary)."""
glob _SCHEMA_SQL: list[str] = [
         """
    CREATE TABLE IF NOT EXISTS anchors (
        id              TEXT PRIMARY KEY,
        type            TEXT NOT NULL,
        arch_module     TEXT,
        arch_type       TEXT,
        fingerprint     TEXT,
        data            JSONB NOT NULL,
        format_version  INTEGER NOT NULL DEFAULT 1,
        updated_at      TEXT
    )
    """,
         """
    CREATE TABLE IF NOT EXISTS anchors_quarantine (
        id                   TEXT PRIMARY KEY,
        type                 TEXT,
        arch_module          TEXT,
        arch_type            TEXT,
        fingerprint          TEXT,
        data                 JSONB,
        error                TEXT,
        reason_code          TEXT,
        quarantined_at       TEXT,
        from_format_version  INTEGER
    )
    """,
         """
    CREATE TABLE IF NOT EXISTS schema_meta (
        key   TEXT PRIMARY KEY,
        value TEXT
    )
    """,
         """
    CREATE TABLE IF NOT EXISTS aliases (
        old_name    TEXT PRIMARY KEY,
        new_name    TEXT NOT NULL,
        created_at  TEXT
    )
    """
     ];


"""Attach a process-cached bounded connection pool, bootstrapping the schema
once per pool build (idempotent: CREATE TABLE IF NOT EXISTS + ON CONFLICT).

ScaleTieredMemory constructs a fresh PostgresBackend per request; without the
cache each request opened a new ConnectionPool (min_size sessions + schema
bootstrap) and tore it down at ctx.close(). Mirrors the mongo client's
_process_cache pattern (glob'd in memory_hierarchy.jac, in scope here without
an import — same module). The pool (not a single shared connection) is
required because the inherited async wrappers run sync methods in threads
concurrently."""
impl PostgresBackend.postinit -> None {
    self.l3_fetch_count = 0;
    self.__mem__ = {};
    key = f"pg_pool::{self.dsn}::{self.pool_min}::{self.pool_max}";
    pool = _process_cache.get(key);
    if pool is None {
        with _pg_pool_build_lock {
            pool = _process_cache.get(key);
            if pool is None {
                pool = ConnectionPool(
                    self.dsn, min_size=self.pool_min, max_size=self.pool_max, open=True
                );
                conn: any = pool.getconn();
                try {
                    for stmt in _SCHEMA_SQL {
                        conn.execute(stmt);
                    }
                    conn.execute(
                        "INSERT INTO schema_meta (key, value) "
                        "VALUES ('db_format_version', %s) "
                        "ON CONFLICT (key) DO NOTHING",
                        (str(PG_DB_FORMAT_VERSION), )
                    );
                    conn.commit();
                } finally {
                    pool.putconn(conn);
                }
                _process_cache[key] = pool;
                # Close at process exit (nobody else will: per-request
                # close() only drops the local ref), so shutdown doesn't
                # trip ConnectionPool.__del__ during interpreter teardown.
                atexit.register(pool.close);
            }
        }
    }
    self.__pool__ = pool;
}


"""Drop this backend's reference to the shared pool. The pool is process-cached
(see postinit) and stays open for the process lifetime — per-request
ScaleTieredMemory.close must not tear it down. Mirrors RedisBackend.close.
Flushing is the runtime's job (commit -> apply); close must not write."""
impl PostgresBackend.close -> None {
    self.__pool__ = None;
}


# =============================================================================
# Read-path helpers (module-level, mirroring the mongo backend's free fns)
# =============================================================================
"""Serialize an anchor to the column tuple for the anchors table. Mirrors
SqliteMemory._anchor_to_row, but leaves `data` a dict (Jsonb-wrapped at the
call site) instead of a JSON string — Postgres stores jsonb, not text."""
def _pg_anchor_to_row(anchor: Anchor) -> tuple {
    data = Serializer.serialize(anchor, include_type=True);
    anchor_type = type(anchor).__name__;
    arch_module: (str | None) = None;
    arch_type: (str | None) = None;
    fingerprint: (str | None) = None;
    if anchor.is_populated() and anchor.archetype is not None {
        arch = anchor.archetype;
        arch_module = type(arch).__module__;
        arch_type = type(arch).__name__;
        fp = type(arch)?.__jac_fingerprint__;
        fingerprint = fp if isinstance(fp, str) and fp else None;
    }
    return (
        anchor_type,
        arch_module,
        arch_type,
        fingerprint,
        data,
        PG_DB_FORMAT_VERSION,
        datetime.now(timezone.utc).isoformat()
    );
}


"""Move a row that failed to load into anchors_quarantine (never dropped),
tagging it with a machine-readable `reason_code` (Mongo vocabulary). Mirrors
SqliteMemory._quarantine's insert+delete. `manage_txn=True` commits the
caller's connection (read-path healer); apply() will pass False so the
quarantine rides its transaction. `delete_live=True` removes the live anchor
row (deser-failure path, mirroring _quarantine); dangling-ref recording passes
False since it must NOT delete a row that may still be a live referent
(SqliteMemory._record_dangling is insert-only). Never raises.

ponytail: no NodeAnchor->edge cascade (SqliteMemory._quarantine memory.impl.jac
:276-376). No suite test exercises it, and it only fires when schema drift
removes a node type that still has live edges citing it. Port that cascade
here (data->>'source'/'target' match + jsonb edge-array strip) if a
drift-removes-node scenario needs orphan-edge cleanup."""
def _pg_quarantine(
    conn: any,
    id_str: str,
    anchor_type: any,
    arch_module: any,
    arch_type: any,
    fingerprint: any,
    data: any,
    error: str,
    reason_code: str = 'DESER_ERROR',
    from_format_version: any = None,
    manage_txn: bool = True,
    delete_live: bool = True
) {
    try {
        now_ts = datetime.now(timezone.utc).isoformat();
        conn.execute(
            """
            INSERT INTO anchors_quarantine
                (id, type, arch_module, arch_type, fingerprint, data,
                 error, reason_code, quarantined_at, from_format_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                type=EXCLUDED.type, arch_module=EXCLUDED.arch_module,
                arch_type=EXCLUDED.arch_type, fingerprint=EXCLUDED.fingerprint,
                data=EXCLUDED.data, error=EXCLUDED.error,
                reason_code=EXCLUDED.reason_code,
                quarantined_at=EXCLUDED.quarantined_at,
                from_format_version=EXCLUDED.from_format_version
            """,
            (
                id_str,
                anchor_type,
                arch_module,
                arch_type,
                fingerprint,
                Jsonb(cast(dict[str, object], data)) if data is not None else None,
                error,
                reason_code,
                now_ts,
                from_format_version
            )
        );
        if delete_live {
            conn.execute("DELETE FROM anchors WHERE id = %s", (id_str, ));
        }
        if manage_txn {
            conn.commit();
        }
    } except Exception as e {
        logger.error(f"PostgresBackend: failed to quarantine anchor {id_str}: {e}");
    }
}


"""Deserialize one anchor row. On failure move it to quarantine (classifying
the reason like MongoBackend._load_anchor) and return None; on success snapshot
field hashes and return the anchor. `pool` is used only to open a short-lived
connection for the quarantine write, so this stays decoupled from whatever
connection produced the row. Mirrors SqliteMemory.get :773-841."""
def _pg_load_row(
    pool: any,
    id_str: str,
    anchor_type: any,
    arch_module: any,
    arch_type: any,
    fingerprint: any,
    data: any,
    fmt_version: any
) -> (Anchor | None) {
    # Fingerprint drift is informational only — the serializer tolerates
    # added/removed fields; a type change surfaces as a deserialize failure.
    if arch_module and arch_type and fingerprint {
        cls = Serializer._get_class(cast(str, arch_module), cast(str, arch_type));
        current_fp = cls?.__jac_fingerprint__ if cls else None;
        if current_fp and current_fp != fingerprint {
            logger.info(
                f"PostgresBackend: schema drift on {arch_module}.{arch_type} "
                f"(stored={fingerprint}, current={current_fp}, id={id_str}); "
                "attempting best-effort load."
            );
        }
    }
    try {
        anchor = (
            Serializer.deserialize(cast(dict[str, object], data))
                if data is not None
                else None
        );
    } except Exception as e {
        logger.warning(
            f"PostgresBackend: failed to deserialize anchor {id_str} "
            f"({arch_module}.{arch_type}): {type(e).__name__}: {e}. "
            "Moving to anchors_quarantine."
        );
        conn = pool.getconn();
        try {
            _pg_quarantine(
                conn,
                id_str,
                anchor_type,
                arch_module,
                arch_type,
                fingerprint,
                data,
                f"deserialize error: {type(e).__name__}: {e}",
                'DESER_ERROR',
                from_format_version=fmt_version
            );
        } finally {
            pool.putconn(conn);
        }
        return None;
    }
    if anchor is None {
        cls_resolved = (
            Serializer._get_class(cast(str, arch_module), cast(str, arch_type))
                if (arch_module and arch_type)
                else None
        );
        if cls_resolved is None {
            reason = f"class {arch_module}.{arch_type} unresolvable";
            code = 'CLASS_MISSING';
        } else {
            reason = f"archetype field deserialization failed: {arch_module}.{arch_type}";
            code = 'FIELD_RECONSTRUCT';
        }
        logger.warning(
            f"PostgresBackend: {reason} (anchor {id_str}). "
            "Moving to anchors_quarantine."
        );
        conn = pool.getconn();
        try {
            _pg_quarantine(
                conn,
                id_str,
                anchor_type,
                arch_module,
                arch_type,
                fingerprint,
                data,
                reason,
                code,
                from_format_version=fmt_version
            );
        } finally {
            pool.putconn(conn);
        }
        return None;
    }
    snapshot_field_hashes(cast(Anchor, anchor));
    return cast(Anchor, anchor);
}


# =============================================================================
# Write-path helpers — apply() merge-write (P3, module-level free fns)
# =============================================================================
"""Serialize an object to canonical JSON for equality comparison (access
merge). Local clone of memory.impl.jac's module-private `_canonical_json`.
ponytail: a 4-line clone over importing another module's `_`-private free def
(not declared in memory.jac, so cross-module resolution is fragile)."""
def _pg_canonical_json(val: object) -> str {
    return json.dumps(
        Serializer.serialize(val, include_type=True),
        sort_keys=True,
        default=lambda v: any : str(v)
    );
}


"""Blind upsert of one anchor row (INSERT ... ON CONFLICT (id) DO UPDATE).
`row` is a tuple from `_pg_anchor_to_row`; the jsonb `data` col is Jsonb-wrapped
here. Same statement as put(); the merge path calls it for both the merged and
the full-write branch."""
def _pg_upsert(conn: any, key: str, row: any) {
    conn.execute(
        """
        INSERT INTO anchors
            (id, type, arch_module, arch_type, fingerprint,
             data, format_version, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            type=EXCLUDED.type, arch_module=EXCLUDED.arch_module,
            arch_type=EXCLUDED.arch_type, fingerprint=EXCLUDED.fingerprint,
            data=EXCLUDED.data, format_version=EXCLUDED.format_version,
            updated_at=EXCLUDED.updated_at
        """,
        (key, row[0], row[1], row[2], row[3], Jsonb(row[4]), row[5], row[6])
    );
}


"""Merge-aware write (cross-process safety, issue #5446): SELECT ... FOR UPDATE
the stored row, apply this unit's edge delta / dirty fields / access / topology
onto the DB-current row, and upsert the merged result. A concurrent writer's
edges survive because the delta merges onto the DB-current list, not ours; the
row lock serializes two writers on the same node, so the second reads the
first's committed edges (the Postgres equivalent of sqlite's BEGIN IMMEDIATE).
Line-for-line port of SqliteMemory._merge_write; the one divergence is `data`
comes back a dict (psycopg auto-loads jsonb), so no json.loads."""
def _pg_merge_write(conn: any, intent: WriteIntent) -> None {
    anchor = intent.anchor;
    key = str(anchor.id);
    raw_row: any = conn.execute(
        f"SELECT {_READ_COLS} FROM anchors WHERE id = %s FOR UPDATE", (key, )
    ).fetchone();
    stored: (Anchor | None) = None;
    if raw_row {
        row_type = cast(str, raw_row[0]);
        row_arch_module = cast((str | None), raw_row[1]);
        row_arch_type = cast((str | None), raw_row[2]);
        row_fingerprint = cast((str | None), raw_row[3]);
        row_data = raw_row[4];
        row_fmt = cast(int, raw_row[5]);
        try {
            stored = cast(
                (Anchor | None),
                Serializer.deserialize(cast(dict[str, object], row_data))
            );
        } except Exception as de {
            logger.warning(
                f"PostgresBackend.apply: stored anchor {key} unreadable "
                f"({type(de).__name__}: {de}); quarantining and "
                "overwriting with in-memory version."
            );
            # apply() holds the transaction: the quarantine must ride it,
            # not commit mid-flush (manage_txn=False).
            _pg_quarantine(
                conn,
                key,
                row_type,
                row_arch_module,
                row_arch_type,
                row_fingerprint,
                row_data,
                f"apply-time deserialize: {type(de).__name__}: {de}",
                'DESER_ERROR',
                from_format_version=row_fmt,
                manage_txn=False
            );
            stored = None;
        }
    }

    if stored is not None and stored.is_populated() {
        stored_anchor = cast(Anchor, stored);
        changed = False;
        # Edge-delete repair: the intent's anchor is a STUB endpoint ref
        # (EdgeAnchor.__getstate__ persists endpoints via make_stub), so it
        # exposes no .edges/.archetype/.access — touching them triggers
        # Anchor.populate() and raises "not a valid reference". The stored node
        # IS this same node fully loaded, so merge the intent's recorded id
        # deltas onto its DB-current edge list and decide Root/prune from it.
        # Self-contained: a stub carries no topology/access/fields to merge.
        if (
            isinstance(stored_anchor, NodeAnchor)
            and isinstance(anchor, NodeAnchor)
            and not anchor.is_populated()
        ) {
            edges_added = set(intent.edges_added);
            edges_removed = set(intent.edges_removed);
            if edges_added or edges_removed {
                if intent.cas_version is not None
                and stored_anchor.version != intent.cas_version {
                    raise WriteConflict(
                        anchor_id=anchor.id,
                        expected_version=intent.cas_version,
                        actual_version=stored_anchor.version
                    );
                }
                stored_set = set(e.id for e in stored_anchor.edges);
                # ponytail: added ids without a stored edge object are dropped
                # (an edge-add always carries a populated anchor); edge-delete
                # repair only removes, so `merged_ids` stays a subset of stored.
                merged_ids = (stored_set | edges_added) - edges_removed;
                edge_by_id = {e.id: e for e in stored_anchor.edges};
                stored_anchor.edges = [
                    edge_by_id[eid]
                    for eid in merged_ids
                    if eid in edge_by_id
                ];
                stored_anchor.version = stored_anchor.version + 1;
                if (
                    not stored_anchor.edges
                    and not isinstance(stored_anchor.archetype, Root)
                ) {
                    conn.execute("DELETE FROM anchors WHERE id = %s", (key, ));
                    return;
                }
                _pg_upsert(conn, key, _pg_anchor_to_row(stored_anchor));
            }
            return;
        }
        # Merge edge lists: apply this unit's delta to the DB-current list so a
        # concurrent writer's edges survive.
        if (
            isinstance(stored_anchor, NodeAnchor)
            and isinstance(anchor, NodeAnchor)
            and stored_anchor.edges != anchor.edges
        ) {
            delta = anchor.edge_delta();
            if delta is not None {
                edges_added = set(delta[0]);
                edges_removed = set(delta[1]);
                # Read-set OCC: conflict only if this request READ a traversal
                # from this node (cas_version set) and its stored version moved
                # since. A blind append (cas_version None) merges lock-free.
                if (edges_added or edges_removed)
                and intent.cas_version is not None
                and stored_anchor.version != intent.cas_version {
                    raise WriteConflict(
                        anchor_id=anchor.id,
                        expected_version=intent.cas_version,
                        actual_version=stored_anchor.version
                    );
                }
                stored_set = set(e.id for e in stored_anchor.edges);
                merged_ids = (stored_set | edges_added) - edges_removed;
                edge_by_id = {e.id: e for e in stored_anchor.edges};
                edge_by_id.update({e.id: e for e in anchor.edges});
                stored_anchor.edges = [
                    edge_by_id[eid]
                    for eid in merged_ids
                    if eid in edge_by_id
                ];
                if edges_added or edges_removed {
                    # Advance from the STORED version (monotonic regardless of
                    # who wrote); re-baseline the in-memory anchor.
                    new_version = stored_anchor.version + 1;
                    stored_anchor.version = new_version;
                    anchor.version = new_version;
                }
            } else {
                stored_anchor.edges = anchor.edges;
            }
            if (not stored_anchor.edges and not isinstance(anchor.archetype, Root)) {
                conn.execute("DELETE FROM anchors WHERE id = %s", (key, ));
                return;
            }
            changed = True;
        }
        # Topology index is a derived adjacency cache on root NodeAnchors,
        # updated by edges anywhere in the subtree -- not an archetype field,
        # so the edge merge and field merge don't catch it (GTI invariant).
        if (
            isinstance(stored_anchor, NodeAnchor)
            and isinstance(anchor, NodeAnchor)
            and anchor.topology_index_data != stored_anchor.topology_index_data
        ) {
            stored_anchor.topology_index_data = anchor.topology_index_data;
            # Parity with SqliteMemory._merge_write (upstream 46ed1cb12): the
            # blob is refreshed in place, so drop any decoded-index cache.
            # Benign today (deserialize returns a fresh anchor with the cache
            # already cleared) but load-bearing if the serializer ever reuses
            # identity-mapped anchors.
            stored_anchor._topology_index_cache = None;
            changed = True;
        }
        if _pg_canonical_json(stored_anchor.access) != _pg_canonical_json(
            anchor.access
        ) {
            stored_anchor.access = anchor.access;
            changed = True;
        }
        # Merge dirty fields. A full write (create intent) copies every field;
        # otherwise only the fields the collect pass flagged.
        arch = anchor.archetype;
        fields = set(get_field_types(type(arch)).keys())
            if (intent.is_create() and arch is not None)
            else set(intent.fields);
        if fields and stored_anchor.archetype is not None and arch is not None {
            for field in fields {
                try {
                    setattr(stored_anchor.archetype, field, getattr(arch, field));
                } except AttributeError {
                    continue;
                }
            }
            changed = True;
        }
        if changed {
            _pg_upsert(conn, key, _pg_anchor_to_row(stored_anchor));
        }
    } else {
        # No stored row (or stored is a stub): write the anchor whole. A
        # transient class raises AttributeError/ModuleNotFoundError here,
        # bubbling to apply()'s ladder (failed + poisoned).
        _pg_upsert(conn, key, _pg_anchor_to_row(anchor));
    }
}


"""Execute one intent: deletes remove the row (a nonexistent row is a no-op
success); everything else is a merge-aware write against the stored row."""
def _pg_apply_one(conn: any, intent: WriteIntent) -> None {
    if intent.is_delete() {
        conn.execute("DELETE FROM anchors WHERE id = %s", (str(intent.anchor.id), ));
        return;
    }
    _pg_merge_write(conn, intent);
}


"""Per-intent dispatch seam for apply()'s ladder. Subclasses (PostgresRelBackend)
extend the flush unit here -- e.g. edge-row maintenance in the same
transaction -- without copying apply()'s error/rollback machinery."""
impl PostgresBackend._apply_intent(conn: Any, intent: WriteIntent) -> None {
    _pg_apply_one(conn, intent);
}


# =============================================================================
# Operator-surface helpers — quarantine recovery / aliases / fsck (P4)
# =============================================================================
"""Load every DB-resident alias into the in-process Serializer registry so
CLI-added rescues apply on the next read. Mirrors SqliteMemory's
_load_db_aliases; DB entries win over decorator-declared ones."""
def _pg_load_db_aliases(conn: any) -> int {
    rows: any = conn.execute("SELECT old_name, new_name FROM aliases").fetchall();
    count = 0;
    for (old_name, new_name) in rows {
        if isinstance(old_name, str) and isinstance(new_name, str) {
            Serializer._aliases[old_name] = new_name;
            count += 1;
        }
    }
    return count;
}


"""File a dangling reference under DANGLING_REF (shared by the read-path healer
hook and fsck --repair). `manage_txn=False` lets fsck batch it into its unit of
work. Port of SqliteMemory._record_dangling; reason_code='DANGLING_REF' is the
marker is_recoverable_quarantine EXCLUDES. Never raises (via _pg_quarantine)."""
def _pg_record_dangling(
    conn: any, missing_id: any, referrer_id: any, kind: str, manage_txn: bool = True
) {
    anchor_type = 'EdgeAnchor' if kind == 'edge' else 'NodeAnchor';
    ref_str = str(referrer_id) if referrer_id is not None else '?';
    mid = str(missing_id);
    err = f"DANGLING_REF: missing {kind} {mid} cited by {ref_str}";
    _pg_quarantine(
        conn,
        mid,
        anchor_type,
        None,
        'DANGLING_REF',
        None,
        {'referrer': ref_str, 'kind': kind},
        err,
        'DANGLING_REF',
        from_format_version=None,
        manage_txn=manage_txn,
        delete_live=False
    );
}


"""Strip `remove_ids` from one node row's data.edges in place; return the
number of citations removed. Caller owns the transaction. Port of
SqliteMemory._prune_node_edges — data is a dict (JSONB auto-loaded), so no
json.loads/dumps; the merged dict is Jsonb-wrapped on write-back."""
def _pg_prune_node_edges(conn: any, node_id: str, remove_ids: set[str]) -> int {
    row: any = conn.execute(
        "SELECT data FROM anchors WHERE id = %s", (node_id, )
    ).fetchone();
    if not row {
        return 0;
    }
    d = row[0];
    if not isinstance(d, dict) {
        return 0;
    }
    old_edges: list = cast(list, d.get('edges') or []);
    new_edges: list = [
        e
        for e in old_edges
        if str(e) not in remove_ids
    ];
    if len(new_edges) == len(old_edges) {
        return 0;
    }
    d['edges'] = new_edges;
    conn.execute(
        "UPDATE anchors SET data = %s WHERE id = %s",
        (Jsonb(cast(dict[str, object], d)), node_id)
    );
    return len(old_edges) - len(new_edges);
}


"""Attempt to re-deserialize one quarantined row, re-stamped with the live
class's identity + fingerprint on success, then moved back to the live table.
Returns (ok, reason). Row column order matches the recover_one/all SELECT:
(id, type, arch_module, arch_type, fingerprint, data, error, quarantined_at,
from_format_version). Port of SqliteMemory._sqlite_attempt_recover; data is a
dict (JSONB), so no json.loads, and _pg_anchor_to_row already re-stamps live
class metadata + fingerprint (so the re_data_json dance is unnecessary)."""
def _pg_attempt_recover(conn: any, row: any) -> tuple {
    row_id = cast(str, row[0]);
    anchor_type = row[1];
    arch_module = row[2];
    arch_type = row[3];
    data = row[5];
    if data is None {
        return (False, "no data payload stored");
    }
    try {
        anchor = Serializer.deserialize(cast(dict[str, object], data));
    } except Exception as e {
        return (False, f"deserialize raised: {type(e).__name__}: {e}");
    }
    if anchor is None {
        return (False, f"class {arch_module}.{arch_type} still unresolvable");
    }
    # Re-stamp with live class metadata (via _pg_anchor_to_row) and move the row
    # from quarantine back into the live table.
    _pg_upsert(conn, row_id, _pg_anchor_to_row(cast(Anchor, anchor)));
    conn.execute("DELETE FROM anchors_quarantine WHERE id = %s", (row_id, ));
    # Re-link: recovering an EdgeAnchor that was cascade-quarantined means the
    # connected node(s)' data.edges was stripped. Re-add the edge id to the
    # source (always) and, for undirected edges, the target.
    if anchor_type == 'EdgeAnchor' and isinstance(data, dict) {
        source_id = data.get('source');
        target_id = data.get('target');
        is_undirected = bool(data.get('is_undirected', False));
        relink_ids: list = [
            n
            for n in [source_id]
            if n
        ];
        if is_undirected and target_id and target_id != source_id {
            relink_ids.append(target_id);
        }
        for node_id in relink_ids {
            node_row: any = conn.execute(
                "SELECT data FROM anchors WHERE id = %s AND type = 'NodeAnchor'",
                (node_id, )
            ).fetchone();
            if node_row {
                try {
                    node_data = node_row[0];
                    edges = node_data.get('edges', []);
                    if row_id not in edges {
                        edges.append(row_id);
                        node_data['edges'] = edges;
                        conn.execute(
                            "UPDATE anchors SET data = %s WHERE id = %s",
                            (Jsonb(cast(dict[str, object], node_data)), node_id)
                        );
                    }
                } except Exception as relink_err {
                    logger.warning(
                        f"PostgresBackend: recover re-link of edge {row_id} "
                        f"to node {node_id} failed: {relink_err}"
                    );
                }
            } else {
                logger.warning(
                    f"PostgresBackend: recover re-link of edge {row_id} "
                    f"to node {node_id} skipped: node not found in live anchors"
                );
            }
        }
    }
    return (True, "recovered");
}


# =============================================================================
# Memory interface — reads / CRUD / batch_get (P2)
# =============================================================================
"""The pool is open (postinit opens it, raising if PG is unreachable), so a
live pool is a live backend."""
impl PostgresBackend.is_available -> bool {
    return self.__pool__ is not None;
}

"""Load an anchor by id from Postgres. Cold every call — L3 keeps no working
set (L1/L2 own the identity map). A row that fails to load is quarantined,
not returned. Mirrors SqliteMemory.get."""
impl PostgresBackend.get(id: UUID) -> (Anchor | None) {
    conn = self.__pool__.getconn();
    # autocommit for the read: no implicit txn, so the pool's return check
    # finds the connection IDLE instead of INTRANS - saves a ROLLBACK
    # round-trip per call. Restored before putconn so write checkouts keep
    # their transactional default.
    conn.autocommit = True;
    try {
        row: any = conn.execute(
            f"SELECT {_READ_COLS} FROM anchors WHERE id = %s", (str(id), )
        ).fetchone();
    } finally {
        conn.autocommit = False;
        self.__pool__.putconn(conn);
    }
    if row is None {
        return None;
    }
    self.l3_fetch_count += 1;
    return _pg_load_row(
        self.__pool__, str(id), row[0], row[1], row[2], row[3], row[4], row[5]
    );
}

"""Admin/seeding upsert. The runtime never calls l3.put() for graph mutations
(those flow through commit -> apply); a direct put is an out-of-band write.
Non-persistent / unpopulated anchors are skipped, matching SqliteMemory."""
impl PostgresBackend.put(anchor: Anchor) -> None {
    if not anchor.persistent or not anchor.is_populated() {
        return;
    }
    conn = self.__pool__.getconn();
    try {
        row: any = _pg_anchor_to_row(anchor);
        conn.execute(
            """
            INSERT INTO anchors
                (id, type, arch_module, arch_type, fingerprint,
                 data, format_version, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                type=EXCLUDED.type, arch_module=EXCLUDED.arch_module,
                arch_type=EXCLUDED.arch_type, fingerprint=EXCLUDED.fingerprint,
                data=EXCLUDED.data, format_version=EXCLUDED.format_version,
                updated_at=EXCLUDED.updated_at
            """,
            (
                str(anchor.id),
                row[0],
                row[1],
                row[2],
                row[3],
                Jsonb(row[4]),
                row[5],
                row[6]
            )
        );
        conn.commit();
    } except (AttributeError, ModuleNotFoundError) {
        # Transient/unserializable classes (e.g. test-local archetypes) stay
        # absent, matching SqliteMemory's legacy skip.
        conn.rollback();
    } except Exception as e {
        conn.rollback();
        logger.warning(
            f"PostgresBackend.put: failed to persist {anchor.id}: "
            f"{type(e).__name__}: {e}"
        );
    } finally {
        self.__pool__.putconn(conn);
    }
}

"""Forget backend-local cache state for an anchor. L3 keeps no working set
(L1/L2 own the identity map), so this is a no-op -- mirrors MongoBackend.delete
(memory_hierarchy.mongo.impl.jac) and SqliteMemory.delete's __mem__ pop.
Durable removal happens ONLY via apply()'s ordered delete intents, in
dependency order with the edge-list repairs that must precede it -- never
inline (issue #6587). A durable DELETE here would corrupt on two paths:
TieredMemory.delete evicting mid-request outside apply()'s txn, and
TieredMemory.abort dropping caches for every dirty anchor on a failed request
-- with PG that would permanently delete merely mutated rows."""
impl PostgresBackend.delete(id: UUID) -> None { }

impl PostgresBackend.`has(id: UUID) -> bool {
    conn = self.__pool__.getconn();
    conn.autocommit = True;  # read-only: skip txn + return-rollback trip
    try {
        row = conn.execute(
            "SELECT 1 FROM anchors WHERE id = %s", (str(id), )
        ).fetchone();
        return row is not None;
    } finally {
        conn.autocommit = False;
        self.__pool__.putconn(conn);
    }
}

"""Scan every persisted anchor (an L3 with no working set can't answer from
memory the way SqliteMemory does), yielding those that load and pass filter."""
impl PostgresBackend.query(
    filter: (Callable[[Anchor], bool] | None) = None
) -> Generator[Anchor, None, None] {
    conn = self.__pool__.getconn();
    conn.autocommit = True;  # read-only: skip txn + return-rollback trip
    try {
        rows: any = conn.execute(f"SELECT id, {_READ_COLS} FROM anchors").fetchall();
    } finally {
        conn.autocommit = False;
        self.__pool__.putconn(conn);
    }
    for row in rows {
        r: any = row;
        anchor = _pg_load_row(
            self.__pool__, str(r[0]), r[1], r[2], r[3], r[4], r[5], r[6]
        );
        if anchor is not None and (filter is None or filter(anchor)) {
            yield anchor;
        }
    }
}

"""Yield every persisted Root via the indexed arch_type filter.

ponytail: matches anchors whose arch_type is exactly 'Root' (jac's built-in
root, which every user root is). A user-defined Root SUBCLASS would carry a
different arch_type and be missed — SqliteMemory scans all NodeAnchors and
does issubclass() to catch those. Widen to that scan if custom root types
appear."""
impl PostgresBackend.get_roots -> Generator[Root, None, None] {
    conn = self.__pool__.getconn();
    conn.autocommit = True;  # read-only: skip txn + return-rollback trip
    try {
        rows: any = conn.execute(
            f"SELECT id, {_READ_COLS} FROM anchors "
            "WHERE type = 'NodeAnchor' AND arch_type = 'Root'"
        ).fetchall();
    } finally {
        conn.autocommit = False;
        self.__pool__.putconn(conn);
    }
    for row in rows {
        r: any = row;
        anchor = _pg_load_row(
            self.__pool__, str(r[0]), r[1], r[2], r[3], r[4], r[5], r[6]
        );
        if anchor is not None and isinstance(anchor.archetype, Root) {
            yield cast(Root, anchor.archetype);
        }
    }
}

"""Find anchors by id(s) with optional filter (accepts a single UUID or an
iterable). Mirrors SqliteMemory.find."""
impl PostgresBackend.find(
    ids: (UUID | Iterable[UUID]), filter: (Callable[[Anchor], Anchor] | None) = None
) -> Generator[Anchor, None, None] {
    id_list = [ids] if isinstance(ids, UUID) else list(ids);
    for id in id_list {
        if (anchor := self.get(id)) {
            if filter is None or filter(anchor) {
                yield anchor;
            }
        }
    }
}

"""Return the first anchor among id(s) that loads and passes filter, else None."""
impl PostgresBackend.find_one(
    ids: (UUID | Iterable[UUID]), filter: (Callable[[Anchor], Anchor] | None) = None
) -> (Anchor | None) {
    id_list = [ids] if isinstance(ids, UUID) else list(ids);
    for id in id_list {
        if (anchor := self.get(id)) {
            if filter is None or filter(anchor) {
                return anchor;
            }
        }
    }
    return None;
}

"""No-op: an L3 backend has no unit of work of its own; flushing happens via
apply() driven by the runtime (TieredMemory.commit)."""
impl PostgresBackend.commit(anchor: (Anchor | None) = None) -> None { }

"""L3 keeps no in-process working set; the empty dict backs the documented
shape (the real store is the DB, reachable via query/get)."""
impl PostgresBackend.get_mem -> dict[UUID, Anchor] {
    return self.__mem__;
}

"""Fetch N anchors in ONE round-trip via `= ANY(%s)` (a list param — psycopg3
rejects `IN %s` with a tuple). Empty-list safe. Misses are simply absent from
the result. Load-bearing: without it GTI materialization degrades to N gets."""
impl PostgresBackend.batch_get(ids: list[UUID]) -> dict[UUID, Anchor] {
    result: dict[UUID, Anchor] = {};
    if not ids {
        return result;
    }
    str_ids = [str(id) for id in ids];
    conn = self.__pool__.getconn();
    conn.autocommit = True;  # read-only: skip txn + return-rollback trip
    try {
        rows: any = conn.execute(
            f"SELECT id, {_READ_COLS} FROM anchors WHERE id = ANY(%s)", (str_ids, )
        ).fetchall();
    } finally {
        conn.autocommit = False;
        self.__pool__.putconn(conn);
    }
    self.l3_fetch_count += 1;
    for row in rows {
        r: any = row;
        anchor = _pg_load_row(
            self.__pool__, str(r[0]), r[1], r[2], r[3], r[4], r[5], r[6]
        );
        if anchor is not None {
            # Materialized reads must not read back as dirty writes.
            anchor.is_updated = False;
            result[UUID(str(r[0]))] = anchor;
        }
    }
    return result;
}

"""Flush a unit of work in ONE transaction on a pooled connection.

No `self.__lock__` and no explicit BEGIN: each apply gets its own pooled
connection, psycopg opens the transaction implicitly on the first execute, and
SELECT ... FOR UPDATE row locks (inside _pg_merge_write) provide the
cross-process/thread serialization sqlite got from a shared conn + BEGIN
IMMEDIATE. Staged order is a no-op for atomicity here (one transaction is
all-or-nothing), but executing it keeps one code path with non-transactional
backends. Per-intent serialize failures are skipped (dependents poisoned);
conflicts and transaction-level failures roll the whole unit back."""
impl PostgresBackend.apply(changeset: ChangeSet) -> ApplyReport {
    apply_report = ApplyReport();
    if changeset.is_empty() {
        return apply_report;  # Nothing to flush; don't touch the pool.
    }
    conn: any = self.__pool__.getconn();
    try {
        try {
            poisoned: set[UUID] = set();
            for stage in changeset.staged() {
                for intent in stage {
                    if (deps := intent.depends_on & poisoned) {
                        # Proceeding would mint a dangling reference (e.g. a
                        # node delete after a failed edge delete).
                        dep = next(iter(deps));
                        apply_report.skipped[intent.anchor.id] = (
                            f"dependency {dep} failed"
                        );
                        poisoned.add(intent.anchor.id);
                        logger.error(
                            f"PostgresBackend.apply: skipping {intent.op.name} on "
                            f"{intent.anchor.id}: dependency {dep} failed"
                        );
                        continue;
                    }
                    try {
                        self._apply_intent(conn, intent);
                        apply_report.applied.append(intent.anchor.id);
                    } except WriteConflict as wc {
                        # OCC miss: poison like any failed write (skips
                        # dependents), carry the typed conflict so the boundary
                        # can replay. DEBUG, not ERROR: a losing racer is
                        # expected.
                        poisoned.add(intent.anchor.id);
                        apply_report.failed[intent.anchor.id] = wc.message();
                        apply_report.conflicts.append(wc);
                        logger.debug(
                            f"PostgresBackend.apply: write conflict on "
                            f"{intent.anchor.id}: {wc.message()}"
                        );
                    } except (AttributeError, ModuleNotFoundError) as se {
                        # Anchors that can't be serialized (e.g. transient test
                        # classes) are skipped, not fatal.
                        poisoned.add(intent.anchor.id);
                        apply_report.failed[intent.anchor.id] = str(se);
                    } except Exception as e {
                        poisoned.add(intent.anchor.id);
                        apply_report.failed[intent.anchor.id] = str(e);
                        logger.error(
                            f"PostgresBackend.apply: {intent.op.name} failed for "
                            f"{intent.anchor.id}: {type(e).__name__}: {e}"
                        );
                    }
                    # ponytail: no per-intent SAVEPOINT. A failed SQL statement
                    # aborts the whole psycopg txn (status INERROR); every later
                    # intent fails into failed{} too, and the INERROR guard below
                    # rolls the unit back and folds any already-applied ids into
                    # failed. psycopg's commit() on an aborted txn does NOT raise
                    # -- PG silently converts COMMIT to ROLLBACK -- so the guard,
                    # not the commit, is what stops the report from lying. Add
                    # SAVEPOINTs only if partial-apply-after-SQL-error is needed.
                }
            }
            if apply_report.conflicts {
                # OCC loser: its child/edge were written earlier in THIS
                # transaction, so a plain commit would strand them as orphans.
                # Roll the whole unit back; the request boundary replays.
                # `applied` cleared so _post_apply re-baselines nothing. The
                # rollback also undoes any in-txn quarantine (same as sqlite).
                conn.rollback();
                apply_report.applied = [];
            } elif conn.info.transaction_status == TransactionStatus.INERROR {
                # A mid-unit SQL statement aborted the txn -- e.g. a trigger
                # error, or a PG deadlock loser whose FOR UPDATE lost the lock
                # race (it surfaces on a per-intent conn.execute and is caught
                # above into failed{}). psycopg's commit() on an aborted txn does
                # NOT raise: PG silently converts COMMIT to ROLLBACK, so a plain
                # commit would report applied=[A] while 0 rows actually persist.
                # Roll back explicitly and fail every id that appeared to apply
                # -- their L1 anchors stay dirty and re-flush on a later commit,
                # never silently baselined-clean by _post_apply. (The transient-
                # class skip at the AttributeError arm above raises Python-side
                # before any SQL, leaving the txn healthy so it keeps its
                # partial-apply-and-commit -- hence the guard is on INERROR, not
                # merely on a non-empty failed{}.)
                conn.rollback();
                reason = next(iter(apply_report.failed.values()), "SQL error");
                for aid in apply_report.applied {
                    apply_report.failed[aid] = (
                        f"transaction aborted by earlier failure: {reason}"
                    );
                }
                apply_report.applied = [];
            } else {
                conn.commit();
            }
        } except Exception as te {
            # Whole-transaction failure raised by the stage machinery itself
            # (e.g. a changeset whose staged() iteration raises), NOT a per-intent
            # SQL error -- those are caught per-intent above and settled by the
            # INERROR guard. Roll back and mark every intent failed. Rollback
            # runs FIRST so state is restored even if the re-enumeration below
            # raises (e.g. a poison-tail changeset).
            conn.rollback();
            apply_report.applied = [];
            for stage in changeset.staged() {
                for intent in stage {
                    apply_report.failed[intent.anchor.id] = str(te);
                }
            }
            logger.error(f"PostgresBackend.apply: transaction rolled back: {te}");
        }
    } finally {
        self.__pool__.putconn(conn);
    }
    return apply_report;
}

"""Summary dict for `jac db inspect`. Mirrors SqliteMemory.inspect_summary;
`location` is the DSN (carries the db name for display)."""
impl PostgresBackend.inspect_summary -> dict {
    conn = self.__pool__.getconn();
    try {
        fmt_row: any = conn.execute(
            "SELECT value FROM schema_meta WHERE key='db_format_version'"
        ).fetchone();
        fmt_version = fmt_row[0] if fmt_row else '?';
        anchors_rows: any = conn.execute(
            """
            SELECT COALESCE(arch_type, '<none>'), COUNT(*)
            FROM anchors
            GROUP BY arch_type
            ORDER BY COUNT(*) DESC
            """
        ).fetchall();
        quarantine_rows: any = conn.execute(
            """
            SELECT COALESCE(arch_type, '<none>'), COUNT(*)
            FROM anchors_quarantine
            GROUP BY arch_type
            ORDER BY COUNT(*) DESC
            """
        ).fetchall();
        alias_row: any = conn.execute("SELECT COUNT(*) FROM aliases").fetchone();
        alias_count = alias_row[0];
    } finally {
        self.__pool__.putconn(conn);
    }
    return {
        'format_version': str(fmt_version),
        'anchors_total': sum(r[1] for r in anchors_rows),
        'anchors_by_type': [(r[0], r[1]) for r in anchors_rows],
        'quarantine_total': sum(r[1] for r in quarantine_rows),
        'quarantine_by_type': [(r[0], r[1]) for r in quarantine_rows],
        'aliases_total': alias_count,
        'location': self.dsn
    };
}

"""List the N most recent quarantined rows, newest-first, with the documented
str-valued keys. Mirrors SqliteMemory.list_quarantined (no reason_code in the
CLI shape)."""
impl PostgresBackend.list_quarantined(limit: int = 50) -> list {
    conn = self.__pool__.getconn();
    try {
        rows: any = conn.execute(
            """
            SELECT id, COALESCE(arch_module, '?') || '.' ||
                   COALESCE(arch_type, '?'), COALESCE(fingerprint, ''),
                   COALESCE(error, ''), COALESCE(quarantined_at, '')
            FROM anchors_quarantine
            ORDER BY quarantined_at DESC
            LIMIT %s
            """,
            (limit, )
        ).fetchall();
    } finally {
        self.__pool__.putconn(conn);
    }
    return [
        {
            'id': str(r[0]),
            'arch': str(r[1]),
            'fingerprint': str(r[2]),
            'error': str(r[3]),
            'quarantined_at': str(r[4])
        } for r in rows
    ];
}

"""Full detail of one quarantined row (by id or unique prefix). None on miss,
a {'error': 'ambiguous'} sentinel on a multi-hit prefix. Mirrors
SqliteMemory.show_quarantined; `data` is already a dict (JSONB auto-loaded)."""
impl PostgresBackend.show_quarantined(id_prefix: str) -> (dict | None) {
    conn = self.__pool__.getconn();
    try {
        rows: list = list(
            conn.execute(
                """
                SELECT id, type, arch_module, arch_type, fingerprint, data,
                       error, quarantined_at, from_format_version
                FROM anchors_quarantine
                WHERE id = %s OR id LIKE %s
                LIMIT 2
                """,
                (id_prefix, id_prefix + '%')
            ).fetchall()
        );
    } finally {
        self.__pool__.putconn(conn);
    }
    if not rows {
        return None;
    }
    if len(rows) > 1 {
        return {'error': 'ambiguous', 'count': len(rows)};
    }
    r = rows[0];
    return {
        'id': r[0],
        'type': r[1],
        'arch_module': r[2],
        'arch_type': r[3],
        'fingerprint': r[4],
        'error': r[6],
        'quarantined_at': r[7],
        'from_format_version': r[8],
        'data': r[5]
    };
}

"""Recover a single quarantined row (or unique prefix). Loads DB aliases first
so a CLI-added rescue applies. Mirrors SqliteMemory.recover_one."""
impl PostgresBackend.recover_one(id_prefix: str) -> tuple {
    conn = self.__pool__.getconn();
    try {
        _pg_load_db_aliases(conn);
        rows: list = list(
            conn.execute(
                """
                SELECT id, type, arch_module, arch_type, fingerprint, data,
                       error, quarantined_at, from_format_version
                FROM anchors_quarantine
                WHERE id = %s OR id LIKE %s
                LIMIT 2
                """,
                (id_prefix, id_prefix + '%')
            ).fetchall()
        );
        if not rows {
            conn.rollback();
            return (False, f"no quarantined row matching {id_prefix}");
        }
        if len(rows) > 1 {
            conn.rollback();
            return (False, f"prefix {id_prefix} matches multiple rows");
        }
        (ok, reason) = _pg_attempt_recover(conn, rows[0]);
        conn.commit();
        return (ok, reason);
    } finally {
        self.__pool__.putconn(conn);
    }
}

"""Recover every quarantined row; return (n_recovered, [(id, reason)...]).
NodeAnchors are processed before EdgeAnchors so edge re-link finds live nodes.
Mirrors SqliteMemory.recover_all."""
impl PostgresBackend.recover_all -> tuple {
    conn = self.__pool__.getconn();
    try {
        _pg_load_db_aliases(conn);
        rows: list = list(
            conn.execute(
                """
                SELECT id, type, arch_module, arch_type, fingerprint, data,
                       error, quarantined_at, from_format_version
                FROM anchors_quarantine
                """
            ).fetchall()
        );
        rows.sort(key=lambda r: any : 0 if r[1] == 'NodeAnchor' else 1);
        recovered = 0;
        still_stuck: list = [];
        for r in rows {
            (ok, reason) = _pg_attempt_recover(conn, r);
            if ok {
                recovered += 1;
            } else {
                still_stuck.append((str(r[0]), reason));
            }
        }
        conn.commit();
        return (recovered, still_stuck);
    } finally {
        self.__pool__.putconn(conn);
    }
}

"""List DB-resident aliases, oldest-first. Mirrors SqliteMemory.list_aliases."""
impl PostgresBackend.list_aliases -> list {
    conn = self.__pool__.getconn();
    try {
        rows: any = conn.execute(
            "SELECT old_name, new_name, COALESCE(created_at, '') "
            "FROM aliases ORDER BY created_at"
        ).fetchall();
    } finally {
        self.__pool__.putconn(conn);
    }
    return [
        {'old_name': str(r[0]), 'new_name': str(r[1]), 'created_at': str(r[2])}
        for r in rows
    ];
}

"""Add (or replace) an alias and merge it into the in-process Serializer map.
Idempotent (ON CONFLICT DO UPDATE). Mirrors SqliteMemory.add_alias."""
impl PostgresBackend.add_alias(old_name: str, new_name: str) -> None {
    now = datetime.now(timezone.utc).isoformat();
    conn = self.__pool__.getconn();
    try {
        conn.execute(
            """
            INSERT INTO aliases (old_name, new_name, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (old_name) DO UPDATE SET
                new_name=EXCLUDED.new_name, created_at=EXCLUDED.created_at
            """,
            (old_name, new_name, now)
        );
        conn.commit();
    } finally {
        self.__pool__.putconn(conn);
    }
    Serializer._aliases[old_name] = new_name;
}

"""Remove an alias. Returns True if an entry was deleted. Mirrors
SqliteMemory.remove_alias."""
impl PostgresBackend.remove_alias(old_name: str) -> bool {
    conn = self.__pool__.getconn();
    try {
        cursor: any = conn.execute(
            "DELETE FROM aliases WHERE old_name = %s", (old_name, )
        );
        conn.commit();
        removed = cast(int, cursor.rowcount) > 0;
    } finally {
        self.__pool__.putconn(conn);
    }
    if removed {
        Serializer._aliases.pop(old_name, None);
    }
    return removed;
}

"""File a DANGLING_REF quarantine record for a missing referent (a referrer
cites an id with no live row). Idempotent, never raises. Faithful port of
MongoBackend.quarantine_dangling: reason_code='DANGLING_REF' is the
marker is_recoverable_quarantine (P4) must EXCLUDE, so a genuine dangler keeps
being pruned instead of mistaken for schema drift.

ponytail: reuses _pg_quarantine (the same INSERT..ON CONFLICT + commit) via
_pg_record_dangling, which passes delete_live=False — so no live anchor row is
ever deleted for a dangling record (matches SqliteMemory._record_dangling, which
is insert-only). This is load-bearing for fsck --repair, where a cited id may
resolve to a live row that must be preserved, not destroyed."""
impl PostgresBackend.quarantine_dangling(
    missing_id: UUID, referrer_id: (UUID | None), kind: str
) -> None {
    if self.__pool__ is None {
        return;
    }
    conn = self.__pool__.getconn();
    try {
        _pg_record_dangling(conn, missing_id, referrer_id, kind, manage_txn=True);
    } finally {
        self.__pool__.putconn(conn);
    }
}

"""True iff `id` is quarantined under a RECOVERABLE reason (anything but
DANGLING_REF). PG has a `reason_code` column, so this is a direct filter (vs
sqlite's error-text LIKE). `IS DISTINCT FROM` counts a NULL reason_code as
recoverable. Mirrors MongoBackend.is_recoverable_quarantine."""
impl PostgresBackend.is_recoverable_quarantine(id: UUID) -> bool {
    if self.__pool__ is None {
        return False;
    }
    conn = self.__pool__.getconn();
    try {
        row: any = conn.execute(
            """
            SELECT 1 FROM anchors_quarantine
            WHERE id = %s AND reason_code IS DISTINCT FROM 'DANGLING_REF'
            """,
            (str(id), )
        ).fetchone();
        return row is not None;
    } finally {
        self.__pool__.putconn(conn);
    }
}

"""Scan the anchor table for referential-integrity violations; optionally
repair. See the PersistentMemory.fsck contract for the report shape. Read-only
by default. Repair prunes dangling citations (filing each under DANGLING_REF)
and collects orphan/broken/half-linked edges + orphan nodes, atomically in one
transaction. Line-for-line port of SqliteMemory.fsck / MongoBackend.fsck; `data`
is a dict (JSONB auto-loaded), so no json.loads on the scan."""
impl PostgresBackend.fsck(repair: bool = False) -> dict {
    fsck_report: dict = {
        'location': self.dsn,
        'dangling_node_edge': [],
        'dangling_edge_node': [],
        'orphan_edges': [],
        'orphan_nodes': [],
        # Edges cited by exactly one of their two (existing) endpoints -- the
        # optimistic-concurrency orphan signature. Each: (edge, citing, rejecting).
        'half_linked_edges': [],
        'repaired': repair,
        'repaired_counts': {'pruned': 0, 'quarantined': 0, 'collected': 0}
    };
    if self.__pool__ is None {
        return fsck_report;
    }
    conn = self.__pool__.getconn();
    try {
        # --- 1. Read the graph's topology metadata cheaply. ---
        node_ids: set[str] = set();
        edge_ids: set[str] = set();
        node_edges: dict[str, list[str]] = {};
        edge_endpoints: dict[str, tuple[(str | None), (str | None)]] = {};
        node_is_root: dict[str, bool] = {};
        scan: any = conn.execute(
            "SELECT id, type, arch_type, data FROM anchors"
        ).fetchall();
        for (row_id, row_type, row_atype, row_data) in scan {
            rid = str(row_id);
            d = row_data if isinstance(row_data, dict) else {};
            if row_type == 'NodeAnchor' {
                node_ids.add(rid);
                node_edges[rid] = [str(e) for e in (d.get('edges') or [])];
                node_is_root[rid] = row_atype == 'Root';
            } elif row_type == 'EdgeAnchor' {
                edge_ids.add(rid);
                src = d.get('source');
                tgt = d.get('target');
                edge_endpoints[rid] = (
                    (str(src) if src is not None else None),
                    (str(tgt) if tgt is not None else None)
                );
            }
        }
        # --- 2. Classify violations (into typed accumulators, mirrored into the
        # report dict below so repair iterates str-typed pairs). ---
        dangling_ne: list[tuple[str, str]] = [];
        dangling_en: list[tuple[str, str]] = [];
        orphan_e_list: list[str] = [];
        orphan_n_list: list[str] = [];
        half_list: list[tuple[str, str, str]] = [];
        cited_edges: set[str] = set();
        for (nid, eids) in node_edges.items() {
            for eid in eids {
                cited_edges.add(eid);
                if eid not in edge_ids {
                    dangling_ne.append((nid, eid));
                }
            }
        }
        broken_edge_ids: set[str] = set();  # cite a missing node
        for (eid, endpoints) in edge_endpoints.items() {
            for endp in endpoints {
                if endp is not None and endp not in node_ids {
                    dangling_en.append((eid, cast(str, endp)));
                    broken_edge_ids.add(eid);
                }
            }
        }
        orphan_edge_ids: set[str] = set();  # cited by nobody
        for eid in edge_ids {
            if eid not in cited_edges {
                orphan_e_list.append(eid);
                orphan_edge_ids.add(eid);
            }
        }
        # Half-linked edge (OCC orphan signature): both endpoints exist, but only
        # one cites the edge. The non-citing endpoint authoritatively rejected
        # the link. A symmetric edge is healthy; a doubly-uncited edge is already
        # an orphan_edge above.
        half_linked_ids: set[str] = set();
        for (eid, ep) in edge_endpoints.items() {
            if (
                ep[0] is None
                or ep[1] is None
                or ep[0] not in node_ids
                or ep[1] not in node_ids
            ) {
                continue;  # missing endpoint -> dangling_edge_node, handled
            }
            src = cast(str, ep[0]);
            tgt = cast(str, ep[1]);
            src_cites = src in node_edges and eid in node_edges[src];
            tgt_cites = tgt in node_edges and eid in node_edges[tgt];
            if src_cites != tgt_cites {
                (citing, rejecting) = (src, tgt) if src_cites else (tgt, src);
                half_list.append((eid, citing, rejecting));
                half_linked_ids.add(eid);
            }
        }
        # A node left edgeless once collectible edges go, unreferenced by any
        # surviving edge, is itself an orphan to collect.
        collectible_edges: set[str] = (
            orphan_edge_ids | half_linked_ids | broken_edge_ids
        );
        surviving_referenced: set[str] = set();
        for (eid, ep) in edge_endpoints.items() {
            if eid not in collectible_edges {
                if ep[0] is not None {
                    surviving_referenced.add(ep[0]);
                }
                if ep[1] is not None {
                    surviving_referenced.add(ep[1]);
                }
            }
        }
        for nid in node_ids {
            remaining = [
                e
                for e in node_edges.get(nid, [])
                if e not in collectible_edges
            ];
            if (
                not node_is_root.get(nid)
                and not remaining
                and nid not in surviving_referenced
            ) {
                orphan_n_list.append(nid);
            }
        }
        fsck_report['dangling_node_edge'] = dangling_ne;
        fsck_report['dangling_edge_node'] = dangling_en;
        fsck_report['orphan_edges'] = orphan_e_list;
        fsck_report['orphan_nodes'] = orphan_n_list;
        fsck_report['half_linked_edges'] = half_list;
        if not repair {
            conn.rollback();  # read-only: touch nothing
            return fsck_report;
        }
        # --- 3. Repair, atomically. ---
        counts = fsck_report['repaired_counts'];
        try {
            remove_by_node: dict[str, set[str]] = {};
            for (nid, eid) in dangling_ne {
                remove_by_node.setdefault(nid, set()).add(eid);
                _pg_record_dangling(conn, eid, nid, 'edge', manage_txn=False);
                counts['quarantined'] += 1;
            }
            for (eid, nid) in dangling_en {
                _pg_record_dangling(conn, nid, eid, 'node', manage_txn=False);
                counts['quarantined'] += 1;
            }
            # Broken + orphan + half-linked edges are collected; first strip
            # their ids from any node still citing them (for half-linked, that
            # strands the citing endpoint's child for orphan-node collection).
            collect_edges: set[str] = (
                broken_edge_ids | orphan_edge_ids | half_linked_ids
            );
            for (nid, eids) in node_edges.items() {
                also = set(eids) & collect_edges;
                if also {
                    remove_by_node.setdefault(nid, set()).update(also);
                }
            }
            for (nid, rem) in remove_by_node.items() {
                counts['pruned'] += _pg_prune_node_edges(conn, nid, rem);
            }
            to_collect: list = list(collect_edges) + list(orphan_n_list);
            if to_collect {
                cur: any = conn.execute(
                    "DELETE FROM anchors WHERE id = ANY(%s)", (to_collect, )
                );
                rc = cast(int, cur.rowcount);
                counts['collected'] += rc if rc and rc > 0 else 0;
            }
            conn.commit();
        } except Exception as e {
            conn.rollback();
            logger.error(f"PostgresBackend.fsck --repair rolled back: {e}");
            fsck_report['repaired'] = False;
        }
    } finally {
        self.__pool__.putconn(conn);
    }
    return fsck_report;
}
