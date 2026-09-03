# Interned str->UUID conversion. The same anchor/edge ids recur on every
# request (feed rows, adjacency lists) - 20k UUID() constructions per request
# on the littleX feed. UUID objects are immutable, so sharing one instance per
# id string is observationally identical while turning repeat conversions into
# one C-level dict hit. Wholesale clear at 500k entries bounds memory.
glob _uuid_cache: dict = {};


glob _mirror_state: dict = {};


glob _adj_state: dict = {};


glob _adjtbl_state: dict = {};


impl intern_uuid(s: object) -> UUID {
    key = s if isinstance(s, str) else str(s);
    if (hit := _uuid_cache.get(key)) is not None {
        return hit;
    }
    u = UUID(key);
    if len(_uuid_cache) > 500000 {
        _uuid_cache.clear();
    }
    _uuid_cache[key] = u;
    return u;
}


glob _SCHEMA_SQL = [
         """
    CREATE TABLE IF NOT EXISTS anchors (
        id             uuid PRIMARY KEY,
        kind           text NOT NULL,
        arch_type      text NOT NULL DEFAULT '',
        arch_module    text NOT NULL DEFAULT '',
        fingerprint    text NOT NULL DEFAULT '',
        root_id        uuid,
        src            uuid,
        dst            uuid,
        undirected     boolean NOT NULL DEFAULT false,
        props          jsonb NOT NULL DEFAULT '{}'::jsonb,
        format_version integer NOT NULL DEFAULT 1,
        updated_at     timestamptz NOT NULL DEFAULT now(),
        seq            bigserial
    )
    """,
         """
    CREATE INDEX IF NOT EXISTS idx_anchors_src
        ON anchors (src, arch_type) WHERE src IS NOT NULL
    """,
         """
    CREATE INDEX IF NOT EXISTS idx_anchors_dst
        ON anchors (dst, arch_type) WHERE dst IS NOT NULL
    """,
         """
    CREATE INDEX IF NOT EXISTS idx_anchors_kind_type
        ON anchors (kind, arch_type)
    """,
         """
    ALTER TABLE anchors ADD COLUMN IF NOT EXISTS src_type text
    """,
         """
    ALTER TABLE anchors ADD COLUMN IF NOT EXISTS dst_type text
    """,
         # Typed-endpoint indexes: a hop like `-->[?:Tweet]` filters the target
         # node's type, but the target type lives on the *node* row, so without
         # these the edge scan yields every incident edge and half the fetched
         # targets are thrown away. Carrying the endpoint arch_type on the edge
         # lets the hop prune here instead. Measured on littleX (2550-tweet
         # feed): 5000 target probes -> 2500, 18.7k buffers -> 8.3k, 12.9ms ->
         # 6.2ms.
         #
         # INCLUDE the OPPOSITE endpoint (P6 turn 2): every hop reads the far
         # end of the edge it just found, and that column lives in the heap,
         # so a scan returning n edges paid n random heap fetches. Carrying it
         # in the index leaf makes the hop an Index Only Scan. Measured on the
         # SNB ic1 depth-3 Knows closure (2761 expansions, ~30 edges each):
         # 83k heap fetches -> ~4.5k, 125-135ms -> 65-72ms warm.
         # ponytail: INCLUDE disables btree deduplication, so these indexes
         # roughly double on disk (136MB -> 539MB for dst_typed on SF1). Worth
         # it while reads dominate; a write-heavy store would want the plain
         # form back.
         """
    CREATE INDEX IF NOT EXISTS idx_anchors_src_typed
        ON anchors (src, arch_type, dst_type) INCLUDE (dst)
        WHERE src IS NOT NULL
    """,
         """
    CREATE INDEX IF NOT EXISTS idx_anchors_dst_typed
        ON anchors (dst, arch_type, src_type) INCLUDE (src)
        WHERE dst IS NOT NULL
    """,
         """
    CREATE INDEX IF NOT EXISTS idx_anchors_root
        ON anchors (root_id) WHERE root_id IS NOT NULL
    """,
         """
    CREATE TABLE IF NOT EXISTS graph_types (
        type_name text NOT NULL,
        ancestor  text NOT NULL,
        PRIMARY KEY (type_name, ancestor)
    )
    """,
         """
    CREATE TABLE IF NOT EXISTS kv_state (
        key        text PRIMARY KEY,
        value      text NOT NULL,
        expires_at timestamptz,
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
         """
    CREATE TABLE IF NOT EXISTS quarantine (
        missing_id  uuid NOT NULL,
        referrer_id uuid,
        kind        text NOT NULL,
        created_at  timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (missing_id, kind)
    )
    """
     ];


impl ConnInfo.dsn -> str {
    if self.unix_socket_dir {
        return (
            f"host={self.unix_socket_dir} user={self.user} " f"dbname={self.database}"
        );
    }
    return (
        f"host={self.host} port={self.port} user={self.user} " f"dbname={self.database}"
    );
}


def _jsonable(o: object) -> str {
    return str(o);
}


def _sanitize_ident(name: str) -> str {
    out = '';
    for ch in name.lower() {
        out += ch if (ch.isalnum() or ch == '_') else '_';
    }
    return out;
}


def _bare_ident(name: str) -> bool {
    # unlike _sanitize_ident this does not rewrite: it answers whether `name`
    # is already safe to paste into DDL (archetype names are CamelCase, so
    # sanitising would never round-trip).
    if not name or name[0].isdigit() {
        return False;
    }
    for ch in name {
        if not (ch.isalnum() or ch == '_') {
            return False;
        }
    }
    return True;
}


def _store_ns(info: ConnInfo) -> str {
    return f"{info.unix_socket_dir or info.host}:{info.port}/{info.database}";
}


glob _PG_CHANNEL_LIMIT = 63,
     _CHANNEL_DIGEST_LEN = 16,
     _CHANNEL_ENVELOPE_KEY = '__jac_channel',
     _CHANNEL_ENVELOPE_VERSION = 1,
     _LISTEN_POLL_SECONDS = 1.0,
     _LISTEN_JOIN_SECONDS = 5.0;


def _channel_travels_verbatim(channel: str) -> bool {
    return (
        bool(channel)
        and '\x00' not in channel
        and len(channel.encode('utf-8')) <= _PG_CHANNEL_LIMIT
    );
}


def _channel_ident(channel: str) -> str {
    if _channel_travels_verbatim(channel) {
        return channel;
    }
    import hashlib;
    digest = hashlib.sha256(channel.encode('utf-8')).hexdigest()[:_CHANNEL_DIGEST_LEN];
    stem = _sanitize_ident(channel)[:_PG_CHANNEL_LIMIT - _CHANNEL_DIGEST_LEN - 1];
    return f"{stem}_{digest}";
}


def _quote_channel(ident: str) -> str {
    escaped = ident.replace('"', '""');
    return f'"{escaped}"';
}


def _channel_wire_payload(channel: str, ident: str, payload: str) -> str {
    if ident == channel {
        return payload;
    }
    return json.dumps(
        {
            _CHANNEL_ENVELOPE_KEY: _CHANNEL_ENVELOPE_VERSION,
            'channel': channel,
            'payload': payload
        }
    );
}


def _channel_envelope(payload: str) -> (ChannelMessage | None) {
    try {
        data = json.loads(payload);
    } except Exception {
        return None;
    }
    if not isinstance(data, dict)
        or data.get(_CHANNEL_ENVELOPE_KEY) != _CHANNEL_ENVELOPE_VERSION {
        return None;
    }
    return ChannelMessage(
        channel=str(data.get('channel', '')), payload=str(data.get('payload', ''))
    );
}


impl PgStore.postinit -> None {
    self._conn = None;
    self._side_conn = None;
    self._lock = threading.RLock();
    self._server_version = None;
    self._in_txn = False;
    self._isolation = None;
    self._known_types = set();
    self._subtype_names_cache = {};
    self._listeners = [];
    self._listen_thread = None;
    self._listen_stop = None;
    self._booted = False;
    self._ready = False;
    self._readying = None;
}


impl PgStore._ensure_ready -> None {
    if self._ready {
        return;
    }
    with self._lock {
        if self._ready or self._readying == threading.get_ident() {
            return;
        }
        self._readying = threading.get_ident();
        try {
            if self.ensure_cb is not None and not self._booted {
                self.conninfo = self.ensure_cb();
                self._booted = True;
            }
            if self.auto_schema {
                ns = _store_ns(self.conninfo);
                with _schema_gate {
                    if ns not in _schema_ready {
                        self.ensure_schema(self.promotions);
                        _schema_ready.add(ns);
                    }
                }
            }
            self._ready = True;
        } finally {
            self._readying = None;
        }
    }
}


impl SessionConflictError.init(
    self: SessionConflictError, database: str = '', blockers: (list[dict] | None) = None
) -> None {
    self.database = database;
    self.blockers = list(blockers or []);
    parts: list[str] = [];
    for b in self.blockers {
        owner = b.get('owner_pid');
        who = (
            f"pid {owner}"
                if owner is not None
                else f"backend {b.get('backend_pid', '?')}"
        );
        cmd = str(b.get('cmd') or '');
        if cmd {
            who = f"{who} (jac {cmd})";
        }
        started = str(b.get('started') or '');
        if started {
            who = f"{who} since {started}";
        }
        parts.append(who);
    }
    detail = '; '.join(parts) if parts else 'an unidentified session';
    super.__init__(
        f"project database '{database}' is held by another live jac"
        f" process: {detail}"
    );
}


def _app_identity -> str {
    import sys;
    cmd = 'embedded';
    try {
        argv = list(sys?.argv or []);
        if argv {
            cmd = os.path.basename(str(argv[0]) or '') or 'embedded';
            if cmd.startswith('jac') and len(argv) > 1 {
                sub = str(argv[1]);
                if sub and not sub.startswith('-') {
                    cmd = sub;
                }
            }
        }
    } except Exception {
        cmd = 'unknown';
    }
    return f"jac:{os.getpid()}:{cmd}"[:63];
}


def _sqlstate(e: Exception) -> str {
    for arg in getattr(e, 'args', ()) {
        if isinstance(arg, dict) and 'C' in arg {
            return str(arg.get('C') or '');
        }
    }
    return '';
}


def _parse_pid(raw: str) -> (int | None) {
    try {
        return int(raw);
    } except ValueError {
        return None;
    }
}


def _owner_alive(pid: (int | None)) -> bool {
    if pid is None or pid <= 0 {
        return True;
    }
    try {
        os.kill(pid, 0);
        return True;
    } except ProcessLookupError {
        return False;
    } except Exception {
        return True;
    }
}


impl PgStore._connect -> Any {
    import from jaclang.vendor.pgpsycopg { resolve_connect }
    pg_connect = resolve_connect();
    info = self.conninfo;
    return pg_connect(
        info.user,
        host=(info.host or None),
        port=info.port,
        unix_socket_dir=info.unix_socket_dir,
        database=info.database,
        password=(info.password or None),
        startup_params={'application_name': _app_identity()}
    );
}


# JAC_PG_POOL=1: park the main wire connection at PgStore.close and hand it
# to the next PgStore for the same DSN, instead of closing it. The serving
# layer builds one Session (and so one PgStore) per request; without the
# pool every request tears down its connection and the next one pays a
# fresh backend fork + startup on the embedded cluster (~10-25ms measured).
# Only the MAIN connection is pooled - side connections can carry LISTEN
# state and are always closed for real. A parked connection is never in a
# transaction (close() rolls back or discards it). Default off.
def _pg_pool_enabled -> bool {
    import os;
    return os.environ.get('JAC_PG_POOL', '').strip().lower()
        in ('1', 'true', 'yes', 'on');
}


def _make_lock -> Any {
    import threading;
    return threading.Lock();
}


glob _PG_POOL: bool = _pg_pool_enabled(),
     _POOL_MAX = 4,
     _pool_gate: Any = _make_lock(),
     _conn_pool: dict[str, list] = {};


def _pool_checkout(dsn: str) -> Any {
    with _pool_gate {
        conns = _conn_pool.get(dsn);
        if conns {
            return conns.pop();
        }
    }
    return None;
}


def _pool_checkin(dsn: str, conn: Any) -> bool {
    with _pool_gate {
        conns = _conn_pool.setdefault(dsn, []);
        if len(conns) < _POOL_MAX {
            conns.append(conn);
            return True;
        }
    }
    return False;
}


impl PgStore._main -> Any {
    if self._conn is None {
        if _PG_POOL {
            self._conn = _pool_checkout(self.conninfo.dsn());
        }
        if self._conn is None {
            self._conn = self._connect();
        }
    }
    return self._conn;
}


impl PgStore._side -> Any {
    self._ensure_ready();
    if self._side_conn is None {
        self._side_conn = self._connect();
    }
    return self._side_conn;
}


def _conn_dead(e: Exception) -> bool {
    if isinstance(e, (ConnectionError, BrokenPipeError, EOFError, OSError)) {
        return True;
    }
    for arg in getattr(e, 'args', ()) {
        if isinstance(arg, dict)
            and arg.get('C') in ('08006', '08003', '57P01', '57P03', '25P03') {
            return True;
        }
    }
    return False;
}


impl PgStore._run(sql: str, params: dict) -> list {
    # JAC_STAGE_HEADERS: the single choke point for every main-connection
    # statement, so it is where x-stg-db-ms is accumulated. q_enter returns
    # None (no timing) unless the request is in its data-query phase and the
    # statement is not transaction control - see stagetimer.py.
    _stg_h = _stg.q_enter(sql) if _stg.ON else None;
    try {
        self._ensure_ready();
        with self._lock {
            conn: Any = None;
            try {
                conn = self._main();
            } except Exception as e {
                if not (_conn_dead(e) and self.ensure_cb is not None) {
                    raise;
                }
                self._conn = None;
                try {
                    self.conninfo = self.ensure_cb();
                } except Exception { }
                conn = self._main();
            }
            try {
                return conn.run(sql, **params) or [];
            } except Exception as e {
                if _conn_dead(e) {
                    try {
                        conn.close();
                    } except Exception { }
                    self._conn = None;
                    was_txn = self._in_txn;
                    self._in_txn = False;
                    if self.ensure_cb is not None {
                        try {
                            self.conninfo = self.ensure_cb();
                        } except Exception { }
                    }
                    if was_txn {
                        import from jaclang.runtimelib.pgwire { PgWireError }
                        raise PgWireError(
                            {
                                'C': '08006',
                                'M': 'connection lost mid-transaction; retry'
                            }
                        ) from e;
                    }
                    conn2: Any = self._main();
                    return conn2.run(sql, **params) or [];
                }
                if self._in_txn {
                    try {
                        conn.run('ROLLBACK');
                    } except Exception { }
                    self._in_txn = False;
                }
                raise;
            }
        }
    } finally {
        if _stg_h is not None {
            _stg.q_exit(_stg_h);
        }
    }
}


impl PgStore.is_available -> bool {
    try {
        self._run('SELECT 1', {});
        return True;
    } except Exception {
        return False;
    }
}


impl PgStore.server_version -> int {
    if self._server_version is None {
        raw = str(self._run('SHOW server_version_num', {})[0][0]);
        self._server_version = int(raw) // 10000;
    }
    return self._server_version;
}


impl PgStore.ensure_schema(promotions: dict[str, list[str]]) -> None {
    with self._lock {
        self.promotions = dict(promotions);
        fp = self._schema_fingerprint();
        if self._schema_stamp() == fp {
            self._load_known_types();
            return;
        }
        try {
            self._apply_schema_ddl();
        } except PgWireError as e {
            if _sqlstate(e) != '55P03' {
                raise;
            }
            if self._reap_dead_sessions() == 0 {
                raise SessionConflictError(
                    database=self.conninfo.database, blockers=self._live_blockers()
                ) from e;
            }
            try {
                self._apply_schema_ddl();
            } except PgWireError as e2 {
                if _sqlstate(e2) != '55P03' {
                    raise;
                }
                raise SessionConflictError(
                    database=self.conninfo.database, blockers=self._live_blockers()
                ) from e2;
            }
        }
        self.kv_put(SCHEMA_STAMP_KEY, fp);
        self._load_known_types();
    }
}


impl PgStore.reset_data -> None {
    with self._lock {
        if self._in_txn {
            self.rollback();
        }
        listed = self._run(
            'SELECT tablename FROM pg_tables WHERE schemaname = current_schema()', {}
        );
        tables = [str(row[0]) for row in listed];
        if not tables {
            return;
        }
        stamp = self._schema_stamp();
        targets = ', '.join(f'"{name}"' for name in sorted(tables));
        self._run(f"TRUNCATE {targets} RESTART IDENTITY CASCADE", {});
        if stamp {
            self.kv_put(SCHEMA_STAMP_KEY, stamp);
        }
        self._known_types = set();
        self._subtype_names_cache = {};
    }
}


impl PgStore._apply_schema_ddl -> None {
    self._run("SET lock_timeout = '5s'", {});
    try {
        for stmt in _SCHEMA_SQL {
            self._run(stmt, {});
        }
        has_seq = bool(
            self._run(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'anchors' AND column_name = 'seq'
                """,
                {}
            )
        );
        if not has_seq {
            self._run('ALTER TABLE anchors ADD COLUMN IF NOT EXISTS seq bigserial', {});
        }
        self._backfill_endpoint_types();
        self._apply_promotions();
        self._property_graph_ddl();
    } finally {
        self._run('SET lock_timeout = DEFAULT', {});
    }
}


