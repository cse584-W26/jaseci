"""PostgresRelBackend bodies: the KV Postgres store + a relational edges table.

The edges table replaces the per-root GTI blob as the topology answer-er:
one row per EdgeAnchor, maintained inside apply()'s transaction from changeset
intents (no topo_utils hooks, so no JAC_TOPOLOGY_INDEX coupling -- the rel
backend keeps working with the GTI flag off). Consistency rule: an edges row
exists iff the edge's anchors row exists; both change in the same transaction.
Hop resolution is served by resolve_hop_sql via the 'topology_sql' capability
(dispatched from resolver.impl.jac's resolve_hop). See ARCH_REL.md and
docs/superpowers/specs/2026-07-13-pg-rel-backend-design.md."""

import os;
import threading;

# Rel-schema bootstrap is separate from the KV pool build: the pool may
# already be process-cached by a KV PostgresBackend on the same DSN, so the
# postinit pool-cache hit would skip any schema work folded in there.
glob _pgrel_schema_lock = threading.Lock(),
     _pgrel_schema_done: set[str] = set();

glob _REL_SCHEMA_SQL: list[str] = [
         """
    CREATE TABLE IF NOT EXISTS edges (
        edge_id       UUID PRIMARY KEY,
        source        UUID NOT NULL,
        target        UUID NOT NULL,
        edge_type     TEXT NOT NULL,
        is_undirected BOOLEAN NOT NULL DEFAULT FALSE,
        seq           BIGINT GENERATED ALWAYS AS IDENTITY
    )
    """,
         "CREATE INDEX IF NOT EXISTS idx_edges_src ON edges (source, edge_type, seq)",
         "CREATE INDEX IF NOT EXISTS idx_edges_tgt ON edges (target, edge_type, seq)"
     ];


impl PostgresRelBackend.postinit -> None {
    super.postinit();
    if self.dsn not in _pgrel_schema_done {
        with _pgrel_schema_lock {
            if self.dsn not in _pgrel_schema_done {
                conn: any = self.__pool__.getconn();
                try {
                    for stmt in _REL_SCHEMA_SQL {
                        conn.execute(stmt);
                    }
                    conn.commit();
                } finally {
                    self.__pool__.putconn(conn);
                }
                _pgrel_schema_done.add(self.dsn);
            }
        }
    }
}


# JAC_ORDER_PUSHDOWN parser now lives in runtimelib.utils (shared with the
# mongo Route-A tail); imported here so pg-rel's mid-chain SQL ordering is
# unchanged. See utils.order_pushdown_cfg for the flag format.
import from jaclang.runtimelib.utils { order_pushdown_cfg as _order_pushdown_cfg }


"""Advertise SQL topology. JAC_TOPOLOGY_SQL=0 turns the resolver dispatch off
while keeping rel storage (ablation axis: rel-storage-with-GTI-hops vs
rel-storage-with-SQL-hops)."""
impl PostgresRelBackend.capabilities -> set[str] {
    caps: set[str] = set();
    env = os.environ.get("JAC_TOPOLOGY_SQL");
    if env is None or env.lower() not in ("0", "false", "no", "off") {
        caps.add('topology_sql');
    }
    if projection_cfg() {
        # Independent of the topology kill switch: these route the final-hop
        # QueryPlan tail through execute_plan (projection + full-hydrate
        # fallback), which works with or without SQL hops.
        caps |= {'id_in', 'type_pushdown', 'projection'};
    }
    return caps;
}


