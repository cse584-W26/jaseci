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
        edge_id       TEXT PRIMARY KEY,
        source        TEXT NOT NULL,
        target        TEXT NOT NULL,
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


"""Advertise SQL topology. JAC_TOPOLOGY_SQL=0 turns the resolver dispatch off
while keeping rel storage (ablation axis: rel-storage-with-GTI-hops vs
rel-storage-with-SQL-hops)."""
impl PostgresRelBackend.capabilities -> set[str] {
    env = os.environ.get("JAC_TOPOLOGY_SQL");
    if env is not None and env.lower() in ("0", "false", "no", "off") {
        return set();
    }
    return {'topology_sql'};
}


impl PostgresRelBackend.put(anchor: Anchor) -> None {
    super.put(anchor);
}


impl PostgresRelBackend._apply_intent(conn: Any, intent: WriteIntent) -> None {
    super._apply_intent(conn, intent);
}


impl PostgresRelBackend.resolve_hop_sql(
    current_ids: set[UUID],
    edge_type: (str | None),
    node_type: (str | None),
    direction: int,
    slc: (slice | None) = None
) -> (set[UUID] | list[UUID] | None) {
    return None;
}