impl PgStore._backfill_endpoint_types -> None {
    # Databases written before the typed-endpoint columns existed have NULL
    # src_type/dst_type on their edges. The compiler's typed-hop predicate is
    # an equality, so a NULL would silently drop the edge - backfill before any
    # query can observe it. Idempotent and incremental: matches zero rows once
    # the graph is converted, so it costs one indexless scan on first boot and
    # nothing thereafter.
    for (col, endpoint) in (('src_type', 'src'), ('dst_type', 'dst')) {
        try {
            self._run(
                f"""
                UPDATE anchors e SET {col} = n.arch_type
                  FROM anchors n
                 WHERE e.kind = 'EdgeAnchor' AND e.{endpoint} = n.id
                   AND e.{endpoint} IS NOT NULL AND e.{col} IS NULL
                """,
                {}
            );
        } except Exception as ex {
            logger.warning(f"endpoint-type backfill for {col} failed: {ex}");
        }
    }
}


impl PgStore._load_known_types -> None {
    for (tname, ) in self._run('SELECT DISTINCT type_name FROM graph_types', {}) {
        self._known_types.add(str(tname));
    }
}


impl PgStore._schema_fingerprint -> str {
    import hashlib;
    h = hashlib.sha256();
    h.update(str(SCHEMA_VERSION).encode());
    h.update(str(self.server_version()).encode());
    for stmt in _SCHEMA_SQL {
        h.update(stmt.encode());
    }
    for col in sorted(self._promotion_columns()) {
        h.update(str(col).encode());
    }
    return f"{SCHEMA_VERSION}:{h.hexdigest()[:24]}";
}


impl PgStore._schema_stamp -> (str | None) {
    try {
        return self.kv_get(SCHEMA_STAMP_KEY);
    } except PgWireError as e {
        if _sqlstate(e) == '42P01' {
            return None;
        }
        raise;
    }
}


impl PgStore._peer_sessions -> list[dict] {
    rows = self._run(
        """
        SELECT pid, application_name, state, backend_start::text
        FROM pg_stat_activity
        WHERE datname = current_database() AND pid <> pg_backend_pid()
        """,
        {}
    );
    out: list[dict] = [];
    for (pid, app, state, started) in rows {
        app_s = str(app or '');
        owner: (int | None) = None;
        cmd = '';
        parts = app_s.split(':', 2);
        if len(parts) == 3 and parts[0] == 'jac' {
            owner = _parse_pid(parts[1]);
            cmd = parts[2];
        }
        out.append(
            {
                'backend_pid': int(pid),
                'app': app_s,
                'state': str(state or ''),
                'started': str(started or ''),
                'owner_pid': owner,
                'cmd': cmd,
                'owner_alive': _owner_alive(owner)
            }
        );
    }
    return out;
}


impl PgStore._reap_dead_sessions -> int {
    if not self.conninfo.unix_socket_dir {
        return 0;
    }
    n = 0;
    for p in self._peer_sessions() {
        if p['owner_pid'] is not None and not p['owner_alive'] {
            try {
                self._run('SELECT pg_terminate_backend(:p)', {'p': p['backend_pid']});
                n += 1;
            } except Exception as e {
                logger.warning(f"failed to reap backend {p['backend_pid']}: {e}");
            }
        }
    }
    if n {
        logger.info(f"reaped {n} database session(s) left by dead process(es)");
    }
    return n;
}


impl PgStore._live_blockers -> list[dict] {
    peers = [
        p
        for p in self._peer_sessions()
        if p['owner_alive']
    ];
    held = [
        p
        for p in peers
        if 'idle in transaction' in p['state']
    ];
    return held or peers;
}


impl PgStore.takeover -> int {
    n = 0;
    for p in self._peer_sessions() {
        try {
            self._run('SELECT pg_terminate_backend(:p)', {'p': p['backend_pid']});
            n += 1;
        } except Exception as e {
            logger.warning(f"takeover failed for backend {p['backend_pid']}: {e}");
        }
    }
    return n;
}


impl PgStore.begin(isolation: TxnIsolation = TxnIsolation.SERIALIZABLE) -> None {
    with self._lock {
        if self._in_txn {
            return;
        }
        self._run(f"BEGIN {isolation.value}", {});
        self._in_txn = True;
        self._isolation = isolation;
        try {
            self._run("SET LOCAL lock_timeout = '10s'", {});
        } except Exception { }
    }
}


impl PgStore.commit -> None {
    with self._lock {
        if not self._in_txn {
            return;
        }
        try {
            self._run('COMMIT', {});
        } finally {
            self._in_txn = False;
            self._isolation = None;
        }
    }
}


impl PgStore.rollback -> None {
    with self._lock {
        if not self._in_txn {
            return;
        }
        try {
            self._run('ROLLBACK', {});
        } finally {
            self._in_txn = False;
            self._isolation = None;
        }
    }
}


impl PgStore.in_txn -> bool {
    return self._in_txn;
}


impl PgStore.txn_isolation -> (TxnIsolation | None) {
    return self._isolation if self._in_txn else None;
}


impl PgStore.load_full(ids: list[UUID]) -> dict[UUID, AnchorRow] {
    if not ids {
        return {};
    }
    out: dict[UUID, AnchorRow] = {};
    # F2/lazy adjacency: this SELECT deliberately carries NO edge list. The
    # old `string_agg(e.id) WHERE e.src=a.id OR e.dst=a.id` subquery was an
    # O(node's lifetime edge count) scan+sort+aggregate run on EVERY load of
    # EVERY node, whether or not the walker ever traversed from it (TPC-C's
    # Warehouse: 100,064 edges rebuilt on 100% of new_order/payment, which
    # only read w_tax off it). `adjacency=None` now means "not fetched" -
    # Session._materialize installs a LazyEdges proxy that fetches once, on
    # first actual read of anchor.edges, via PgStore.load_adjacency.
    rows = self._run(
        """
        SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint,
               a.root_id, a.src, a.dst, a.undirected, a.props, a.xmin::text
        FROM anchors a WHERE a.id = ANY(CAST(:ids AS uuid[]))
        """,
        {'ids': [str(i) for i in ids]}
    );
    for r in rows {
        raw_props = r[9];
        props: dict = (
            raw_props if isinstance(raw_props, dict) else json.loads(str(raw_props))
        );
        row = AnchorRow(
            id=intern_uuid(r[0]),
            kind=str(r[1]),
            arch_type=str(r[2]),
            arch_module=str(r[3]),
            fingerprint=str(r[4]),
            root_id=intern_uuid(r[5]) if r[5] else None,
            props=props,
            src=intern_uuid(r[6]) if r[6] else None,
            dst=intern_uuid(r[7]) if r[7] else None,
            undirected=bool(r[8]),
            version=int(str(r[10])),
            adjacency=None
        );
        out[row.id] = row;
    }
    return out;
}


impl PgStore.load_adjacency(id: UUID) -> list[UUID] {
    # The lazy half of load_full: one node's edge ids, fetched only when
    # something actually reads anchor.edges. Runs on the SAME connection and
    # therefore the SAME transaction/snapshot as the request that triggered
    # it, so it can never observe rows the caller's snapshot cannot see.
    # idx_anchors_src / idx_anchors_dst cover both arms of the OR.
    rows = self._run(
        """
        SELECT e.id FROM anchors e
        WHERE e.src = CAST(:id AS uuid) OR e.dst = CAST(:id AS uuid)
        ORDER BY e.seq, e.id
        """,
        {'id': str(id)}
    );
    return [intern_uuid(r[0]) for r in rows];
}


# --- R1/R2 typed mirrors -----------------------------------------------------
# Per-node-archetype mirror tables, trigger-maintained from `anchors` in the
# SAME transaction as every write (anchors stays the source of truth; mirrors
# are derived state, rebuildable by re-running the backfill). Each row carries
# the prebuilt api response fragment (R2) and the ACL scalars the exact fast
# path needs (R4), plus one jsonb column per declared field so the stream path
# can fetch the proof's field set as typed columns instead of parsing props.
def _mirror_table_for(cls: type) -> (dict | None) {
    # -> {'table': name, 'cols': {field: column}} or None if unmappable
    import from hashlib { md5 }
    import from jaclang.runtimelib.typecache { field_names }
    tname = getattr(cls, '__name__', '');
    mod = getattr(cls, '__module__', '');
    if not tname or not mod {
        return None;
    }
    names = field_names(cls);
    if not names {
        return None;
    }
    cols: dict = {};
    seen: set = set();
    for f in names {
        c = 'f_' + _sanitize_ident(str(f));
        if c in seen or not f {
            return None;   # sanitised collision: refuse rather than guess
        }
        seen.add(c);
        cols[str(f)] = c;
    }
    table = 'g_n_' + _sanitize_ident(tname) + '_' + md5(mod.encode()).hexdigest()[:6];
    return {'table': table, 'cols': cols};
}


def _mirror_base_cols -> list {
    out: list = [];
    for c in ('root_id', 'acl_all', 'acl_spec', 'frag') {
        out.append(c);
    }
    return out;
}


# --- memo guard --------------------------------------------------------------
# _mirror_state / _adj_state / _adjtbl_state each assert that a projection
# EXISTS in the database, but they live for the lifetime of the PROCESS. Any
# path that removes one behind the runtime's back leaves the memo naming an
# object that is gone and the ensure is never re-run:
# benchmark/scripts/pg_bulk_load.py --mode full DROPs every g_n_* mirror table
# while the app server is up (its own output says "RESTART the app server
# before serving reads"), and a hand-dropped index is invisible to any error
# path at all - it just plans a seq scan. night0823 F2: littleX feed_page 382ms
# vs 2.9ms, SNB is2 563ms vs 2.2ms, both healed only by a reboot.
#
# The guard is one throttled existence probe over the names the memos have
# claimed so far. Anything missing invalidates ALL THREE memos, not just the
# one that names it - deliberately: the bulk loader drops the mirrors but keeps
# adj_* tables while suppressing their triggers for the whole COPY, so that
# table survives MISSING EVERY BULK ROW with no signal of its own. The signal
# has to be allowed to arrive from a sibling. Over-clearing costs one re-run of
# a set of ensures that are all idempotent (CREATE ... IF NOT EXISTS / OR
# REPLACE / ON CONFLICT DO NOTHING), which is what a reseed wants anyway.
#
# Cost: ONE statement per JAC_MEMO_TTL_SECS (default 5), on the request's own
# connection, and only when an ensure_* is consulted - zero statements on a
# request that does not reach one.
#
# ponytail: detects DISAPPEARANCE, not silent replacement. Nothing in this tree
# drops-and-recreates a memoised name behind the runtime's back (the loader's
# DROP INDEX / recreate-from-pg_get_indexdef pair rebuilds objects whose
# content is correct), so existence is enough. Upgrade path if that changes:
# record to_regclass(n)::oid at DDL time and compare oids - same one statement
# per TTL, one extra SELECT per successful ensure.
#
# Rejected: keying on pg_database.oid or pg_class.oid of `anchors`. Neither
# flips on ANY live-process path - dropping the database needs zero live
# connections (which is exactly why every harness reset script kills the server
# first) and no path drops `anchors`. Also rejected: a generation row bumped by
# the loaders - it needs harness edits, still misses a hand-dropped index, and
# makes runtime correctness depend on external cooperation.
def _memo_ttl -> float {
    import os;
    try {
        return float(os.environ.get('JAC_MEMO_TTL_SECS', '') or 5);
    } except Exception {
        return 5.0;
    }
}


