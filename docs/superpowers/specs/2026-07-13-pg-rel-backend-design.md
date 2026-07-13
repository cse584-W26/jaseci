# PostgresRelBackend MVP -- Design Spec

Date: 2026-07-13. Branch: `feat/pg-rel-mvp` off `5fbce338e` (fix/pg-l3-read-trips tip).
Grounded in 5-scout recon (27 drift flags); every file:line below scout-verified on this worktree.

## What we're building

An alternative L3 backend where **topology questions are answered by indexed SQL instead of
decoding per-root GTI blobs in Python**. Selected via `JAC_SCALE_BACKEND=postgres-rel`
(fail-loud). KV backend stays untouched and selectable.

Framing that fell out of recon: this is NOT "rewrite anchor storage relationally." EdgeAnchors
are already first-class anchors with their own rows; node blobs must keep their `edges` id-list
(runtime contract: fallback walk iterates `nanch.edges` stubs; serializer is off-limits).
The MVP is **"the GTI as a table instead of a blob"** -- a global `edges` index table plus a
SQL hop resolver, with everything else inherited from the KV backend.

## Scout findings that changed the plan (drift log)

| # | Finding | Consequence |
|---|---------|-------------|
| D1 | `JAC_TOPOLOGY_INDEX` gates GTI **write hooks** (`topo_utils.impl.jac:1-14,108-199` all early-return on `_is_enabled()`); reads have no gate | Do NOT wire edge-row maintenance through topo hooks. Maintain rows inside `apply()` from changeset intents -- flag-independent, transaction-safe. Rel backend can run GTI fully OFF → kills blob re-encode write amplification for free |
| D2 | Resolver hard `isinstance(TopologyIndex)`-checks (`resolver.impl.jac:82,248`) + raw attr access `node_to_lid` / `node_table[lid][2]` in per-uid loops (`:284-288`); `get_topology_index()` never returns None (returns empty index); `set_topology_index` calls `encode()` | Adapter-impersonation (Option A) rejected. Seam = capability-gated branch at top of `resolve_hop` (Option B) |
| D3 | No `resolve_chain_cross_root` method exists; cross-root is resolver-side `_resolve_hop_cross_root` (`resolver.impl.jac:45-92`) = get_cross_root_ids + batch_get foreign roots + per-root blob decode | Our SQL hop is global -- cross-root ceases to exist as a concept on the SQL path. `cross_root_resolve` flag becomes moot when `topology_sql` fires |
| D4 | Edge order lives in 2 places; node-blob edge list order is ALREADY unreliable after concurrent merges (rebuilt from a set: `postgres.impl.jac:492-500`); only GTI `adj_list` append order (= creation order) is authoritative | `edges.seq` = global monotonic identity column, mirrors adj_list creation order. `ORDER BY` on seq reproduces `resolve_chain_ordered` |
| D5 | GTI edge-type filters are **exact-match** (no MRO fan-out, `topology_index.impl.jac:106-114`); node-type filters fan out over MRO at write time | SQL exact-match on edge_type = parity. Node-type filter: exact match only in MVP; superclass node filters diverge from GTI (returns fewer). Ledgered; littleX uses leaf types only |
| D6 | `TieredMemory.delete` does an immediate out-of-txn `l3.delete(id)` (`memory.impl.jac:1710-1724`); KV merge auto-deletes non-Root nodes whose edge list empties | **No FK constraints** edges→anchors (eager deletes + silent-drop path would turn constraint violations into lost writes). Empty-node auto-delete inherited via subclassing |
| D7 | `ApplyReport.failed` is silently dropped at request boundary (only WriteConflict raises); pre-existing ledger item | Rel backend adds no constraints that could fail (see D6); inherits the staged-loop contract unchanged |
| D8 | PG test suites share `postgresql:///jactest` and TRUNCATE each other's tables | Cloned rel suite uses separate db `jactest_rel` |
| D9 | u16 lid ceiling: GTI blob corrupts silently past 65,535 nodes/root | Not our problem (we don't encode blobs) -- but noted: at scale the rel backend is the only one that still works. Paper ammo |

## Design decisions (alternatives considered)

### Decision 1 -- Storage shape: anchors table + edges index table (chosen)

- **S1 (chosen): inherit the `anchors` table wholesale, add one `edges` table** that indexes
  EdgeAnchor rows. Subclass `PostgresBackend`. Inherits: pool process-cache, autocommit-toggle
  reads, `_pg_merge_write` OCC/edge-list merge, quarantine machinery, fsck/recover, 40-test
  conformance surface.
- S2 (rejected for MVP): full nodes/edges relational split. Requires reimplementing quarantine,
  merge-write, fsck, get()-table-dispatch; conformance suite rewrite; serializer contract
  (node blob edges list) still forces dual representation anyway. This is the post-MVP
  "typed columns" step, explicitly out of scope.

The honest description for the paper: KV backend = GTI-as-blob; rel backend = GTI-as-table.
Same anchor storage, different topology index. Clean single-variable ablation.

### Decision 2 -- Resolver seam: capability-gated branch in `resolve_hop` (chosen)

- **B (chosen): early branch at top of `resolve_hop` (`resolver.impl.jac:271`)**:
  if the memory advertises `topology_sql`, delegate the hop to the backend; `None` result
  falls through to the existing index/walk ladder unchanged. Precedent: `_try_pushdown`
  already does capability-gated dispatch through `mem`. Gated = byte-identical behavior for
  every other backend (attribution rule satisfied -- same pattern as `cross_root_resolve` /
  `batch_l3` flags).
- A (rejected): TopologyIndex-impersonating adapter. Must subclass to pass isinstance, lie in
  `__len__`, fake `node_to_lid`/`node_table` dict/list protocols with per-key SQL under a
  per-uid hot loop, and survive `set_topology_index`'s `encode()`. Slower and uglier than the
  thing it replaces.
- C (rejected): full QueryPlan chain pushdown via `execute_plan`. That's piece-2
  filter-pushdown (gti-pg-hybrid), explicitly out of scope.

Scope notes: `_try_field_pushdown` (`:192-240`) keeps using the blob index (degrades to None
gracefully -- acceptable, documented). Edge-only final hops (`runtime.impl.jac:1114-1118`)
bypass the resolver either way -- SQL seam does not accelerate `[edge -->]` collectors (ledger).

### Decision 3 -- Edges schema

```sql
CREATE TABLE IF NOT EXISTS edges (
    edge_id   TEXT PRIMARY KEY,
    source    TEXT NOT NULL,
    target    TEXT NOT NULL,
    edge_type TEXT NOT NULL,              -- leaf arch_type, exact-match (D5)
    is_undirected BOOLEAN NOT NULL DEFAULT FALSE,
    seq       BIGINT GENERATED ALWAYS AS IDENTITY  -- creation order (D4)
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges (source, edge_type, seq);
CREATE INDEX IF NOT EXISTS idx_edges_tgt ON edges (target, edge_type, seq);
```

- No FK to anchors (D6). Consistency rule instead: **edges row exists iff the EdgeAnchor's
  anchors row exists**, both maintained in the same `apply()` transaction.
- No `owner_root` column: the table is global; ownership checks belong to the blob design
  (SELF_ROOT pre-checks) which the SQL path deliberately skips. Grant semantics identical to
  the GTI indexed path (neither checks grants -- scout-confirmed parity, `runtime.impl.jac:331,339`
  fires only on fallback walk).
- Node-type filter joins `anchors.arch_type` at query time (no denormalized target-type column
  to go stale).

Hop query shape (OUT direction; IN swaps columns; BOTH = union; undirected rows match both ways):

```sql
SELECT e.target FROM edges e
JOIN anchors a ON a.id = e.target
WHERE e.source = ANY(%s)
  AND e.edge_type = %s            -- omitted when hop has no edge filter
  AND a.arch_type = %s            -- omitted when hop has no node filter
```

Ordered+sliced variant: `GROUP BY e.target ORDER BY MIN(e.seq)` + slice applied Python-side
(first-seen dedup semantics of `resolve_chain_ordered`, `topology_index.impl.jac:400-419`).

### Decision 4 -- Write path: extend `apply()`, not hooks

Subclass overrides the per-intent handler to add, inside the SAME transaction:

- `EDGE_CREATE` → parent upserts the edge's anchor row; we also `INSERT INTO edges ... ON CONFLICT (edge_id) DO NOTHING`.
- `EDGE_DELETE` / `is_delete()` on an edge → parent deletes anchor row; we also `DELETE FROM edges WHERE edge_id=%s`.
- `NODE_DELETE` → parent deletes node row; we also `DELETE FROM edges WHERE source=%s OR target=%s`
  (defensive sweep; Python cascade usually staged the edge deletes already).
- `delete(id)` override (the eager out-of-txn path, D6): parent row delete + edges sweep.
- Everything else (merge-write, OCC, quarantine, INERROR guard) inherited untouched.

Source/target/type read from the EdgeAnchor in the intent (serializer keys `source`, `target`,
`is_undirected` -- scout-verified `serializer.impl.jac:147-153`). Edge-delete repair-path stubs
carry ids in `intent.edges_added/removed`, not `anchor.edges` (scout open question -- verify at
build time against `changeset.jac`).

### Decision 5 -- Selection & flags

- `JAC_SCALE_BACKEND=postgres-rel` (env wins over toml, existing precedence). New elif branch in
  `memory_hierarchy.main.impl.jac` postinit; new `PersistenceType.POSTGRES_REL`; else-raise
  message updated. Rel branch checked BEFORE any isinstance-vs-PostgresBackend logic (subclass
  ambiguity, scout drift). Auto path never returns it.
- `capabilities()` adds `'topology_sql'`. Env kill-switch `JAC_TOPOLOGY_SQL=0` disables the
  resolver branch while keeping rel storage → ablation axis: rel-storage-with-GTI-hops vs
  rel-storage-with-SQL-hops. Default on when backend selected.
- `INTENT_RULES`: map `"postgres-rel" → "data.postgres"` (`capabilities.jac:93-104`) so toml
  intent syncs psycopg.

### Decision 6 -- Failure semantics on the SQL hop

`resolve_hop_sql` returns `None` on any exception → resolver falls through to blob/walk ladder
(graceful, same contract as every other fast path). DEBUG log + counter so a silent-fallback
benchmark contamination is detectable (`rel_hop_fallback_count` attr, mirrors `l3_fetch_count`
pattern).

## What this kills (measured fork defects → schema shape)

1. Celebrity-blob pathology + Root-blob re-encode per commit (`archetype.impl.jac:268` re-encodes
   whole blob per mutation; cross-root edges re-encode TWO blobs) → edge write = one row insert.
2. Concurrent-edge-discard race (blob CAS last-writer-wins) → row-level inserts don't conflict.
3. Cross-root N+1 (foreign-root batch_get + per-root decode) → single global-table query.
4. u16/65k-node blob ceiling → gone.

Ceiling honestly stated: hop resolution ≈ 1 SQL round-trip per hop (~0.3-1ms each) vs in-memory
decode-cached dict lookups. The win is on writes, cross-root, cold paths, and scale -- plus the
serializer/hydration tail is untouched by design (out of scope).

## Out of scope (unchanged from task)

Filter/ORDER BY/LIMIT pushdown; typed per-archetype columns; identity storage; serializer/shared
runtime behavior changes (resolver branch is additive + gated); Redis/L2 changes; blob→row
migration tooling (fresh seed only).

## Test plan

All in `jac/jaclang/scale/tests/data/`, db `postgresql:///jactest_rel` (D8), serial
(`JAC_TEST_JOBS=0`), global `jac` with cwd in worktree.

1. `test_postgres_rel_backend.jac` -- cloned 40-test conformance (backend class + DSN swapped)
   PLUS new: edge-row lifecycle (create/delete/node-delete sweep/eager-delete), hop SQL
   correctness (OUT/IN/BOTH, undirected, edge-type filter, node-type join filter, ordered+slice
   first-seen dedup, seq ordering), consistency rule (edges row iff anchor row, same txn).
2. `test_postgres_rel_selection.jac` -- cloned 7: postgres-rel fail-loud no-URI, unreachable,
   selects PostgresRelBackend + POSTGRES_REL, unknown-backend message lists postgres-rel,
   KV 'postgres' still selects PostgresBackend (regression).
3. `test_postgres_rel_e2e_integration.jac` -- graph_app 2-hop with `JAC_SCALE_BACKEND=postgres-rel`
   **and `JAC_TOPOLOGY_INDEX=0`** (proves SQL hops are truly blob-independent), raw-psycopg
   asserts edge rows exist, cold restart. [SERVER BOOT -- runs only after user go]
4. Regression: KV trio (40+7+1) + mongo seams (12+7+27) + core flag tests stay green.
5. Post-go: littleX seed `--user-prefix rel_`, PARITY OK 20/0, sanity bench vs KV-PG 124.8 /
   Mongo 105.5.

## Build-time verification list (open questions to close before/while coding)

- `WriteIntent`/`ChangeSet` exact member semantics (`changeset.jac`) -- esp. stub intents on the
  edge-delete repair path.
- `TieredMemory.capabilities()` delegation to l3 (needed by the resolver branch) -- verify it
  reaches the backend; add thin delegate if not.
- `resolve_hop` hop-tuple types: edge_type/node_type as name-strings vs classes; direction int
  encoding (1=IN, 2=OUT, 3=BOTH per scout).
- `ScaleTieredMemory.commit` L2 write-through branch for rel-applied anchors (generic put is
  fine for MVP; confirm no mongo-specific skip trips).