"""Projected payload fetch for the final-hop QueryPlan tail. plan.projection
set -> narrow SELECT of jsonb paths -> slim marked anchors (never L1/L2
cached, never dirty-scanned). plan.projection None -> full-hydrate fallback:
with projection caps advertised, plans for UNDECLARED types also pass the
needs() subset test and route here; returning empty would silently empty the
walker's result (caps-leak guard from review)."""
impl PostgresRelBackend.execute_plan(plan: QueryPlan) -> Generator[Anchor, None, None] {
    if plan.id_in is None {
        return;
    }
    if plan.projection is None {
        for anchor in self.batch_get(list(plan.id_in)).values() {
            if (
                plan.node_type_final is None
                or type(anchor.__dict__.get('archetype')).__name__ == plan.node_type_final
            ) {
                yield anchor;
            }
        }
        return;
    }
    fields = sorted(plan.projection);
    cols = ", ".join(["data->'archetype'->%s"] * len(fields));
    # data->>'root' rides along unconditionally: slim anchors keep structural
    # identity (owning root) so they stay valid traversal origins on the GTI
    # fast path; only archetype payload fields are trimmed.
    sql = f"SELECT id, arch_module, arch_type, {cols}, data->>'root' FROM anchors WHERE id = ANY(%s)";
    params: list = list(fields);  # SELECT-list binds precede WHERE binds
    params.append([str(u) for u in plan.id_in]);
    if plan.node_type_final is not None {
        sql += " AND arch_type = %s";
        params.append(plan.node_type_final);
    }
    try {
        with self._read_conn() as conn {
            rows: any = conn.execute(sql, tuple(params)).fetchall();
        }
    } except Exception as e {
        logger.debug(
            f"PostgresRelBackend.execute_plan failed: {type(e).__name__}: {e}"
        );
        return;
    }
    for row in rows {
        r: any = row;
        fvals: dict = {};
        for i in range(len(fields)) {
            if r[3 + i] is not None {
                fvals[fields[i]] = r[3 + i];
            }
        }
        slim = Serializer.deserialize_projected(
            to_uuid(r[0]),
            r[1] or '',
            r[2] or '',
            fvals,
            plan.projection,
            root_id=cast((str | None), r[3 + len(fields)])
        );
        if slim is not None {
            self.rel_projection_count += 1;
            yield slim;
        }
    }
}


"""One edges-index row for a populated EdgeAnchor (INSERT .. ON CONFLICT
upsert; edge rows are immutable in practice, the upsert covers re-seeding)."""
def _rel_edge_row_sql -> str {
    return (
        "INSERT INTO edges (edge_id, source, target, edge_type, is_undirected) "
        "VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (edge_id) DO UPDATE SET "
        "source=EXCLUDED.source, target=EXCLUDED.target, "
        "edge_type=EXCLUDED.edge_type, is_undirected=EXCLUDED.is_undirected"
    );
}


def _rel_edge_params(anchor: Anchor) -> (tuple | None) {
    if not isinstance(anchor, EdgeAnchor)
    or not anchor.is_populated()
    or anchor.source is None
    or anchor.target is None {
        return None;
    }
    # Native uuid binds (columns are UUID): psycopg adapts uuid.UUID directly;
    # no str() round-trip on either side of the boundary.
    return (
        anchor.id,
        anchor.source.id,
        anchor.target.id,
        type(anchor.archetype).__name__,
        bool(anchor.is_undirected)
    );
}


"""Admin/seeding upsert: keep the edges row in step with the out-of-band
anchor write. Runtime graph mutations flow through apply(), not here."""
impl PostgresRelBackend.put(anchor: Anchor) -> None {
    super.put(anchor);
    params = _rel_edge_params(anchor);
    if params is None {
        return;
    }
    conn: any = self.__pool__.getconn();
    try {
        conn.execute(_rel_edge_row_sql(), params);
        conn.commit();
    } except Exception as e {
        conn.rollback();
        logger.warning(
            f"PostgresRelBackend.put: edge row for {anchor.id} failed: "
            f"{type(e).__name__}: {e}"
        );
    } finally {
        self.__pool__.putconn(conn);
    }
}


"""Extend the flush unit with edges-table maintenance, same transaction.

Sweeps run BEFORE the parent's anchor delete (order is cosmetic inside one
txn but keeps the rows gone even if the parent arm early-returns); the
edge-row insert runs AFTER the parent upserts the edge's anchor row, so the
consistency rule (edges row iff anchors row) holds at commit whatever the
parent did. Unpopulated/stub EDGE_CREATE anchors are skipped (cannot happen
via record_create, which only stages populated edges)."""
impl PostgresRelBackend._apply_intent(conn: Any, intent: WriteIntent) -> None {
    anchor = intent.anchor;
    key = anchor.id;
    if intent.op == WriteOp.NODE_DELETE {
        conn.execute("DELETE FROM edges WHERE source = %s OR target = %s", (key, key));
    } elif intent.op == WriteOp.EDGE_DELETE {
        conn.execute("DELETE FROM edges WHERE edge_id = %s", (key, ));
    }
    super._apply_intent(conn, intent);
    if intent.op == WriteOp.EDGE_CREATE {
        params = _rel_edge_params(anchor);
        if params is not None {
            conn.execute(_rel_edge_row_sql(), params);
        }
    }
}