# one dict, never rebound: every field is mutated in place, so no global
# rebinding is needed inside the helpers below
glob _MEMO_MAX_TRIES = 8,
     _memo: dict = {
         'ttl': _memo_ttl(),
         'gate': _make_lock(),
         'objs': set(),
         'at': 0.0,
         'warned': set()
     };


def _memo_track(names: list) -> None {
    with _memo['gate'] {
        for n in names {
            if _bare_ident(str(n)) {
                _memo['objs'].add(str(n));
            }
        }
    }
}


def _memo_check(store: Any) -> None {
    import time;
    if time.monotonic() - float(_memo['at']) < float(_memo['ttl']) {
        return;
    }
    names: list = [];
    with _memo['gate'] {
        if time.monotonic() - float(_memo['at']) < float(_memo['ttl']) {
            return;
        }
        _memo['at'] = time.monotonic();
        names = sorted(_memo['objs']);
    }
    if not names {
        return;
    }
    vals: list = [];
    for n in names {
        vals.append("('" + n + "')");
    }
    try {
        rows = store._run(
            'SELECT count(*) FROM (VALUES ' + ', '.join(vals) + ') v(n) '
                + 'WHERE to_regclass(v.n) IS NULL',
            {}
        );
    } except Exception as e {
        # a probe that cannot run is not evidence of anything; keep the memos
        logger.debug(f"memo guard probe failed (memos kept): {e}");
        return;
    }
    gone = int(rows[0][0]) if rows else 0;
    if not gone {
        return;
    }
    logger.warning(
        f"memo guard: {gone} of {len(names)} memoised projections vanished from"
        ' the database (external reseed?); clearing every ensure_* memo'
    );
    with _memo['gate'] {
        _memo['objs'] = set();
        _memo['warned'] = set();
    }
    _mirror_state.clear();
    _adj_state.clear();
    _adjtbl_state.clear();
}


def _memo_log_once(what: str, reason: str) -> None {
    key = what + '|' + reason;
    msg = f"{what}: {reason}";
    if key in _memo['warned'] {
        logger.debug(msg);
    } else {
        _memo['warned'].add(key);
        logger.warning(msg);
    }
}


# Pre-increment before a build attempt, matching the gord_tries/ep_tries/tries
# discipline this replaces: a DDL connection that HANGS rather than raises is
# only bounded by a counter written before the attempt.
def _memo_attempt(st: dict) -> dict {
    st['ok'] = False;
    st['retryable'] = True;
    st['retry_at'] = 0.0;
    st['tries'] = int(st.get('tries', 0)) + 1;
    return st;
}


def _memo_refused(st: Any) -> bool {
    import time;
    if not isinstance(st, dict) or st.get('ok') is not False {
        return False;
    }
    if not st.get('retryable') or int(st.get('tries', 0)) >= _MEMO_MAX_TRIES {
        return True;
    }
    return time.monotonic() < float(st.get('retry_at', 0.0));
}


def _memo_refuse(st: dict, what: str, reason: str, retryable: bool) -> dict {
    import time;
    tries = int(st.get('tries', 0));
    if not retryable {
        tries += 1;   # a retryable attempt already counted itself
    }
    st['ok'] = False;
    st['tries'] = tries;
    st['reason'] = reason;
    st['retryable'] = retryable;
    st['retry_at'] = time.monotonic() + min(60.0, float(2 ** tries));
    capped = (not retryable) or tries >= _MEMO_MAX_TRIES;
    _memo_log_once(
        what,
        f"refused ({reason}); tries={tries}"
            + (
                ' - giving up until the database changes'
                    if capped
                    else ' - will retry'
            )
    );
    return st;
}


impl PgStore.ensure_mirror(cls: type) -> bool {
    _memo_check(self);
    at = getattr(cls, '__name__', '');
    cached = _mirror_state.get(cls);
    if cached is not None {
        if cached['ok'] {
            return True;
        }
        if _memo_refused(cached) {
            return False;
        }
    }
    # a live refusal record is carried forward so its try count survives
    prev = cached if (cached is not None and cached.get('ok') is False) else {};
    spec = _mirror_table_for(cls);
    if spec is None {
        _mirror_state[cls] = _memo_refuse(
            prev,
            f"mirror for {at}",
            'field names collide after sanitisation, or the type has none',
            False
        );
        return False;
    }
    table = spec['table'];
    cols = spec['cols'];
    _memo_attempt(prev);
    # Mirror creation is one-time schema bootstrap, not request work, so it
    # runs on its OWN connection rather than self._run's. Two reasons:
    # (1) a read-only request transaction (JAC_RO_WALKERS ->
    #     SNAPSHOT_READ_ONLY) refuses DDL outright - 25006, and the failure
    #     was then cached for the process lifetime, so a read-only serving
    #     arm could never build a mirror at all;
    # (2) on a read-write request the DDL would otherwise join that request's
    #     transaction and be rolled back with it.
    # The DDL is idempotent (IF NOT EXISTS / OR REPLACE / DO NOTHING) and
    # CREATE TRIGGER's SHARE ROW EXCLUSIVE on anchors does not conflict with
    # the ACCESS SHARE a concurrent read holds.
    ddl_conn: Any = None;
    try {
        self._ensure_ready();
        ddl_conn = self._connect();
        col_list: list = [];
        for c in cols.values() {
            col_list.append(c);
        }
        ddl_parts: list = [];
        for c in col_list {
            ddl_parts.append(c + ' jsonb');
        }
        col_ddl = ', '.join(ddl_parts);
        empty_obj = "'{}'::jsonb";
        ddl_conn.run(
            'CREATE TABLE IF NOT EXISTS ' + table + ' ('
                + 'id uuid PRIMARY KEY, root_id uuid, '
                + 'acl_all smallint NOT NULL DEFAULT -1, '
                + 'acl_spec boolean NOT NULL DEFAULT false, '
                + "frag text NOT NULL DEFAULT '[]', "
                + col_ddl
                + ')'
        );
        all_cols: list = _mirror_base_cols();
        for c in col_list {
            all_cols.append(c);
        }
        set_cols = ', '.join(all_cols);
        acl_all_expr = (
            "CASE WHEN jsonb_typeof(NEW.props->'access'->'all') = 'number' "
            + "THEN (NEW.props->'access'->>'all')::smallint ELSE -1 END"
        );
        acl_spec_expr = (
            "COALESCE(NEW.props->'access'->'roots'->'anchors', " + empty_obj
            + ') <> ' + empty_obj
        );
        frag_expr = (
            '(COALESCE((SELECT jsonb_object_agg(k.key, k.value) '
            + "FROM jsonb_each(COALESCE(NEW.props->'archetype', " + empty_obj
            + ")) k WHERE left(k.key, 2) <> '__'), " + empty_obj + ') '
            + "|| jsonb_build_object('_jac_type', NEW.arch_type, "
            + "'_jac_id', replace(NEW.id::text, '-', ''), "
            + "'_jac_archetype', 'node'))::text"
        );
        val_list: list = [];
        val_list.append('NEW.root_id');
        val_list.append(acl_all_expr);
        val_list.append(acl_spec_expr);
        val_list.append(frag_expr);
        for f in cols.keys() {
            val_list.append("NEW.props->'archetype'->'" + f + "'");
        }
        vals_sql = ', '.join(val_list);
        upd_parts: list = [];
        for c in all_cols {
            upd_parts.append(c + ' = EXCLUDED.' + c);
        }
        upd = ', '.join(upd_parts);
        ddl_conn.run(
            'CREATE OR REPLACE FUNCTION ' + table + '_sync() RETURNS trigger AS $$ '
                + 'BEGIN IF TG_OP = ' + "'DELETE'" + ' THEN '
                + 'DELETE FROM ' + table + ' WHERE id = OLD.id; RETURN OLD; END IF; '
                + 'INSERT INTO ' + table + ' (id, ' + set_cols + ') '
                + 'VALUES (NEW.id, ' + vals_sql + ') '
                + 'ON CONFLICT (id) DO UPDATE SET ' + upd + '; RETURN NEW; '
                + 'END $$ LANGUAGE plpgsql'
        );
        ddl_conn.run(
            'CREATE OR REPLACE TRIGGER ' + table + '_ins '
                + 'AFTER INSERT OR UPDATE ON anchors FOR EACH ROW '
                + "WHEN (NEW.kind = 'NodeAnchor' AND NEW.arch_type = '" + at + "') "
                + 'EXECUTE FUNCTION ' + table + '_sync()'
        );
        ddl_conn.run(
            'CREATE OR REPLACE TRIGGER ' + table + '_del '
                + 'AFTER DELETE ON anchors FOR EACH ROW '
                + "WHEN (OLD.kind = 'NodeAnchor' AND OLD.arch_type = '" + at + "') "
                + 'EXECUTE FUNCTION ' + table + '_sync()'
        );
        # triggers first, THEN backfill with DO NOTHING: concurrent writes win
        sel_sql = vals_sql.replace('NEW.', 'a.');
        ddl_conn.run(
            'INSERT INTO ' + table + ' (id, ' + set_cols + ') '
                + 'SELECT a.id, ' + sel_sql + ' FROM anchors a '
                + "WHERE a.kind = 'NodeAnchor' AND a.arch_type = '" + at + "' "
                + 'ON CONFLICT (id) DO NOTHING'
        );
        # The DDL above committed on a connection of its own, so a request
        # whose snapshot was already taken sees the mirror as missing or
        # EMPTY (postgres resolves catalog lookups against a fresh snapshot
        # but row reads against the transaction's). Serving a chain from an
        # incomplete mirror silently returns fewer rows - the worst kind of
        # wrong - so confirm completeness FROM THE CALLER'S OWN snapshot
        # before declaring the mirror usable. Anti-join with LIMIT 1: it
        # stops at the first row the mirror is missing.
        missing = self._run(
            "SELECT 1 FROM anchors a WHERE a.kind = 'NodeAnchor' "
                + 'AND a.arch_type = :at AND NOT EXISTS ('
                + 'SELECT 1 FROM ' + table + ' m WHERE m.id = a.id) LIMIT 1',
            {'at': at}
        );
        if missing {
            # Deliberately NOT cached: this request falls back to the
            # non-mirror path (correct, just slower) and the next request -
            # whose snapshot is newer than the DDL commit - probes again and
            # succeeds. Re-running the DDL on that retry is free; every
            # statement is IF NOT EXISTS / OR REPLACE / DO NOTHING.
            return False;
        }
        _mirror_state[cls] = {'ok': True, 'table': table, 'cols': cols};
        _memo_track([table]);
        return True;
    } except Exception as e {
        _mirror_state[cls] = _memo_refuse(
            prev, f"mirror for {at}", str(e), True
        );
        return False;
    } finally {
        if ddl_conn is not None {
            try {
                ddl_conn.close();
            } except Exception { }
        }
    }
}


impl PgStore.mirror_info(cls: type) -> (dict | None) {
    st = _mirror_state.get(cls);
    if not st or not st['ok'] {
        return None;
    }
    return {'table': st['table'], 'cols': st['cols']};
}


# JAC_FUSED_FEED's access path: the sort column on its OWN, so a top-K over an
# arbitrary membership set can be answered by walking the index in order and
# stopping, instead of per-source range scans under
# (src_endpoint, <order_col>). Deliberately a second index rather than a
# widening of that one - the endpoint index is still the right access path for
# single-source queries, and neither can serve the other's drive order.
# `equality=True` asks for the same btree over the column's SCALAR TEXT
# (`col #>> '{}'`) instead of the raw jsonb DESC: get_closure's property
# filter is an equality on that expression (it has to be - the same field is
# a jsonb number from the bulk loader and a jsonb string from a walker), and
# without a matching expression index it seq-scans the whole mirror. Same
# memo/refusal machinery, its own key space and index name so the two can
# coexist on one column.
impl PgStore.ensure_mirror_order_index(
    cls: type, order_col: str, equality: bool = False
) -> bool {
    st = _mirror_state.get(cls);
    if not st or not st['ok'] {
        return False;
    }
    key = ('=' + order_col) if equality else order_col;
    done = st.setdefault('gords', set());
    if key in done {
        return True;
    }
    table = st['table'];
    rf = st.setdefault('gord_refuse', {});
    if _memo_refused(rf.get(key)) {
        return False;
    }
    if not _bare_ident(order_col) {
        rf[key] = _memo_refuse(
            rf.get(key) or {},
            f"mirror order index {table}.{order_col}",
            'order column is not a bare identifier',
            False
        );
        return False;
    }
    _memo_attempt(rf.setdefault(key, {}));
    ddl_conn: Any = None;
    try {
        self._ensure_ready();
        ddl_conn = self._connect();
        # same self-deadlock guard as ensure_mirror_endpoint: the calling
        # request may already hold ACCESS SHARE on this mirror
        ddl_conn.run("SET lock_timeout = '250ms'");
        suffix: str = '_gval_';
        idef: str = "((" + order_col + " #>> '{}'))";
        if not equality {
            suffix = '_gord_';
            idef = '(' + order_col + ' DESC)';
        }
        iname = str(table) + suffix + order_col;
        ddl_conn.run(
            'CREATE INDEX IF NOT EXISTS ' + iname + ' ON ' + str(table)
                + ' ' + idef
        );
        ddl_conn.run('ANALYZE ' + table);
        done.add(key);
        rf.pop(key, None);
        _memo_track([iname]);
        return True;
    } except Exception as e {
        # No completeness probe needed, unlike the endpoint column: an index
        # is either visible to the caller's snapshot and complete, or not
        # visible and the planner simply picks another path. Nothing can be
        # silently dropped from a page by a half-built index.
        rf[key] = _memo_refuse(
            rf.setdefault(key, {}),
            f"mirror order index {table}.{order_col}",
            str(e),
            True
        );
        return False;
    } finally {
        if ddl_conn is not None {
            try {
                ddl_conn.close();
            } except Exception { }
        }
    }
}


