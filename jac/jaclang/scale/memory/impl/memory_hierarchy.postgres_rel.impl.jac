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
    return (
        str(anchor.id),
        str(anchor.source.id),
        str(anchor.target.id),
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
    key = str(anchor.id);
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


impl PostgresRelBackend.resolve_hop_sql(
    current_ids: set[UUID],
    edge_type: (str | None),
    node_type: (str | None),
    direction: int,
    slc: (slice | None) = None
) -> (set[UUID] | list[UUID] | None) {
    return None;
}