"""Answer a WHOLE hop-chain in one SQL round-trip: one CTE per hop, each
joining the edges table against the previous hop's frontier and deduping
via GROUP BY (prevents fan-out blowup). Node-type filters join anchors
per hop (edges-side cast, see resolve_hop_sql). Final hop: creation-order
(MIN seq) with the slice applied Python-side; JAC_ORDER_PUSHDOWN applies
to the final hop's node type. None on failure/empty-chain -> caller falls
back to the per-hop ladder. This is what turns k hops into 1 round-trip
(the depth-slope lever); Mongo has no equivalent join to push into."""
impl PostgresRelBackend.resolve_chain_sql(
    origin_ids: set[UUID], chain: list[tuple], slc: (slice | None) = None
) -> (set[UUID] | list[UUID] | None) {
    if not chain {
        return None;
    }
    if not origin_ids {
        return [] if slc is not None else set();
    }
    n = len(chain);
    (_, last_node_type, _) = chain[-1];
    order_cfg = _order_pushdown_cfg(last_node_type);
    ctes: list[str] = ["h0 AS (SELECT unnest(%s::uuid[]) AS out_id)"];
    params: list = [list(origin_ids)];
    for (i, hop) in enumerate(chain) {
        (edge_type, node_type, direction) = hop;
        etype_pred = " AND e.edge_type = %s" if edge_type is not None else "";
        if direction == 2 {
            legs = [('source', 'target', False), ('target', 'source', True)];
        } elif direction == 1 {
            legs = [('target', 'source', False), ('source', 'target', True)];
        } else {
            legs = [('source', 'target', False), ('target', 'source', False)];
        }
        parts: list[str] = [];
        leg_params: list = [];
        for (src_col, dst_col, undirected_only) in legs {
            upred = " AND e.is_undirected" if undirected_only else "";
            parts.append(
                f"SELECT e.{dst_col} AS out_id, e.seq AS seq FROM edges e "
                f"JOIN h{i} p ON e.{src_col} = p.out_id "
                f"WHERE TRUE{etype_pred}{upred}"
            );
            if edge_type is not None {
                leg_params.append(edge_type);
            }
        }
        inner = " UNION ALL ".join(parts);
        type_join = "";
        if node_type is not None {
            type_join = (
                f" JOIN anchors a{i} ON a{i}.id = dst.out_id::text "
                f"AND a{i}.arch_type = %s"
            );
        }
        is_last = i == n - 1;
        if is_last and order_cfg is not None {
            # Order key carried out of the final CTE for the outer ORDER BY.
            # Params bind by placeholder position in the CTE TEXT: the ordkey
            # %s sits in the SELECT list, BEFORE the FROM-subquery leg params
            # and the arch_type join predicate.
            ctes.append(
                f"h{i + 1} AS (SELECT dst.out_id, MIN(dst.seq) AS seq, "
                f"MAX(a{i}.data->'archetype'->>%s) AS ordkey "
                f"FROM ({inner}) dst{type_join} GROUP BY dst.out_id)"
            );
            params.append(order_cfg[1]);
            params.extend(leg_params);
        } else {
            ctes.append(
                f"h{i + 1} AS (SELECT dst.out_id, MIN(dst.seq) AS seq "
                f"FROM ({inner}) dst{type_join} GROUP BY dst.out_id)"
            );
            params.extend(leg_params);
        }
        if node_type is not None {
            params.append(node_type);
        }
    }
    order_by = f"ordkey {order_cfg[2]}" if order_cfg is not None else "seq";
    sql = f"WITH {', '.join(ctes)} SELECT out_id FROM h{n} ORDER BY {order_by}";
    try {
        with self._read_conn() as conn {
            rows: any = conn.execute(sql, tuple(params)).fetchall();
        }
        self.rel_chain_count += 1;
        ordered = [r[0] for r in rows];
        if slc is not None {
            return ordered[slc];
        }
        if order_cfg is not None {
            return ordered;
        }
        return set(ordered);
    } except Exception as e {
        self.rel_hop_fallback_count += 1;
        logger.debug(
            f"PostgresRelBackend.resolve_chain_sql fell back: "
            f"{type(e).__name__}: {e}"
        );
        return None;
    }
}