# get_topk_inbound's LATERAL src_field arm (jac0core/impl/runtime.impl.jac)
# drives one ordered index scan per source, per dst, stopping at :lim - same
# trick as ensure_mirror_order_index's global top-k arm, one level narrower
# (per-source instead of whole-mirror). Without it: seq scan of the whole
# mirror inside every LATERAL - SNB is2 563ms / ic2 5.9s at SF1 (night0823
# F1, hand-built as idx_g_n_post_d2a57d_creator_created /
# idx_g_n_comment_d2a57d_creator_created to unblock the run; this grows the
# same shape at first use instead).
#
# The index expressions below MUST stay textually identical (module the `m.`
# alias, which postgres resolves to the same Var regardless of spelling) to
# ord_expr/scol in get_topk_inbound, or the planner cannot prove the match -
# the same lesson JAC_PROMOTED_DRIVE and get_closure's adjacency comment
# already paid for.
#
# ponytail: two columns (src, ord DESC), matching the hand-built DDL this
# replaces. EXPLAIN (ANALYZE, BUFFERS) against SNB SF1 showed a third (tie)
# column made no difference to the plan - ties on a millisecond timestamp are
# rare enough that the extra sort, when the planner needs one at all, is over
# 1-2 rows. Add tie back into the index if a workload with frequent
# order-field ties shows a regression (see item3_jtopk/RESULT.md gate a).
impl PgStore.ensure_topk_index(
    cls: type, src_field: str, ord_field: str, tie_field: str
) -> bool {
    st = _mirror_state.get(cls);
    if not st or not st['ok'] {
        return False;
    }
    key = (src_field, ord_field);
    done = st.setdefault('topk', set());
    if key in done {
        return True;
    }
    table = st['table'];
    rf = st.setdefault('topk_refuse', {});
    if _memo_refused(rf.get(key)) {
        return False;
    }
    cols = st['cols'];
    scol = cols.get(src_field);
    ocol = cols.get(ord_field);
    what = f"topk index {table}.{src_field}/{ord_field}";
    if not scol or not ocol or not _bare_ident(scol) or not _bare_ident(ocol) {
        rf[key] = _memo_refuse(
            rf.get(key) or {}, what,
            'source or order field is not a mapped bare-identifier column',
            False
        );
        return False;
    }
    _memo_attempt(rf.setdefault(key, {}));
    name = (
        table + '_topk_' + _sanitize_ident(src_field) + '_'
            + _sanitize_ident(ord_field)
    );
    ddl_conn: Any = None;
    try {
        self._ensure_ready();
        ddl_conn = self._connect();
        # same self-deadlock guard as ensure_mirror_order_index: the calling
        # request may already hold ACCESS SHARE on this mirror
        ddl_conn.run("SET lock_timeout = '250ms'");
        ddl_conn.run(
            'CREATE INDEX IF NOT EXISTS ' + name + ' ON ' + table
                + ' ((' + scol + " #>> '{}'), (((" + ocol
                + " #>> '{}'))::bigint) DESC)"
        );
        ddl_conn.run('ANALYZE ' + table);
        done.add(key);
        rf.pop(key, None);
        _memo_track([name]);
        return True;
    } except Exception as e {
        rf[key] = _memo_refuse(rf.setdefault(key, {}), what, str(e), True);
        return False;
    } finally {
        if ddl_conn is not None {
            try {
                ddl_conn.close();
            } except Exception { }
        }
    }
}


# --- R6 adjacency projection -------------------------------------------------
# A typed hop's access path is idx_anchors_{src,dst}_typed, keyed
# (endpoint, arch_type, endpoint_type) INCLUDE (other endpoint) over EVERY edge
# row in the store. At SNB SF1 that is 11M entries / 539-561MB, of which the
# Knows edges a friendship hop actually wants are 180,665 (1.6%) - so the hop
# pays a wide-key btree descent one level deeper than its own edge type needs.
#
# Same rows, one index per (edge type, endpoint type): the two type equalities
# move OUT of the key and into the index PREDICATE, leaving a bare uuid key.
# 8.8MB instead of 550MB, and one descent level shorter. Measured on the SNB
# ic1 depth-3 Knows closure (2761 expansions, warm psql, n=10 interleaved):
# hop buffers 31,791 -> 25,902, recursion node 55.4ms -> 40.6ms (-27%), whole
# closure statement 71.8ms -> 57.3ms (-20%). Build is 2.1s for both at SF1 and
# needs no ANALYZE (a plain-column index's relpages/reltuples are set by
# CREATE INDEX itself).
#
# ponytail: the CALLER must spell those two equalities as LITERALS. Postgres
# only uses a partial index when it can PROVE the predicate, and `arch_type =
# :et` proves nothing once the statement goes generic-plan - the same lesson
# JAC_PROMOTED_DRIVE (c3377f78e) paid for. get_closure does exactly that and
# is the only caller. Two more ceilings: nothing ever drops these, so a store
# whose writes dominate its typed-hop reads pays index maintenance on every
# edge insert forever; and the build takes SHARE on `anchors`, blocking writes
# for those 2s the first time an edge type is traversed.
impl PgStore.ensure_adjacency_index(edge_type: str, node_type: str) -> bool {
    _memo_check(self);
    key = (edge_type, node_type);
    hit = _adj_state.get(key);
    if hit is True {
        return True;
    }
    if _memo_refused(hit) {
        return False;
    }
    what = f"adjacency index for {edge_type}/{node_type}";
    # interpolated into DDL below, and the caller interpolates the same two
    # strings into its WHERE clause - refuse anything not already a bare
    # identifier rather than quoting-by-guess (archetype names are CamelCase)
    if not _bare_ident(edge_type) or not _bare_ident(node_type) {
        _adj_state[key] = _memo_refuse(
            hit if isinstance(hit, dict) else {},
            what,
            'edge or node type is not a bare identifier',
            False
        );
        return False;
    }
    prev = _memo_attempt(hit if isinstance(hit, dict) else {});
    _adj_state[key] = prev;
    stem = 'idx_adj_' + _sanitize_ident(edge_type) + '_' + _sanitize_ident(node_type);
    ddl_conn: Any = None;
    try {
        self._ensure_ready();
        ddl_conn = self._connect();
        # same self-deadlock guard as the mirror DDL: the request that
        # triggered this already holds ACCESS SHARE on anchors
        ddl_conn.run("SET lock_timeout = '250ms'");
        ddl_conn.run(
            'CREATE INDEX IF NOT EXISTS ' + stem + '_src ON anchors (src) '
                + "INCLUDE (dst) WHERE arch_type = '" + edge_type
                + "' AND dst_type = '" + node_type + "'"
        );
        ddl_conn.run(
            'CREATE INDEX IF NOT EXISTS ' + stem + '_dst ON anchors (dst) '
                + "INCLUDE (src) WHERE arch_type = '" + edge_type
                + "' AND src_type = '" + node_type + "'"
        );
        _adj_state[key] = True;
        _memo_track([stem + '_src', stem + '_dst']);
        return True;
    } except Exception as e {
        # Retryable, not structural: unlike the endpoint COLUMN, an index is
        # either visible to the caller's snapshot and complete, or invisible
        # and the planner picks the wide index instead. Nothing can be
        # silently dropped from a result by a half-built one, so a busy-lock
        # failure is retried on the next closure - bounded by the try cap so a
        # permanently-failing DDL stops costing every request an attempt.
        _adj_state[key] = _memo_refuse(prev, what, str(e), True);
        return False;
    } finally {
        if ddl_conn is not None {
            try {
                ddl_conn.close();
            } except Exception { }
        }
    }
}


# --- R7 adjacency TABLE ------------------------------------------------------
# One rung above R6. R6 kept the edge rows where they were and gave the hop a
# narrow access path; R7 materialises the adjacency itself: `adj_<edge>`, two
# rows per edge (both directions), PK(src,dst). The closure's hop then stops
# being a two-arm `CROSS JOIN LATERAL (src-probe UNION ALL dst-probe)` and
# becomes ONE join against ONE index - because "the other direction" is a row
# now, not a second query. Measured on the SNB ic1 depth-3 Knows closure at SF1
# (PHASE_A.md, warm psql, n=7 interleaved): 2761+2761 Index Searches -> 2761,
# closure statement 43.3 -> 35.1ms (-18.8%) and 25,902 -> 9,022 buffers
# (-65.2%); whole ic1 statement 54.6 -> 38.4ms (-29.7%), 53,013 -> 9,687
# buffers (-81.7%). Storage is the honest price: 43MB (21MB table + 22MB PK)
# vs R6's 17.5MB of index, i.e. ~2.5x, because this is a second physical copy
# of the edge set rather than index pages over the first one.
#
# Maintenance is a pair of row triggers on `anchors` in the ensure_mirror
# idiom - the projection is kept correct by the DB, in the writer's own
# transaction, not by app code remembering to.
#
# ponytail: four declared ceilings.
#  - ONE table per EDGE type, claimed by the first endpoint type that asks. A
#    second endpoint type for the same edge would need its own row set; it is
#    refused (falls back to R6) rather than silently answered from the wrong
#    one.
#  - HOMOGENEOUS edges only. The closure's two arms filter dst_type on the
#    forward arm and src_type on the reverse, so an edge with only ONE endpoint
#    of the wanted type contributes in one direction only - which a symmetric
#    row pair cannot express. Probed for, and refused if found.
#  - endpoints are assumed IMMUTABLE: the UPDATE trigger re-inserts the current
#    pair but does not retract a previous one. No path in this runtime rewrites
#    an edge anchor's src/dst; add an OLD-pair delete here if one ever does.
#  - nothing ever drops it, so every edge insert of this type pays two extra
#    row inserts forever (measured at SF1, add_friendship n=50 with the trigger
#    live vs disabled: |delta| < 1.1ms on both client and server p50, i.e.
#    BELOW the fsync jitter floor - no rank claim).
#  - the memo is per PROCESS, so every boot re-pays the whole ensure: 1135ms
#    for the first ic1 of a boot at SF1 (502ms idempotent backfill + 307ms
#    completeness anti-join + 35ms ANALYZE + DDL no-ops), even when the table
#    is already complete. Absorbed by any warm pass, so left alone; the fix if
#    it ever matters is to run the completeness anti-join FIRST, on the
#    caller's own connection, and skip the DDL connection entirely when it
#    comes back empty (~310ms instead of 1135ms).
impl PgStore.ensure_adjacency_table(edge_type: str, node_type: str) -> (str | None) {
    _memo_check(self);
    st = _adjtbl_state.get(edge_type);
    if st is not None {
        if st['node'] != node_type {
            return None;
        }
        if st.get('ok') is True {
            return st['table'];
        }
        if _memo_refused(st) {
            return None;
        }
    }
    what = f"adjacency table for {edge_type}/{node_type}";
    prev = st if (st is not None and st.get('ok') is False) else {};
    prev['node'] = node_type;
    if not _bare_ident(edge_type) or not _bare_ident(node_type) {
        _adjtbl_state[edge_type] = _memo_refuse(
            prev, what, 'edge or node type is not a bare identifier', False
        );
        return None;
    }
    table = 'adj_' + _sanitize_ident(edge_type);
    _adjtbl_state[edge_type] = _memo_attempt(prev);
    # literal-inlined, not bound: these two strings are per-call-SITE constants
    # and both the DDL and the trigger WHEN clauses need them proven, not
    # merely equal - the same provability lesson ensure_adjacency_index and
    # JAC_PROMOTED_DRIVE paid for. Both went through _bare_ident above.
    et = "'" + edge_type + "'";
    nt = "'" + node_type + "'";
    rowset = (
        "e.kind = 'EdgeAnchor' AND e.arch_type = " + et
        + ' AND e.src_type = ' + nt + ' AND e.dst_type = ' + nt
        + ' AND e.src IS NOT NULL AND e.dst IS NOT NULL'
    );
    ddl_conn: Any = None;
    try {
        self._ensure_ready();
        ddl_conn = self._connect();
        # same self-deadlock guard as the mirror DDL: the request that
        # triggered this already holds ACCESS SHARE on anchors
        ddl_conn.run("SET lock_timeout = '250ms'");
        mixed = ddl_conn.run(
            "SELECT 1 FROM anchors e WHERE e.kind = 'EdgeAnchor' "
                + 'AND e.arch_type = ' + et
                + " AND (COALESCE(e.src_type, '') = " + nt
                + ") <> (COALESCE(e.dst_type, '') = " + nt + ') LIMIT 1'
        );
        if mixed {
            # structural, not transient: a symmetric row pair cannot express a
            # one-directional contribution. Cached as a refusal.
            _adjtbl_state[edge_type] = _memo_refuse(
                prev, what, 'edge type has mixed endpoint types', False
            );
            return None;
        }
        ddl_conn.run(
            'CREATE TABLE IF NOT EXISTS ' + table
                + ' (src uuid NOT NULL, dst uuid NOT NULL, '
                + 'PRIMARY KEY (src, dst))'
        );
        # DELETE retracts a direction only when NO other edge of this type
        # still justifies it (parallel edges between the same pair), so the
        # projection stays exactly `EXISTS an edge` rather than a refcount the
        # first delete would zero out. AFTER DELETE, so OLD's own row is
        # already gone and needs no exclusion.
        ddl_conn.run(
            'CREATE OR REPLACE FUNCTION ' + table + '_sync() RETURNS trigger '
                + 'AS $$ BEGIN IF TG_OP = ' + "'DELETE'" + ' THEN '
                + 'DELETE FROM ' + table + ' a WHERE (a.src, a.dst) IN '
                + '((OLD.src, OLD.dst), (OLD.dst, OLD.src)) '
                + 'AND NOT EXISTS (SELECT 1 FROM anchors e WHERE ' + rowset
                + ' AND ((e.src = a.src AND e.dst = a.dst) '
                + 'OR (e.src = a.dst AND e.dst = a.src))); '
                + 'RETURN OLD; END IF; '
                + 'INSERT INTO ' + table + ' (src, dst) VALUES '
                + '(NEW.src, NEW.dst), (NEW.dst, NEW.src) '
                + 'ON CONFLICT DO NOTHING; RETURN NEW; '
                + 'END $$ LANGUAGE plpgsql'
        );
        ddl_conn.run(
            'CREATE OR REPLACE TRIGGER ' + table + '_ins '
                + 'AFTER INSERT OR UPDATE ON anchors FOR EACH ROW '
                + "WHEN (NEW.kind = 'EdgeAnchor' AND NEW.arch_type = " + et
                + ' AND NEW.src_type = ' + nt + ' AND NEW.dst_type = ' + nt
                + ' AND NEW.src IS NOT NULL AND NEW.dst IS NOT NULL) '
                + 'EXECUTE FUNCTION ' + table + '_sync()'
        );
        ddl_conn.run(
            'CREATE OR REPLACE TRIGGER ' + table + '_del '
                + 'AFTER DELETE ON anchors FOR EACH ROW '
                + "WHEN (OLD.kind = 'EdgeAnchor' AND OLD.arch_type = " + et
                + ' AND OLD.src_type = ' + nt + ' AND OLD.dst_type = ' + nt
                + ' AND OLD.src IS NOT NULL AND OLD.dst IS NOT NULL) '
                + 'EXECUTE FUNCTION ' + table + '_sync()'
        );
        # triggers first, THEN backfill with DO NOTHING: a concurrent write is
        # already covered by the trigger, and re-inserting is idempotent.
        ddl_conn.run(
            'INSERT INTO ' + table + ' (src, dst) '
                + 'SELECT e.src, e.dst FROM anchors e WHERE ' + rowset
                + ' UNION '
                + 'SELECT e.dst, e.src FROM anchors e WHERE ' + rowset
                + ' ON CONFLICT DO NOTHING'
        );
        ddl_conn.run('ANALYZE ' + table);
    } except Exception as e {
        # transient (lock_timeout, concurrent claimer): retryable, bounded by
        # the same try cap as everything else.
        _adjtbl_state[edge_type] = _memo_refuse(prev, what, str(e), True);
        return None;
    } finally {
        if ddl_conn is not None {
            try {
                ddl_conn.close();
            } except Exception { }
        }
    }
    # Same hazard ensure_mirror guards, and it bites HARDER here than for an
    # index: the DDL committed on a connection of its own, so a request whose
    # snapshot was already taken sees the TABLE (catalog lookups resolve
    # against a fresh snapshot) but not the backfilled ROWS - and a missing
    # adjacency row does not fail, it silently drops nodes from the closure.
    # Confirm completeness from the caller's own snapshot; if it is not there
    # yet this request falls back to the R6 index path (correct, just slower)
    # and the next one - whose snapshot is newer than the backfill commit -
    # succeeds. Deliberately not cached, so the retry re-probes.
    incomplete = self._run(
        'SELECT 1 FROM anchors e WHERE ' + rowset + ' AND NOT EXISTS ('
            + 'SELECT 1 FROM ' + table + ' a '
            + 'WHERE a.src = e.src AND a.dst = e.dst) LIMIT 1',
        {}
    );
    if incomplete {
        return None;
    }
    _adjtbl_state[edge_type] = {'node': node_type, 'ok': True, 'table': table};
    _memo_track([table]);
    return table;
}


