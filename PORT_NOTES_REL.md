# PORT NOTES -- PostgresRelBackend MVP (feat/pg-rel-mvp)

2026-07-13. Branch off `5fbce338e` (fix/pg-l3-read-trips tip). Companion docs:
`ARCH_REL.md` (diagrams), `docs/superpowers/specs/2026-07-13-pg-rel-backend-design.md`
(decisions + alternatives), `docs/superpowers/plans/2026-07-13-pg-rel-mvp.md` (task log).

## What was built

`PostgresRelBackend(PostgresBackend)`: the KV anchor store + one `edges` index
table (edge_id PK, source, target, edge_type, is_undirected, seq identity;
indexes on (source, edge_type, seq) and (target, edge_type, seq)). The table
replaces the per-root GTI blob as the topology answer-er:

- **Write path**: edge rows are maintained inside `apply()`'s transaction via
  the new `_apply_intent` per-intent dispatch seam on PostgresBackend
  (behavior-identical refactor: KV path still routes to `_pg_apply_one`).
  EDGE_CREATE inserts the row after the parent upserts the edge's anchor row;
  EDGE_DELETE / NODE_DELETE sweep rows before it. `put()` (seeding path) keeps
  the row in step. Consistency rule: edges row exists iff the edge's anchors
  row exists, enforced by sharing the transaction.
- **Read path**: `resolve_hop_sql(current_ids, edge_type, node_type,
  direction, slc)` answers one hop with a UNION-ALL-legs query (undirected
  rows traverse both ways), optional `JOIN anchors ON arch_type` for node
  filters, `GROUP BY endpoint ORDER BY MIN(seq)` for first-seen creation
  order; slice applied Python-side. Errors return None (never raise into a
  request) and bump `rel_hop_fallback_count`.
- **Resolver seam** (the one shared-file edit, `resolver.impl.jac` top of
  `resolve_hop`): capability-gated dispatch on `'topology_sql' in
  mem.capabilities()`. Dead branch for every other backend -- no backend but
  this one advertises the capability -- so flag-off behavior is byte-identical
  (same attribution pattern as cross_root_resolve / batch_l3).
- **Selection**: `JAC_SCALE_BACKEND=postgres-rel` (fail-loud: no-URI, no
  psycopg, unreachable PG all raise), `PersistenceType.POSTGRES_REL`,
  INTENT_RULES maps `postgres-rel -> data.postgres`.
- **Kill switch**: `JAC_TOPOLOGY_SQL=0` empties capabilities() -> resolver
  branch never fires -> rel storage with GTI/walk hops (ablation control).

## Why no GTI hooks (load-bearing discovery)

`JAC_TOPOLOGY_INDEX` gates the GTI WRITE hooks (`topo_utils.impl.jac`
`_is_enabled()` at the top of on_edge_created/destroyed/on_node_saved/
destroyed); reads have no flag. Hook-based edge-row maintenance would have
inherited that gate. Maintaining rows from changeset intents inside apply()
decouples entirely: **postgres-rel works with JAC_TOPOLOGY_INDEX=0** -- no
blob decode, no whole-blob re-encode per mutation, no dual-blob cross-root
writes, no 65,535-node u16 blob ceiling, no blob-CAS edge-discard race.

## Ablation matrix

| Config | Topology answered by | Measures |
|---|---|---|
| `postgres` (KV) + GTI on | blob decode in Python | baseline (124.8ms feed p50 all-flags) |
| `postgres-rel` + `JAC_TOPOLOGY_SQL=0` + GTI on | blob (rel storage inert) | storage-swap control (expect ~= KV) |
| `postgres-rel` + SQL hops + GTI on | edges table | hop-resolution delta |
| `postgres-rel` + SQL hops + GTI off | edges table | + write-amplification savings |

## Ledger (divergences, limits, decisions)

1. **Node-type filter is exact-match** in SQL (joins `anchors.arch_type`).
   GTI fans node filters out over the MRO at write time, so a traversal
   filtered by a SUPERCLASS returns fewer rows on the SQL path. littleX uses
   leaf types only. Edge-type exact-match is parity (GTI is exact there too).