"""Answer one hop from the edges table. Returns None on any failure so the
resolver falls back to the blob/walk ladder (never raises into a request).

direction uses EdgeDir ints (IN=1, OUT=2, ANY=3). Directed rows traverse
source->target; undirected rows traverse both ways (GTI parity: topo_utils
writes two adjacency entries for them). Result order is first-seen creation
order (GROUP BY endpoint ORDER BY MIN(seq)), matching
TopologyIndex.resolve_chain_ordered's adj_list walk; the slice is applied
here. Type filters are exact-match: edge_type is parity with GTI (no MRO
fan-out there either), node_type diverges for superclass filters (ledgered
in PORT_NOTES_REL.md)."""
impl PostgresRelBackend.resolve_hop_sql(
    current_ids: set[UUID],
    edge_type: (str | None),
    node_type: (str | None),
    direction: int,
    slc: (slice | None) = None
) -> (set[UUID] | list[UUID] | None) {
    if not current_ids {
        return [] if slc is not None else set();
    }
    ids = list(current_ids);  # uuid.UUID binds straight to the UUID[] param
    etype_pred = " AND e.edge_type = %s" if edge_type is not None else "";

    # (src_col, dst_col, undirected_only) legs UNION ALL'd per direction.
    if direction == 2 {
        legs = [('source', 'target', False), ('target', 'source', True)];
    } elif direction == 1 {
        legs = [('target', 'source', False), ('source', 'target', True)];
    } else {
        legs = [('source', 'target', False), ('target', 'source', False)];
    }
    parts: list[str] = [];
    params: list = [];
    for (src_col, dst_col, undirected_only) in legs {
        upred = " AND e.is_undirected" if undirected_only else "";
        parts.append(
            f"SELECT e.{dst_col} AS out_id, e.seq AS seq FROM edges e "
            f"WHERE e.{src_col} = ANY(%s){etype_pred}{upred}"
        );
        params.append(ids);
        if edge_type is not None {
            params.append(edge_type);
        }
    }
    inner = " UNION ALL ".join(parts);
    type_join = "";
    if node_type is not None {
        # anchors.id stays TEXT (KV-shared table); cast on the edges side so
        # the anchors PK index remains usable.
        type_join = " JOIN anchors a ON a.id = dst.out_id::text AND a.arch_type = %s";
        params.append(node_type);
    }
    order_cfg = _order_pushdown_cfg(node_type);
    if order_cfg is not None {
        # Field ordering in PG (experiment flag). ISO timestamps sort
        # correctly as text; MAX() satisfies GROUP BY (data is functionally
        # dependent on out_id but PG wants an aggregate).
        sql = (
            f"SELECT dst.out_id FROM ({inner}) dst{type_join} "
            f"GROUP BY dst.out_id "
            f"ORDER BY MAX(a.data->'archetype'->>%s) {order_cfg[2]}"
        );
        params.append(order_cfg[1]);
    } else {
        sql = (
            f"SELECT dst.out_id FROM ({inner}) dst{type_join} "
            "GROUP BY dst.out_id ORDER BY MIN(dst.seq)"
        );
    }
    try {
        with self._read_conn() as conn {
            rows: any = conn.execute(sql, tuple(params)).fetchall();
        }
        self.rel_hop_count += 1;
        ordered = [r[0] for r in rows];  # UUID column -> uuid.UUID objects
        if slc is not None {
            return ordered[slc];
        }
        if order_cfg is not None {
            # Ordered list result: the resolver materializes lists in order,
            # so PG's ORDER BY survives into the walker's visit sequence.
            return ordered;
        }
        return set(ordered);
    } except Exception as e {
        self.rel_hop_fallback_count += 1;
        logger.debug(
            f"PostgresRelBackend.resolve_hop_sql fell back: " f"{type(e).__name__}: {e}"
        );
        return None;
    }
}