# --- R5b outbound endpoint column (item #23) ---------------------------------
# Same denormalisation as `src_endpoint` above, one hop the other way round:
# for `A -[E]-> B` (SNB authorship: `Post -[HasCreator]-> Person`) the mirror
# of A carries B's id as a scalar, so a top-K over "everything these B's
# authored" is an ordered index range scan per B instead of a join through
# `anchors` plus one mirror PK lookup per candidate (17876 lookups / 33701
# buffers / 109ms for SNB ic2 at SF1).
#
# Why this is a SEPARATE claim from `src_endpoint` and not a fourth probe on
# it: `src_endpoint`'s probe 1 asks "does exactly ONE edge archetype land on
# this node type", which is (a) the wrong direction for authorship - HasCreator
# points OUT of Post - and (b) the wrong QUESTION. What makes a scalar column
# correct is a per-edge-type cardinality property, not a whole-node-type
# uniqueness property. Post has >=3 inbound edge types (ContainerOf, ReplyOf,
# Likes) and would be refused forever while still satisfying "every Post has
# exactly one HasCreator". So the claim here is keyed by (edge type,
# direction), the edge type is NAMED by the caller rather than derived, and
# the probes are:
#   C1 no A has two outbound E edges          (the column has room for one dst)
#   C2 no undirected edge touches A on either end
# and the trigger below keeps C1 true for every FUTURE write instead of
# trusting the claim-time snapshot - which is the hole the `src_endpoint`
# ponytail note above admits and parks behind a flag.
#
# On violation the trigger does NOT just NULL the column: a NULL is
# indistinguishable from "no edge", so the violating node would silently
# vanish from a legitimate author's page - the exact wrong-answer class the
# refusal policy forbids. It records the source in `jac_ep_violation` and
# get_topk_inbound gates its fast arm on that table being empty for this
# (mirror, edge type), with the ordinary edge-join arm gated the other way.
# Both guards are uncorrelated subqueries, so postgres evaluates them once per
# statement as a One-Time Filter and skips the disabled arm's children
# entirely; the cost when nothing is wrong is one seq scan of a 0-page table.
#
# ponytail: the claim never un-refuses. Deleting the extra edge leaves the
# `jac_ep_violation` row in place and this (mirror, edge type) stays on the
# slow arm until the row is removed by hand or the memo guard clears. Correct
# and boring; automatic recovery would need a full re-verification pass, and
# a violation is supposed to be a bug in the app, not a routine event.
def _ensure_ep_outbound(
    store: Any, cls: type, edge_type: str, order_col: str
) -> (str | None) {
    st = _mirror_state.get(cls);
    if not st or not st['ok'] {
        return None;
    }
    at = getattr(cls, '__name__', '');
    what = f"outbound endpoint column for {at} -[{edge_type}]->";
    # everything below is interpolated into DDL; refuse anything that is not
    # already a bare identifier rather than quoting-by-guess. An unnamed edge
    # type is refused outright: unlike the inbound claim there is nothing to
    # derive it from, and guessing a direction AND a type is not a proof.
    if (
        not edge_type
        or not _bare_ident(edge_type)
        or not _bare_ident(order_col)
        or not _bare_ident(at)
    ) {
        _memo_log_once(
            what,
            'refused (an outbound endpoint claim needs a named edge type, and'
                ' edge type / order column / node type must all be bare'
                ' identifiers)'
        );
        return None;
    }
    col = 'dst_endpoint_' + _sanitize_ident(edge_type);
    claims = st.setdefault('epo', {});
    claim = claims.get(edge_type);
    if claim is not None and order_col in claim['ords'] {
        return col;
    }
    rf = st.setdefault('epo_refuse', {});
    if _memo_refused(rf.get(edge_type)) {
        return None;   # kept failing; stop paying for the attempt
    }
    table = st['table'];
    _memo_attempt(rf.setdefault(edge_type, {}));
    ddl_conn: Any = None;
    short = False;
    try {
        store._ensure_ready();
        ddl_conn = store._connect();
        # same self-deadlock guard as ensure_mirror_endpoint: ADD COLUMN wants
        # ACCESS EXCLUSIVE and the request that triggered this may already
        # hold ACCESS SHARE on the same mirror. Fail fast, let a later request
        # holding no such lock do it.
        ddl_conn.run("SET lock_timeout = '250ms'");
        # The claim is DURABLE: the column plus a live trigger maintaining it
        # is the database's own record that C1/C2 were proved and have been
        # enforced on every write since. Re-deriving that in a fresh process
        # costs MINUTES at SNB SF1 (the C1 GROUP BY has no supporting index),
        # and would be paid on the first request after every boot, so the
        # catalog answers instead - two syscache lookups. `epo_full` is the
        # escape hatch: if the completeness anti-join below ever fails after a
        # shortcut, the next attempt takes the full path and re-backfills
        # (edges bulk-COPYed into a surviving mirror with triggers suppressed
        # is exactly that case).
        trig = table + '_epo_' + _sanitize_ident(edge_type) + '_iu';
        if claim is None and edge_type not in st.get('epo_full', set()) {
            have = ddl_conn.run(
                'SELECT (SELECT count(*) FROM pg_attribute a WHERE a.attrelid'
                    + " = to_regclass('" + table + "') AND a.attname = '" + col
                    + "' AND NOT a.attisdropped) + (SELECT count(*) FROM"
                    + " pg_trigger t WHERE t.tgname = '" + trig
                    + "' AND NOT t.tgisinternal)"
            );
            short = bool(have) and int(have[0][0]) == 2;
        }
        # The two probes below are minutes of work at SNB SF1 (a GROUP BY over
        # 3M edge rows), and the ADD COLUMN after them fails with a lock
        # timeout on the FIRST request that also built the mirror - that
        # request is still holding ACCESS SHARE on it from ensure_mirror's own
        # completeness probe, exactly as the guard above intends. So the SHAPE
        # verdict is memoised separately from the BUILD: the retry that lands
        # on a request holding no such lock re-runs the DDL, not the proof.
        proven = st.setdefault('epo_proven', set());
        if claim is None and not short and edge_type not in proven {
            # C1: cardinality. Stricter than "one creator" on purpose - two
            # edges to the SAME dst also trip it, and that is exactly the case
            # where the column arm (one row) and the edge-join arm (the row
            # twice) would disagree.
            multi = ddl_conn.run(
                "SELECT 1 FROM anchors WHERE kind = 'EdgeAnchor' AND arch_type = '"
                    + edge_type + "' AND src_type = '" + at + "' "
                    + 'AND src IS NOT NULL '
                    + 'GROUP BY src HAVING count(*) > 1 LIMIT 1'
            );
            if multi {
                rf[edge_type] = _memo_refuse(
                    rf.get(edge_type) or {}, what,
                    'C1 cardinality: a ' + at + ' already has two outbound '
                        + edge_type + ' edges',
                    False
                );
                return None;
            }
            # C2: an undirected edge stored either way round is traversable
            # both ways, and one column cannot represent that.
            bad = ddl_conn.run(
                "SELECT 1 FROM anchors WHERE kind = 'EdgeAnchor' AND undirected "
                    + "AND (src_type = '" + at + "' OR dst_type = '" + at
                    + "') LIMIT 1"
            );
            if bad {
                rf[edge_type] = _memo_refuse(
                    rf.get(edge_type) or {}, what,
                    'C2: an undirected edge touches this type', False
                );
                return None;
            }
            proven.add(edge_type);
        }
        # unconditional: get_topk_inbound's fallback guard reads this table on
        # every statement, so it has to exist on the shortcut path too
        ddl_conn.run(
            'CREATE TABLE IF NOT EXISTS jac_ep_violation ('
                + 'tbl text NOT NULL, edge_type text NOT NULL, '
                + 'src uuid NOT NULL, '
                + 'noticed_at timestamptz NOT NULL DEFAULT now(), '
                + 'PRIMARY KEY (tbl, edge_type, src))'
        );
        if claim is None and not short {
            ddl_conn.run(
                'ALTER TABLE ' + table + ' ADD COLUMN IF NOT EXISTS ' + col
                    + ' uuid'
            );
            # Maintained inside the writer's own transaction, driven off the
            # EDGE row. UPDATE and DELETE both retract what OLD contributed
            # first, so an UPDATE is (retract, re-assert) and can never look
            # like a second edge - which is what makes the violation test
            # below free: "the column already holds a DIFFERENT non-null
            # value" IS the second-edge signal, no probe of `anchors` needed.
            # The read takes FOR UPDATE so two concurrent inserters against an
            # existing mirror row serialise and the second one sees, and
            # flags, the first's value.
            # Upsert rather than update: the node row and its edge land in the
            # same flush with no ordering guarantee between them, and the node
            # trigger's own ON CONFLICT set-list does not mention this column,
            # so neither clobbers the other.
            ddl_conn.run(
                'CREATE OR REPLACE FUNCTION ' + table + '_epo_'
                    + _sanitize_ident(edge_type)
                    + '() RETURNS trigger AS $jacepo$ '
                    + 'DECLARE cur uuid; BEGIN '
                    # The mirror can be DROPPED behind this trigger's back -
                    # pg_bulk_load.py --mode full drops every g_n_* table and
                    # CASCADEs only the <mirror>_sync function, not this one -
                    # which would otherwise turn every later edge write into
                    # "relation does not exist". Nothing to maintain when the
                    # projection is gone; ensure_mirror rebuilds it and this
                    # ensure re-backfills before any reader can use it again.
                    + "IF to_regclass('" + table
                    + "') IS NULL THEN RETURN COALESCE(NEW, OLD); END IF; "
                    + "IF TG_OP <> 'INSERT' THEN "
                    + 'UPDATE ' + table + ' SET ' + col + ' = NULL '
                    + 'WHERE id = OLD.src AND ' + col + ' = OLD.dst; '
                    + "IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; "
                    + 'END IF; '
                    + 'SELECT ' + col + ' INTO cur FROM ' + table
                    + ' WHERE id = NEW.src FOR UPDATE; '
                    + 'IF cur IS NOT NULL AND cur <> NEW.dst THEN '
                    + 'INSERT INTO jac_ep_violation (tbl, edge_type, src) '
                    + "VALUES ('" + table + "', '" + edge_type + "', NEW.src) "
                    + 'ON CONFLICT DO NOTHING; '
                    + 'UPDATE ' + table + ' SET ' + col + ' = NULL '
                    + 'WHERE id = NEW.src; '
                    + "RAISE WARNING 'jac: " + table + '.' + col
                    + ' cardinality violated at % - a second ' + edge_type
                    + ' edge appeared; endpoint column disabled for this'
                    + " mirror', NEW.src; "
                    + 'RETURN NEW; END IF; '
                    + 'INSERT INTO ' + table + ' (id, ' + col + ') '
                    + 'VALUES (NEW.src, NEW.dst) ON CONFLICT (id) DO UPDATE '
                    + 'SET ' + col + ' = EXCLUDED.' + col + '; '
                    + 'RETURN NEW; END $jacepo$ LANGUAGE plpgsql'
            );
            ddl_conn.run(
                'CREATE OR REPLACE TRIGGER ' + table + '_epo_'
                    + _sanitize_ident(edge_type) + '_iu '
                    + 'AFTER INSERT OR UPDATE ON anchors FOR EACH ROW '
                    + "WHEN (NEW.kind = 'EdgeAnchor' AND NEW.arch_type = '"
                    + edge_type + "' AND NEW.src_type = '" + at + "') "
                    + 'EXECUTE FUNCTION ' + table + '_epo_'
                    + _sanitize_ident(edge_type) + '()'
            );
            ddl_conn.run(
                'CREATE OR REPLACE TRIGGER ' + table + '_epo_'
                    + _sanitize_ident(edge_type) + '_d '
                    + 'AFTER DELETE ON anchors FOR EACH ROW '
                    + "WHEN (OLD.kind = 'EdgeAnchor' AND OLD.arch_type = '"
                    + edge_type + "' AND OLD.src_type = '" + at + "') "
                    + 'EXECUTE FUNCTION ' + table + '_epo_'
                    + _sanitize_ident(edge_type) + '()'
            );
            # triggers first, THEN backfill: a concurrent write is already
            # covered by the trigger and re-setting the same value is
            # idempotent
            ddl_conn.run(
                'UPDATE ' + table + ' m SET ' + col + ' = e.dst FROM anchors e '
                    + "WHERE e.src = m.id AND e.kind = 'EdgeAnchor' "
                    + "AND e.arch_type = '" + edge_type + "' "
                    + "AND e.src_type = '" + at + "' "
                    + 'AND m.' + col + ' IS DISTINCT FROM e.dst'
            );
        }
        if claim is None {
            claim = {'ords': set()};
            claims[edge_type] = claim;
        }
        # (endpoint, order DESC). The order expression MUST stay textually
        # identical to get_topk_inbound's ord_expr or the planner cannot prove
        # the match - the same lesson JAC_PROMOTED_DRIVE and ensure_topk_index
        # already paid for. That is also why this index is built here and not
        # by ensure_topk_index: the source here is a plain uuid column, not
        # that one's `#>> '{}'` expression.
        iname = (
            table + '_epo_' + _sanitize_ident(edge_type) + '_'
                + _sanitize_ident(order_col)
        );
        ddl_conn.run(
            'CREATE INDEX IF NOT EXISTS ' + iname + ' ON ' + table
                + ' (' + col + ', (((' + order_col + " #>> '{}'))::bigint) DESC)"
        );
        if not short {
            ddl_conn.run('ANALYZE ' + table);
        }
        # Same hazard ensure_mirror_endpoint guards: the DDL and backfill
        # committed on a connection of their own, so a request whose snapshot
        # predates that commit sees the COLUMN but not the VALUES - and a NULL
        # does not fail, it silently drops the row from the page. Confirm
        # completeness from the caller's own snapshot. `src_type` scoping is
        # required and not optional: HasCreator originates from BOTH Post and
        # Comment, so the Post mirror's probe must not be failed by Comment's
        # edges. Deliberately not cached, so the retry re-probes.
        incomplete = store._run(
            "SELECT 1 FROM anchors e WHERE e.kind = 'EdgeAnchor' "
                + 'AND e.arch_type = :et AND e.src_type = :at '
                + 'AND e.src IS NOT NULL AND NOT EXISTS ('
                + 'SELECT 1 FROM ' + table + ' m '
                + 'WHERE m.id = e.src AND m.' + col + ' = e.dst) LIMIT 1',
            {'et': edge_type, 'at': at}
        );
        if incomplete {
            if short {
                # the shortcut trusted a column the data does not back; make
                # the next attempt do the probes and the backfill for real
                st.setdefault('epo_full', set()).add(edge_type);
                claims.pop(edge_type, None);
            }
            return None;
        }
        claim['ords'].add(order_col);
        rf.pop(edge_type, None);
        st.setdefault('epo_full', set()).discard(edge_type);
        _memo_track([iname, 'jac_ep_violation']);
        return col;
    } except Exception as e {
        # transient (lock_timeout, a concurrent claimer) vs structural: both
        # look like an exception here, so retry a bounded number of times
        # rather than poisoning the claim on the first busy moment.
        rf[edge_type] = _memo_refuse(
            rf.setdefault(edge_type, {}), what, str(e), True
        );
        return None;
    } finally {
        if ddl_conn is not None {
            try {
                ddl_conn.close();
            } except Exception { }
        }
    }
}