2. **Edge-only final hops not accelerated**: `[edge -->]`-style refs bypass
   the resolver for the last hop (`runtime.impl.jac` edge_only path).
3. **`_try_field_pushdown` still uses the blob index**; with GTI off it
   degrades to None -> the SQL branch never covers field-predicate hops in
   MVP (they fall to walk). Acceptable: littleX feed has no field-predicate
   traversals on the hot path.
4. **No FK constraints** edges->anchors by design: TieredMemory.delete's
   immediate out-of-txn l3.delete and the silent-drop of ApplyReport.failed
   at the request boundary would turn constraint violations into lost writes.
   Consistency comes from same-transaction maintenance instead.
5. **No delete() override**: PostgresBackend.delete is a deliberate no-op
   (issue #6587, durable deletes only via apply intents) -- the spec's
   original "eager delete override" dissolved on verification.
6. **Ordered semantics**: seq (global creation order) mirrors GTI adj_list
   append order; node-blob edge-list order is NOT reliable after concurrent
   merges (rebuilt from a set) and was not used. First-seen dedup matches
   resolve_chain_ordered.
7. **Grants**: SQL path checks no grants -- identical to the GTI indexed
   path (grants only fire on the fallback walk). Parity, not a regression.
8. **L2/Redis**: rel-applied anchors take ScaleTieredMemory.commit's generic
   write-through branch (no Mongo-style EDGE_LIST_DELTA skip). Untouched.
9. **Cross-root**: the edges table is global, so the SQL path needs neither
   `cross_root_resolve` nor foreign-root fetches. With `JAC_TOPOLOGY_SQL=0`
   the usual flags apply again.
10. **Migration/backfill out of scope**: fresh seed only. A KV-seeded
    database has no edge rows; selecting postgres-rel on it gives empty SQL
    hops with a healthy-looking backend. Seed through postgres-rel (apply or
    put both maintain rows).
11. **Inherited, unchanged**: deadlock->silent-write-drop (pre-Locust fix
    still REQUIRED), fetch-count units (rel_hop_count counts hop round-trips
    separately from l3_fetch_count), empty-edge-list node auto-delete.

## Toolchain notes

- Fresh worktrees lack the untracked LLVM shim; symlink
  `<main>/jac/jaclang/compiler/passes/native/llvm/libjacllvm.so` into the same
  path in the worktree or `import jaclang` (dev-source) dies at compiler load.
- Tests: global `jac`, cwd inside worktree, `JAC_TEST_JOBS=0`, local PG.
  Rel suites use database `jactest_rel` (`POSTGRESQL_REL_URI` override) --
  deliberately disjoint from the KV suites' `jactest` (mutual TRUNCATE).

## Validation (2026-07-13, all green, 124 tests)

- rel: test_postgres_rel_backend 18 (rows 6 / hop 9 / seam 2 / caps 1),
  test_postgres_rel_selection 5
- KV regression: test_postgres_backend 40, test_postgres_selection 7,
  test_postgres_e2e_integration 1
- mongo seams: test_direct_db 12, test_occ_replay 7, test_memory_hierarchy 27
- core flags: test_cross_root_resolve 3, test_read_only_ablation 4
  (plus resolver-adjacent: test_resolver_per_hop 3, test_cross_root_topo_index
  2, test_topology_index 17 -- run at seam commit)

Seam tests prove the headline: 2-hop traversal resolves through SQL with
JAC_TOPOLOGY_INDEX **off** and rel_hop_count > 0; JAC_TOPOLOGY_SQL=0 falls
back to the walk with identical results.

Addendum (2026-07-16): the 18-test count above is point-in-time.
`test_postgres_rel_backend.jac` now contains 27 test blocks (order pushdown,
chain, and projection tests landed after this section was written).

## Pending (gated / next)

- Rel e2e (`jac start` boot, GTI off, cold restart) -- server boot gated.
- littleX seed `--user-prefix rel_` + PARITY OK 20/0 + sanity bench vs
  KV-PG 124.8 / Mongo 105.5.
- Full pushdown (filter/ORDER BY/LIMIT into SQL) remains future work
  (gti-pg-hybrid piece 2); this MVP only moves hop resolution.