# --- R8 write-once parent-chase root column (item #22) -----------------------
# A walker that climbs `cur -[E]-> parent` until it reaches a node of type R
# (SNB is2: Comment -ReplyOf-> ... -> Post) pays one round trip per hop. The
# chain is write-once in every workload that has one (SNB never re-parents a
# message), so the answer is a constant of the row: materialise `root_of_<E>`
# on the chased type's mirror, computed at edge-INSERT time from the PARENT'S
# already-stored root (O(1) per insert), backfilled once by a recursive CTE.
#
# Soundness WITHOUT trusting write-once: a non-NULL value is only ever written
# by (a) the backfill (correct at build) or (b) the insert trigger reading the
# parent's committed root - so it can only go stale if an E edge is RE-PARENTED
# or DELETED, and both of those poison the claim via jac_ep_violation (same
# table + reader-gate idiom as the endpoint column above; descendants are
# never recomputed, the whole (mirror, E) simply drops to the chase arm).
# A NULL value promises nothing: readers resolve those rows through the
# always-correct recursive-CTE fallback. So write-once is the OPTIMIZATION
# precondition (it keeps the fast arm populated), never a safety one.
#
# Flush-order hazard the trigger absorbs: a chain a->b->c created in ONE
# flush can insert c's edge before b's root exists - c then gets NULL and
# costs a chase at read time, which is slow-correct, not wrong.
def _ensure_root_column(
    store: Any, cls: type, edge_type: str, rt_name: str
) -> (str | None) {
    st = _mirror_state.get(cls);
    if not st or not st['ok'] {
        return None;
    }
    ct = getattr(cls, '__name__', '');
    what = f"root column for {ct} -[{edge_type}]->* {rt_name}";
    if (
        not edge_type
        or not rt_name
        or not _bare_ident(edge_type)
        or not _bare_ident(rt_name)
        or not _bare_ident(ct)
    ) {
        _memo_log_once(
            what,
            'refused (a root claim needs bare-identifier edge type, chased'
                ' type and root type)'
        );
        return None;
    }
    col = 'root_of_' + _sanitize_ident(edge_type);
    claims = st.setdefault('rootcol', {});
    if claims.get(edge_type) {
        return col;
    }
    rf = st.setdefault('rootcol_refuse', {});
    if _memo_refused(rf.get(edge_type)) {
        return None;
    }
    table = st['table'];
    _memo_attempt(rf.setdefault(edge_type, {}));
    ddl_conn: Any = None;
    short = False;
    fname = table + '_root_' + _sanitize_ident(edge_type);
    trig = fname + '_iu';
    try {
        store._ensure_ready();
        ddl_conn = store._connect();
        ddl_conn.run("SET lock_timeout = '250ms'");
        # durable-claim shortcut, exactly the endpoint column's: column +
        # trigger existing IS the record that the probes held and every write
        # since has been enforced
        if edge_type not in st.get('rootcol_full', set()) {
            have = ddl_conn.run(
                'SELECT (SELECT count(*) FROM pg_attribute a WHERE a.attrelid'
                    + " = to_regclass('" + table + "') AND a.attname = '" + col
                    + "' AND NOT a.attisdropped) + (SELECT count(*) FROM"
                    + " pg_trigger t WHERE t.tgname = '" + trig
                    + "' AND NOT t.tgisinternal)"
            );
            short = bool(have) and int(have[0][0]) == 2;
        }
        proven = st.setdefault('rootcol_proven', set());
        if not short and edge_type not in proven {
            # C1 cardinality: one outbound E per chased node, or the chase
            # itself is ambiguous and no scalar column can hold the answer
            multi = ddl_conn.run(
                "SELECT 1 FROM anchors WHERE kind = 'EdgeAnchor' AND arch_type = '"
                    + edge_type + "' AND src_type = '" + ct + "' "
                    + 'AND src IS NOT NULL '
                    + 'GROUP BY src HAVING count(*) > 1 LIMIT 1'
            );
            if multi {
                rf[edge_type] = _memo_refuse(
                    rf.get(edge_type) or {}, what,
                    'C1 cardinality: a ' + ct + ' already has two outbound '
                        + edge_type + ' edges',
                    False
                );
                return None;
            }
            # C2: undirected E is traversable both ways - not a parent chain
            bad = ddl_conn.run(
                "SELECT 1 FROM anchors WHERE kind = 'EdgeAnchor' AND undirected "
                    + "AND arch_type = '" + edge_type + "' LIMIT 1"
            );
            if bad {
                rf[edge_type] = _memo_refuse(
                    rf.get(edge_type) or {}, what,
                    'C2: ' + edge_type + ' has undirected rows', False
                );
                return None;
            }
            # C3: the chain must be closed over {chased, root} - an E edge
            # landing on any OTHER type makes "the chain's root" undefined
            stray = ddl_conn.run(
                "SELECT 1 FROM anchors WHERE kind = 'EdgeAnchor' AND arch_type = '"
                    + edge_type + "' AND src_type = '" + ct + "' "
                    + "AND dst_type NOT IN ('" + ct + "', '" + rt_name + "') "
                    + 'LIMIT 1'
            );
            if stray {
                rf[edge_type] = _memo_refuse(
                    rf.get(edge_type) or {}, what,
                    'C3: an ' + edge_type + ' edge leaves the {' + ct + ', '
                        + rt_name + '} chain',
                    False
                );
                return None;
            }
            proven.add(edge_type);
        }
        ddl_conn.run(
            'CREATE TABLE IF NOT EXISTS jac_ep_violation ('
                + 'tbl text NOT NULL, edge_type text NOT NULL, '
                + 'src uuid NOT NULL, '
                + 'noticed_at timestamptz NOT NULL DEFAULT now(), '
                + 'PRIMARY KEY (tbl, edge_type, src))'
        );
        if not short {
            ddl_conn.run(
                'ALTER TABLE ' + table + ' ADD COLUMN IF NOT EXISTS ' + col
                    + ' uuid'
            );
            # INSERT (and the runtime's idempotent edge re-upsert, which
            # arrives as an UPDATE with src/dst unchanged) recomputes the one
            # affected row from the parent's stored root. A REAL re-parent or
            # a DELETE would stale every descendant transitively, so it
            # poisons the claim instead of pretending to fix it.
            ddl_conn.run(
                'CREATE OR REPLACE FUNCTION ' + fname
                    + '() RETURNS trigger AS $jacroot$ '
                    + 'DECLARE r uuid; BEGIN '
                    + "IF to_regclass('" + table
                    + "') IS NULL THEN RETURN COALESCE(NEW, OLD); END IF; "
                    + "IF TG_OP = 'DELETE' OR (TG_OP = 'UPDATE' AND "
                    + '(OLD.src IS DISTINCT FROM NEW.src OR '
                    + 'OLD.dst IS DISTINCT FROM NEW.dst)) THEN '
                    + 'INSERT INTO jac_ep_violation (tbl, edge_type, src) '
                    + "VALUES ('" + table + "', '" + edge_type + "', OLD.src) "
                    + 'ON CONFLICT DO NOTHING; '
                    + "RAISE WARNING 'jac: " + table + '.' + col + ' chain '
                    + 'edge mutated at % (%); root column disabled for this '
                    + "mirror', OLD.src, TG_OP; "
                    + 'RETURN COALESCE(NEW, OLD); END IF; '
                    + "IF NEW.dst_type = '" + rt_name + "' THEN r := NEW.dst; "
                    + 'ELSE SELECT ' + col + ' INTO r FROM ' + table
                    + ' WHERE id = NEW.dst; END IF; '
                    + 'IF r IS NULL THEN RETURN NEW; END IF; '
                    + 'INSERT INTO ' + table + ' (id, ' + col + ') '
                    + 'VALUES (NEW.src, r) ON CONFLICT (id) DO UPDATE '
                    + 'SET ' + col + ' = EXCLUDED.' + col + '; '
                    + 'RETURN NEW; END $jacroot$ LANGUAGE plpgsql'
            );
            ddl_conn.run(
                'CREATE OR REPLACE TRIGGER ' + trig
                    + ' AFTER INSERT OR UPDATE ON anchors FOR EACH ROW '
                    + "WHEN (NEW.kind = 'EdgeAnchor' AND NEW.arch_type = '"
                    + edge_type + "' AND NEW.src_type = '" + ct + "') "
                    + 'EXECUTE FUNCTION ' + fname + '()'
            );
            ddl_conn.run(
                'CREATE OR REPLACE TRIGGER ' + fname + '_d '
                    + 'AFTER DELETE ON anchors FOR EACH ROW '
                    + "WHEN (OLD.kind = 'EdgeAnchor' AND OLD.arch_type = '"
                    + edge_type + "' AND OLD.src_type = '" + ct + "') "
                    + 'EXECUTE FUNCTION ' + fname + '()'
            );
            # triggers first, THEN backfill (concurrent writes covered by the
            # trigger; re-setting the same value is idempotent). ONE recursive
            # CTE resolves every chased row's root; depth-capped so a cyclic
            # chain (impossible in a forest, cheap to be safe against) leaves
            # NULLs - the chase arm - rather than spinning.
            ddl_conn.run(
                'WITH RECURSIVE chase(sid, cur, ctype, d) AS ('
                    + 'SELECT e.src, e.dst, e.dst_type, 1 FROM anchors e '
                    + "WHERE e.kind = 'EdgeAnchor' AND e.arch_type = '"
                    + edge_type + "' AND e.src_type = '" + ct + "' "
                    + 'AND e.src IS NOT NULL AND e.dst IS NOT NULL '
                    + 'UNION ALL '
                    + 'SELECT c.sid, e.dst, e.dst_type, c.d + 1 FROM chase c '
                    + "JOIN anchors e ON e.kind = 'EdgeAnchor' "
                    + "AND e.arch_type = '" + edge_type + "' "
                    + 'AND e.src = c.cur '
                    + "WHERE c.ctype <> '" + rt_name + "' AND c.d < 64) "
                    + 'UPDATE ' + table + ' m SET ' + col + ' = c.cur '
                    + "FROM chase c WHERE c.ctype = '" + rt_name + "' "
                    + 'AND m.id = c.sid AND m.' + col
                    + ' IS DISTINCT FROM c.cur'
            );
            ddl_conn.run('ANALYZE ' + table);
        }
        # completeness sanity from the caller's own snapshot, depth-1 subset:
        # every DIRECT chased->root edge must be reflected. Deeper rows may
        # legitimately be NULL (flush-order, depth cap) - readers chase those.
        incomplete = store._run(
            "SELECT 1 FROM anchors e JOIN " + table + ' m ON m.id = e.src '
                + "WHERE e.kind = 'EdgeAnchor' AND e.arch_type = :et "
                + "AND e.src_type = :ct AND e.dst_type = :rt "
                + 'AND m.' + col + ' IS DISTINCT FROM e.dst LIMIT 1',
            {'et': edge_type, 'ct': ct, 'rt': rt_name}
        );
        if incomplete {
            if short {
                st.setdefault('rootcol_full', set()).add(edge_type);
            }
            return None;
        }
        claims[edge_type] = True;
        rf.pop(edge_type, None);
        st.setdefault('rootcol_full', set()).discard(edge_type);
        _memo_track(['jac_ep_violation']);
        return col;
    } except Exception as e {
        rf[edge_type] = _memo_refuse(
            rf.setdefault(edge_type, {}), what, str(e), True
        );
        if '55P03' in str(e) {
            # mid-request lock timeout: the CALLER's own snapshot holds
            # ACCESS SHARE on this mirror (jroot runs after jtopk read it),
            # so this attempt could never win. get_roots registers a
            # post-commit retry that runs seconds from now with the lock
            # released - don't cool that retry down.
            rf[edge_type]['retry_at'] = 0.0;
        }
        return None;
    } finally {
        if ddl_conn is not None {
            try {
                ddl_conn.close();
            } except Exception { }
        }
    }
}


# --- R5 endpoint column ------------------------------------------------------
# A stream chain's final hop is `<prev node> -[E]-> <mirrored node>`, and the
# generic form has to join `anchors` to walk it: for a 50-source page that is
# one index scan per source PLUS one mirror PK lookup per candidate row - at
# t200 that is 10,000 lookups / 32,126 buffers to return 60 rows, because the
# sort column only exists on the mirror and the planner cannot cut before the
# join (EXPLAIN, PROGRESS.log PHASE10).
#
# `src_endpoint` denormalises the E-edge's src onto the mirror row, so the
# final hop becomes an index range scan of (src_endpoint, <sort col>) that
# stops after `cap` rows per source: 3,000 rows / 684 buffers for the same
# page, 22.9ms -> 3.8ms.
#
# The column is single-valued, so it is CLAIMED by exactly one edge archetype
# per mirror. The claiming edge type is DERIVED from live data rather than
# taken on trust, because the hop that wants it is usually untyped
# (`[-->(?:Tweet)]`). Three probes must all hold, or the mirror is marked
# never-claimable and every query keeps the flat join:
#   1. exactly ONE edge archetype lands on this node type
#   2. no edge touching this node type on EITHER end is undirected (one
#      column cannot represent a hop that is traversable both ways)
#   3. no node of this type currently has two inbound edges of that type
#      (the column has room for one src)
# If the hop DOES name an edge type it must equal the derived one.
#
# ponytail: probe 3 is checked at claim time and never again - nothing stops
# a later write from giving a node a second inbound edge, after which
# src_endpoint holds whichever src was written last and that node's rows can
# go missing from a page. The sound version is a real (src, dst, sort)
# adjacency index rather than a column; that, and having the compiler plan
# which mirrors get one instead of the first stream query claiming it
# lazily, are the upgrade path. Keep this flag-gated until then.
impl PgStore.ensure_root_column(
    cls: type, edge_type: str, root_type: str
) -> (str | None) {
    return _ensure_root_column(self, cls, edge_type, root_type);
}


impl PgStore.ensure_mirror_endpoint(
    cls: type, edge_type: str, order_col: str, outbound: bool = False
) -> (str | None) {
    if outbound {
        # `A -[E]-> B`, the hop the other way round: a separate claim keyed by
        # (edge type, direction) with its own probes and its own trigger.
        # Nothing below this line changes for the inbound/untyped path.
        return _ensure_ep_outbound(self, cls, edge_type, order_col);
    }
    st = _mirror_state.get(cls);
    if not st or not st['ok'] {
        return None;
    }
    claim = st.get('ep');
    if claim is not None {
        # claimed: usable only by the edge type it was built for (an untyped
        # hop passes ''), and only once an index exists for THIS sort column
        if not claim['edge'] or (edge_type and claim['edge'] != edge_type) {
            return None;
        }
        if order_col in claim['ords'] {
            return 'src_endpoint';
        }
    }
    # interpolated into DDL below; refuse anything that is not already a bare
    # identifier rather than quoting-by-guess
    if not _bare_ident(order_col) or (edge_type and not _bare_ident(edge_type)) {
        return None;
    }
    table = st['table'];
    at = getattr(cls, '__name__', '');
    what = f"mirror endpoint column for {at}";
    if _memo_refused(st.get('ep_refuse')) {
        return None;   # kept failing; stop paying for the attempt
    }
    _memo_attempt(st.setdefault('ep_refuse', {}));
    ddl_conn: Any = None;
    try {
        self._ensure_ready();
        ddl_conn = self._connect();
        # ADD COLUMN needs ACCESS EXCLUSIVE on the mirror, and the request
        # that triggered this may already hold ACCESS SHARE on it (e.g. the
        # ensure_mirror completeness probe runs on the request's own
        # connection). Without a lock_timeout the DDL waits on the very
        # request that is waiting for it, until the CLIENT times out - which
        # then strands the backend and blocks every later attempt too.
        # Fail fast and let a later request, holding no such lock, do it.
        ddl_conn.run("SET lock_timeout = '250ms'");
        if claim is None {
            # `refuse` = the shape itself cannot be represented by one column,
            # which no retry changes; an EXCEPTION below is a different thing
            # (busy lock) and is retried, hence the marker is only set here.
            refuse = {'edge': '', 'ords': set()};
            kinds = ddl_conn.run(
                "SELECT DISTINCT arch_type FROM anchors WHERE kind = 'EdgeAnchor' "
                    + "AND dst_type = '" + at + "' LIMIT 2"
            );
            if len(kinds) != 1 {
                st['ep'] = refuse;
                _memo_log_once(
                    what, 'refused (probe 1: not exactly one inbound edge type)'
                );
                return None;
            }
            derived = str(kinds[0][0]);
            if (
                not _bare_ident(derived)
                or (edge_type and derived != edge_type)
            ) {
                st['ep'] = refuse;
                _memo_log_once(
                    what,
                    f"refused (derived edge type '{derived}' is not a bare"
                        f" identifier, or does not match the hop's '{edge_type}')"
                );
                return None;
            }
            edge_type = derived;
            # either endpoint: an undirected edge stored as src=<at> is still
            # traversable INTO <at>, and probe 1's dst_type scan cannot see it
            bad = ddl_conn.run(
                "SELECT 1 FROM anchors WHERE kind = 'EdgeAnchor' AND undirected "
                    + "AND (dst_type = '" + at + "' OR src_type = '" + at + "') LIMIT 1"
            );
            if bad {
                st['ep'] = refuse;
                _memo_log_once(
                    what, 'refused (probe 2: an undirected edge touches this type)'
                );
                return None;
            }
            multi = ddl_conn.run(
                "SELECT 1 FROM anchors WHERE kind = 'EdgeAnchor' AND arch_type = '"
                    + edge_type + "' AND dst IS NOT NULL "
                    + 'GROUP BY dst HAVING count(*) > 1 LIMIT 1'
            );
            if multi {
                st['ep'] = refuse;
                _memo_log_once(
                    what, 'refused (probe 3: a node has two inbound edges)'
                );
                return None;
            }
            ddl_conn.run(
                'ALTER TABLE ' + table + ' ADD COLUMN IF NOT EXISTS src_endpoint uuid'
            );
            # Maintained by the same in-transaction trigger discipline as the
            # rest of the mirror, but driven off the EDGE row rather than the
            # node row. The node row and its edge land in the same flush with
            # no ordering guarantee between them, so this upserts rather than
            # updates; the node trigger's own ON CONFLICT list does not
            # mention src_endpoint, so neither clobbers the other.
            ddl_conn.run(
                'CREATE OR REPLACE FUNCTION ' + table + '_ep() RETURNS trigger AS $$ '
                    + "BEGIN IF TG_OP = 'DELETE' THEN "
                    + 'UPDATE ' + table + ' SET src_endpoint = NULL '
                    + 'WHERE id = OLD.dst AND src_endpoint = OLD.src; RETURN OLD; '
                    + 'END IF; '
                    + 'INSERT INTO ' + table + ' (id, src_endpoint) '
                    + 'VALUES (NEW.dst, NEW.src) ON CONFLICT (id) DO UPDATE SET '
                    + 'src_endpoint = EXCLUDED.src_endpoint; RETURN NEW; '
                    + 'END $$ LANGUAGE plpgsql'
            );
            ddl_conn.run(
                'CREATE OR REPLACE TRIGGER ' + table + '_ep_ins '
                    + 'AFTER INSERT OR UPDATE ON anchors FOR EACH ROW '
                    + "WHEN (NEW.kind = 'EdgeAnchor' AND NEW.arch_type = '"
                    + edge_type + "' AND NEW.dst_type = '" + at + "') "
                    + 'EXECUTE FUNCTION ' + table + '_ep()'
            );
            ddl_conn.run(
                'CREATE OR REPLACE TRIGGER ' + table + '_ep_del '
                    + 'AFTER DELETE ON anchors FOR EACH ROW '
                    + "WHEN (OLD.kind = 'EdgeAnchor' AND OLD.arch_type = '"
                    + edge_type + "' AND OLD.dst_type = '" + at + "') "
                    + 'EXECUTE FUNCTION ' + table + '_ep()'
            );
            # triggers first, THEN backfill: a concurrent write is already
            # covered by the trigger, and re-setting it to the same value is
            # idempotent
            ddl_conn.run(
                'UPDATE ' + table + ' m SET src_endpoint = e.src FROM anchors e '
                    + 'WHERE e.dst = m.id AND e.kind = ' + "'EdgeAnchor' "
                    + 'AND e.arch_type = ' + "'" + edge_type + "' "
                    + 'AND m.src_endpoint IS DISTINCT FROM e.src'
            );
            claim = {'edge': edge_type, 'ords': set()};
            st['ep'] = claim;
        }
        ddl_conn.run(
            'CREATE INDEX IF NOT EXISTS ' + table + '_ep_' + order_col
                + ' ON ' + table + ' (src_endpoint, ' + order_col + ')'
        );
        ddl_conn.run('ANALYZE ' + table);
        # Same hazard ensure_mirror guards, and worse here: the DDL and
        # backfill committed on a connection of their own, so a request whose
        # snapshot was already taken sees the COLUMN (catalog lookups resolve
        # against a fresh snapshot) but not the backfilled VALUES - and a NULL
        # src_endpoint does not fail, it silently drops that row from the
        # page. Confirm completeness from the caller's own snapshot; if it is
        # not there yet, this request falls back to the flat join and the next
        # one - whose snapshot is newer than the backfill commit - succeeds.
        # Deliberately not cached, so the retry re-probes.
        incomplete = self._run(
            "SELECT 1 FROM anchors e WHERE e.kind = 'EdgeAnchor' "
                + 'AND e.arch_type = :et AND e.dst IS NOT NULL AND NOT EXISTS ('
                + 'SELECT 1 FROM ' + table + ' m '
                + 'WHERE m.id = e.dst AND m.src_endpoint = e.src) LIMIT 1',
            {'et': claim['edge']}
        );
        if incomplete {
            return None;
        }
        claim['ords'].add(order_col);
        st.pop('ep_refuse', None);
        _memo_track([table + '_ep_' + order_col]);
        return 'src_endpoint';
    } except Exception as e {
        # transient (lock_timeout, a concurrent claimer) vs structural: both
        # look like an exception here, so retry a bounded number of times
        # rather than poisoning the mirror on the first busy moment.
        st['ep_refuse'] = _memo_refuse(
            st.setdefault('ep_refuse', {}), what, str(e), True
        );
        return None;
    } finally {
        if ddl_conn is not None {
            try {
                ddl_conn.close();
            } except Exception { }
        }
    }
}


impl PgStore.load_mirror_rows(
    cls: type, ids: list[UUID], fields: tuple
) -> (list[tuple] | None) {
    st = _mirror_state.get(cls);
    if not st or not st['ok'] {
        return None;
    }
    table = st['table'];
    cols = st['cols'];
    sel_list: list = [];
    sel_list.append('id');
    for c in _mirror_base_cols() {
        sel_list.append(c);
    }
    for f in fields {
        c = cols.get(str(f));
        if c is None {
            return None;   # proof field unknown to the mirror: fall back
        }
        # ::text pins the wire format of the jsonb field columns. Left as
        # jsonb, psycopg decodes them and the pure-python pgwire driver does
        # not, so the caller would have to guess whether '"Ada"' is a quoted
        # string or a string that happens to look like one. As text both
        # drivers hand back the field's JSON text and the caller decodes it
        # exactly once (query_planner._stream_from_mirror).
        sel_list.append(c + '::text');
    }
    sel = ', '.join(sel_list);
    try {
        return list(
            self._run(
                'SELECT ' + sel + ' FROM ' + table
                    + ' WHERE id = ANY(CAST(:ids AS uuid[]))',
                {'ids': [str(i) for i in ids]}
            )
        );
    } except Exception as e {
        logger.warning(f"mirror read for {table} failed (falling back): {e}");
        return None;
    }
}


impl PgStore.load_props(ids: list[UUID]) -> dict[UUID, AnchorRow] {
    # Stream-path row fetch: props + identity only. No adjacency subquery
    # (the stream proof guarantees .edges is never observed) and no src/dst
    # (node rows only), which is most of load_full's buffer cost.
    if not ids {
        return {};
    }
    out: dict[UUID, AnchorRow] = {};
    rows = self._run(
        """
        SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint,
               a.root_id, a.props, a.xmin::text
        FROM anchors a WHERE a.id = ANY(CAST(:ids AS uuid[]))
        """,
        {'ids': [str(i) for i in ids]}
    );
    for r in rows {
        raw_props = r[6];
        props: dict = (
            raw_props if isinstance(raw_props, dict) else json.loads(str(raw_props))
        );
        row = AnchorRow(
            id=intern_uuid(r[0]),
            kind=str(r[1]),
            arch_type=str(r[2]),
            arch_module=str(r[3]),
            fingerprint=str(r[4]),
            root_id=intern_uuid(r[5]) if r[5] else None,
            props=props,
            version=int(str(r[7]))
        );
        out[row.id] = row;
    }
    return out;
}


impl PgStore.upsert(rows_in: list[AnchorRow]) -> None {
    if not rows_in {
        return;
    }
    by_id: dict[UUID, AnchorRow] = {row.id: row for row in rows_in};
    rows = list(by_id.values());
    chunk = 200;
    # Fixed-shape statement (unnest over column arrays) instead of a
    # VALUES-list sized to the batch: the SQL text is identical for any
    # batch size 1..200, so psycopg/postgres see the SAME statement every
    # call and can actually reuse a prepared plan (JAC_PG_PREPARE_THRESHOLD)
    # instead of re-parsing a fresh N-row text each time.
    upsert_sql = """
        INSERT INTO anchors
            (id, kind, arch_type, arch_module, fingerprint, root_id,
             src, dst, undirected, props, format_version, updated_at,
             src_type, dst_type)
        SELECT id, kind, arch_type, arch_module, fingerprint, root_id,
               src, dst, undirected, props, :fmt_version, now(),
               src_type, dst_type
        FROM unnest(
            CAST(:ids AS uuid[]), CAST(:kinds AS text[]),
            CAST(:arch_types AS text[]), CAST(:arch_modules AS text[]),
            CAST(:fps AS text[]), CAST(:root_ids AS uuid[]),
            CAST(:srcs AS uuid[]), CAST(:dsts AS uuid[]),
            CAST(:undirecteds AS boolean[]), CAST(:propses AS jsonb[]),
            CAST(:src_types AS text[]), CAST(:dst_types AS text[])
        ) AS t(id, kind, arch_type, arch_module, fingerprint, root_id,
               src, dst, undirected, props, src_type, dst_type)
        ON CONFLICT (id) DO UPDATE SET
            kind = EXCLUDED.kind,
            arch_type = EXCLUDED.arch_type,
            arch_module = EXCLUDED.arch_module,
            fingerprint = EXCLUDED.fingerprint,
            root_id = EXCLUDED.root_id,
            src = EXCLUDED.src,
            dst = EXCLUDED.dst,
            undirected = EXCLUDED.undirected,
            props = EXCLUDED.props,
            format_version = EXCLUDED.format_version,
            updated_at = now(),
            -- an edge re-saved while its endpoints are unpopulated stubs
            -- carries NULL types; keep whatever was recorded earlier
            src_type = COALESCE(EXCLUDED.src_type, anchors.src_type),
            dst_type = COALESCE(EXCLUDED.dst_type, anchors.dst_type)
        """;
    for start in range(0, len(rows), chunk) {
        batch = rows[start:start + chunk];
        params = {
            'fmt_version': SCHEMA_VERSION,
            'ids': [str(row.id) for row in batch],
            'kinds': [row.kind for row in batch],
            'arch_types': [row.arch_type for row in batch],
            'arch_modules': [row.arch_module for row in batch],
            'fps': [row.fingerprint for row in batch],
            'root_ids': [str(row.root_id) if row.root_id else None for row in batch],
            'srcs': [str(row.src) if row.src else None for row in batch],
            'dsts': [str(row.dst) if row.dst else None for row in batch],
            'undirecteds': [row.undirected for row in batch],
            'propses': [json.dumps(row.props, default=_jsonable) for row in batch],
            'src_types': [row.src_type for row in batch],
            'dst_types': [row.dst_type for row in batch],
        };
        self._run(upsert_sql, params);
    }
    pairs: list[tuple[str, str]] = [];
    seen_pairs: set[tuple[str, str]] = set();
    for row in rows {
        if row.arch_type and row.arch_type not in self._known_types {
            for anc in (row.ancestry or [row.arch_type]) {
                if (row.arch_type, anc) not in seen_pairs {
                    seen_pairs.add((row.arch_type, anc));
                    pairs.append((row.arch_type, anc));
                }
            }
        }
    }
    if pairs {
        # same fixed-shape trick: unnest two parallel arrays instead of a
        # VALUES-list sized to len(pairs).
        self._run(
            """
            INSERT INTO graph_types (type_name, ancestor)
            SELECT * FROM unnest(CAST(:types AS text[]), CAST(:ancestors AS text[]))
            ON CONFLICT DO NOTHING
            """,
            {
                'types': [p[0] for p in pairs],
                'ancestors': [p[1] for p in pairs],
            }
        );
        for pair in pairs {
            self._known_types.add(pair[0]);
        }
        # P1-ITEM3: a newly-seen (type, ancestor) pair can change some
        # ancestor's subtype set -- drop the whole memoized cache rather
        # than reason about which ancestor keys are affected (rare event:
        # only fires the first time any archetype instance is ever
        # written, all benchmark archetypes are already known by request 1
        # of a seeded run).
        self._subtype_names_cache = {};
    }
}


impl PgStore.delete(ids: list[UUID]) -> None {
    if not ids {
        return;
    }
    self._run(
        'DELETE FROM anchors WHERE id = ANY(CAST(:ids AS uuid[]))',
        {'ids': [str(i) for i in ids]}
    );
}


impl PgStore.existing(ids: list[UUID]) -> set[UUID] {
    if not ids {
        return set();
    }
    rows = self._run(
        'SELECT id FROM anchors WHERE id = ANY(CAST(:ids AS uuid[]))',
        {'ids': [str(i) for i in ids]}
    );
    return {UUID(str(r[0])) for r in rows};
}


impl PgStore.root_ids -> list[UUID] {
    rows = self._run(
        """
        SELECT id FROM anchors
        WHERE kind = 'NodeAnchor' AND arch_type = 'Root' ORDER BY id
        """,
        {}
    );
    return [UUID(str(r[0])) for r in rows];
}


impl PgStore.subtype_names(type_name: str) -> list[str] {
    # P1-ITEM3 (standalone-type-resolution-redundant-refetch): memoized per
    # store instance. graph_types is schema-stable at request granularity --
    # only grows when a brand-new archetype is written for the first time
    # ever (upsert's _known_types tail, which clears this cache when that
    # happens) -- so a cache hit here removes an entire standalone round
    # trip that the caller (e.g. query_planner's fast-path eligibility
    # check) previously issued on every request, only to discard the rows.
    cached = self._subtype_names_cache.get(type_name);
    if cached is not None {
        return list(cached);
    }
    rows = self._run(
        'SELECT type_name FROM graph_types WHERE ancestor = :t', {'t': type_name}
    );
    names = [str(r[0]) for r in rows];
    if type_name not in names {
        names.append(type_name);
    }
    self._subtype_names_cache[type_name] = names;
    return list(names);
}


impl PgStore.rows(sql: str, params: dict) -> list[tuple] {
    return [tuple(r) for r in self._run(sql, params)];
}


impl PgStore.kv_get(key: str) -> (str | None) {
    rows = self._run(
        """
        SELECT value FROM kv_state
        WHERE key = :k AND (expires_at IS NULL OR expires_at > now())
        """,
        {'k': key}
    );
    return str(rows[0][0]) if rows else None;
}


impl PgStore.kv_put(key: str, value: str) -> None {
    self._run(
        """
        INSERT INTO kv_state (key, value, updated_at) VALUES (:k, :v, now())
        ON CONFLICT (key) DO UPDATE SET value = :v, updated_at = now()
        """,
        {'k': key, 'v': value}
    );
}


impl PgStore.kv_put_ttl(key: str, value: str, ttl_seconds: int) -> None {
    with self._lock {
        conn: Any = self._side();
        conn.run(
            """
            INSERT INTO kv_state (key, value, expires_at, updated_at)
            VALUES (
                :k, :v, now() + make_interval(secs => CAST(:ttl AS int)), now()
            )
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                expires_at = EXCLUDED.expires_at,
                updated_at = now()
            """,
            k=key,
            v=value,
            ttl=ttl_seconds
        );
    }
}


impl PgStore.kv_delete(key: str) -> None {
    self._run('DELETE FROM kv_state WHERE key = :k', {'k': key});
}


impl PgStore.quarantine(
    missing_id: UUID, referrer_id: (UUID | None), kind: str
) -> None {
    if self._isolation is TxnIsolation.SNAPSHOT_READ_ONLY {
        return;
    }
    self._run(
        """
        INSERT INTO quarantine (missing_id, referrer_id, kind)
        VALUES (CAST(:m AS uuid), CAST(:r AS uuid), :k)
        ON CONFLICT DO NOTHING
        """,
        {
            'm': str(missing_id),
            'r': str(referrer_id) if referrer_id else None,
            'k': kind
        }
    );
}


impl PgStore.notify(channel: str, payload: str) -> None {
    with self._lock {
        ident = _channel_ident(channel);
        conn: Any = self._side();
        conn.run(
            'SELECT pg_notify(:c, :p)',
            c=ident,
            p=_channel_wire_payload(channel, ident, payload)
        );
    }
}


impl PgStore.listen(channel: str, callback: Any) -> None {
    with self._lock {
        ident = _channel_ident(channel);
        self._listeners.append(
            ChannelListener(channel=channel, ident=ident, callback=callback)
        );
        conn: Any = self._side();
        conn.run(f"LISTEN {_quote_channel(ident)}");
        if self._listen_thread is None {
            self._listen_stop = threading.Event();
            t: Any = threading.Thread(
                target=self._listen_loop, daemon=True, name='jac-pg-listen'
            );
            self._listen_thread = t;
            t.start();
        }
    }
}


impl PgStore.unlisten(channel: str) -> None {
    parked: Any = None;
    with self._lock {
        ident = _channel_ident(channel);
        kept = [
            lst
            for lst in self._listeners
            if lst.channel != channel
        ];
        if len(kept) == len(self._listeners) {
            return;
        }
        self._listeners = kept;
        shared = any((lst.ident == ident) for lst in kept);
        conn: Any = self._side_conn;
        if conn is not None and not shared {
            try {
                conn.run(f"UNLISTEN {_quote_channel(ident)}");
            } except Exception as e {
                logger.debug(f"unlisten {channel} failed: {e}");
            }
        }
        if not self._listeners {
            parked = self._stop_listen_thread();
        }
    }
    self._join_listen_thread(parked);
}


impl PgStore._stop_listen_thread -> Any {
    if self._listen_stop is not None {
        self._listen_stop.set();
    }
    parked = self._listen_thread;
    self._listen_thread = None;
    return parked;
}


impl PgStore._join_listen_thread(parked: Any) -> None {
    if parked is None or parked is threading.current_thread() {
        return;
    }
    parked.join(timeout=_LISTEN_JOIN_SECONDS);
    if parked.is_alive() {
        logger.warning('pg listen thread did not stop within its join window');
    }
}


impl PgStore._listen_loop -> None {
    import select;
    stop: Any = self._listen_stop;
    if stop is None {
        return;
    }
    while not stop.is_set() {
        pending: list = [];
        sock: Any = None;
        try {
            with self._lock {
                conn: Any = self._side_conn;
                if conn is None {
                    break;
                }
                if conn.notifications {
                    pending = list(conn.notifications);
                    conn.notifications.clear();
                } else {
                    sock = conn._sock;
                }
            }
            if not pending {
                if sock is None {
                    stop.wait(_LISTEN_POLL_SECONDS);
                    continue;
                }
                readable = select.select([sock], [], [], _LISTEN_POLL_SECONDS)[0];
                if stop.is_set() {
                    break;
                }
                if not readable {
                    continue;
                }
                with self._lock {
                    conn2: Any = self._side_conn;
                    if conn2 is None {
                        break;
                    }
                    conn2.run('SELECT 1');
                    pending = list(conn2.notifications);
                    conn2.notifications.clear();
                }
            }
            for (pid, channel, payload) in pending {
                self._dispatch_notification(channel, payload);
            }
        } except Exception as e {
            logger.debug(f"listen loop hiccup: {e}");
            stop.wait(_LISTEN_POLL_SECONDS);
        }
    }
}


impl PgStore._dispatch_notification(channel: str, payload: str) -> None {
    envelope: (ChannelMessage | None) = None;
    decoded = False;
    for lst in list(self._listeners) {
        if lst.ident != channel {
            continue;
        }
        body = payload;
        if lst.channel != channel {
            if not decoded {
                envelope = _channel_envelope(payload);
                decoded = True;
                if envelope is None {
                    logger.warning(
                        f"notification on {channel} carries no channel envelope;"
                        ' dropping it rather than guessing a subscriber'
                    );
                }
            }
            if envelope is None or envelope.channel != lst.channel {
                continue;
            }
            body = envelope.payload;
        }
        try {
            lst.callback(body);
        } except Exception as e {
            logger.warning(f"listener callback failed: {e}");
        }
    }
}


impl PgStore._promotion_columns -> list[tuple[str, str, str]] {
    out: list[tuple[str, str, str]] = [];
    for (arch, fields_l) in sorted(self.promotions.items()) {
        for fld in fields_l {
            col = f"g_{_sanitize_ident(arch)}_{_sanitize_ident(fld)}";
            out.append((arch, fld, col));
        }
    }
    return out;
}


impl PgStore._apply_promotions -> None {
    for (arch, fld, col) in self._promotion_columns() {
        try {
            self._run(
                f"""
                ALTER TABLE anchors ADD COLUMN IF NOT EXISTS {col} text
                GENERATED ALWAYS AS (props->'archetype'->>'{fld}') STORED
                """,
                {}
            );
            self._run(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{col} ON anchors ({col})
                WHERE arch_type = '{arch}'
                """,
                {}
            );
        } except Exception as e {
            logger.warning(f"promotion {arch}.{fld} failed: {e}");
        }
    }
}


impl PgStore._property_graph_ddl -> None {
    if self.server_version() < 19 {
        return;
    }
    stmts = [
        """
        CREATE OR REPLACE VIEW graph_nodes AS
            SELECT id, arch_type, root_id, props FROM anchors
            WHERE kind = 'NodeAnchor'
        """,
        """
        CREATE OR REPLACE VIEW graph_edges AS
            SELECT id, arch_type, src, dst, undirected, props FROM anchors
            WHERE kind = 'EdgeAnchor' AND src IS NOT NULL AND dst IS NOT NULL
        """,
        """
        CREATE PROPERTY GRAPH IF NOT EXISTS jac_graph
            VERTEX TABLES (
                graph_nodes KEY (id) LABEL node PROPERTIES (arch_type)
            )
            EDGE TABLES (
                graph_edges KEY (id)
                    SOURCE KEY (src) REFERENCES graph_nodes (id)
                    DESTINATION KEY (dst) REFERENCES graph_nodes (id)
                    LABEL edge PROPERTIES (arch_type)
            )
        """
    ];
    for stmt in stmts {
        try {
            self._run(stmt, {});
        } except Exception as e {
            logger.debug(f"property graph ddl skipped: {e}");
            return;
        }
    }
}


impl PgStore.close -> None {
    parked: Any = None;
    with self._lock {
        parked = self._stop_listen_thread();
        self._listeners = [];
        main_conn = self._conn;
        if _PG_POOL and main_conn is not None {
            reusable = not getattr(main_conn, '_closed', True);
            if reusable and self._in_txn {
                try {
                    main_conn.run('ROLLBACK');
                } except Exception {
                    reusable = False;
                }
            }
            if reusable and _pool_checkin(self.conninfo.dsn(), main_conn) {
                self._conn = None;
            }
        }
        for c in [self._conn, self._side_conn] {
            if c is not None {
                try {
                    c.close();
                } except Exception { }
            }
        }
        self._conn = None;
        self._side_conn = None;
        self._in_txn = False;
    }
    self._join_listen_thread(parked);
}
