# PORT_NOTES_R2 - Postgres L3 backend, round 2 (feat/postgres-l3-r2)

Closing doc for the transplant of the old `feat/postgres-l3` port (cut against `fp-new-main` @
`488b09da1`, old layout `jac-scale/jac_scale/...`) onto the rebased base (jaclang core `main`,
scale package folded into `jac/jaclang/scale/...`). 5 commits, `fd934a4e2..8a0eca7b1`.

If this doc and the code disagree, the code wins.

## 1. FileMap deltas - old port vs this port

| Old path (`feat/postgres-l3`, base `jac-scale/jac_scale/`) | New path (`feat/postgres-l3-r2`) | Status |
|---|---|---|
| `postgres_backend.jac` (decl) | folded into `memory/memory_hierarchy.jac` (PostgresBackend obj + `PersistenceType.POSTGRES`, +57/-1) | moved, merged into shared decl file |
| `impl/postgres_backend.impl.jac` | `memory/impl/memory_hierarchy.postgres.impl.jac` (1567 lines) | moved, renamed to match sibling `.mongo.impl.jac`/`.redis.impl.jac` naming |
| `impl/memory_hierarchy.main.impl.jac` (selection wiring) | `memory/impl/memory_hierarchy.main.impl.jac` (+93/-27) | same file, ported the `backend` flag dispatch as new `elif` branches after the untouched `auto` path |
| config keys (backend/postgresql_uri) | `config/impl/config_loader.impl.jac` (+7) | moved, mechanical (flat-dict pattern unchanged) |
| `_optdeps/psycopg.jac` | `_optdeps/psycopg.jac` (+26) | moved verbatim |
| `jac-scale/jac.toml [optional-dependencies.data]` psycopg extra | `project/capabilities.jac`: `CAPABILITY_SPECS["data.postgres"]` + 2 `INTENT_RULES` keywords (+7/-1) | **replaced**, not moved - upstream deleted the toml-extras mechanism repo-wide in favor of a code-based capability registry between the two branches (DESIGN-CHANGE, see §3) |
| `providers/database/kubernetes_postgres.jac` | - | **not ported**. Out of scope for r2 (benchmarks need the L3 store, not a k8s deploy target). |
| `tests/test_deploy_postgres.jac` | - | **not ported** (companion to the k8s provider above) |
| `tests/test_postgres_backend.jac` | `tests/data/test_postgres_backend.jac` (1422 lines) | moved, conformance suite |
| `tests/test_postgres_selection.jac` | `tests/data/test_postgres_selection.jac` (134 lines) | moved + rewritten against the new `backend`/`postgresql_uri` config keys and `PersistenceType.POSTGRES` |
| `tests/test_postgres_e2e_integration.jac` | `tests/data/test_postgres_e2e_integration.jac` (209 lines) | moved |
| *(none - new this round)* | `tests/data/fixtures/graph_app.jac` (40 lines) | new e2e fixture app |
| *(none - new this round)* | `tests/data/fixtures/jac.toml` (21 lines) | new - bounds `jac start`'s project discovery to the fixtures dir (see gate log; unbounded discovery from cwd climbed to `jac/jac.toml` and tried to launch ~24 unrelated microservice fixtures) |
| `deploy/database/factory.jac` DatabaseType/create_client (raw KV client factory, separate from the L3 graph backend) | - | **not built this round.** Only the `PersistentMemory` L3 backend was in scope; the raw-client KV factory (`jac db` CLI / non-graph key-value access) still has no Postgres arm. Mechanical to add later (see discovery ledger), just not needed for the MVP benchmark. |

Net: `10 files changed, 3576 insertions(+), 28 deletions(-)` under `jac/jaclang/scale` (`git diff de2da69fb..8a0eca7b1 --stat`).

## 2. OCC and pool decisions, as built

**Pool**: one `psycopg_pool.ConnectionPool` per process, cached in the shared `_process_cache`
dict (same pattern as Mongo/Redis clients), keyed by `f"pg_pool::{dsn}::{pool_min}::{pool_max}"`.
Build is guarded by a module-level `threading.Lock` (double-checked: check cache, acquire lock,
re-check, build) - the old floor-fixes lesson (pool-per-request killed the noop floor) plus a
fix for the pre-existing racy check-then-set pattern Mongo/Redis still have (ledger-only there,
not touched - out of scope). `atexit.register(pool.close)` closes it at process exit; `.close()`
on the backend only drops the local reference, matching Mongo/Redis lifecycle.

**OCC / write path**: single Postgres transaction covers all 6 `ChangeSet` stages
(`NODE_CREATE, EDGE_CREATE, EDGE_LIST_DELTA, FIELD_UPDATE, EDGE_DELETE, NODE_DELETE`, honoring
stage order + `depends_on` skip-cascade) - a real cross-row transaction, stronger than
`MongoBackend.apply()` which has no cross-document transaction at all. Per-anchor optimistic
concurrency is enforced via `SELECT ... FOR UPDATE` inside `_pg_merge_write` (row lock, not a
CAS-column compare - issue #5446 cross-process-safety shape), `cas_version` is populated only for
`EDGE_LIST_DELTA` intents (matches the current `TieredMemory._collect_into` contract exactly - no
drift). A trigger-abort / SQL-error mid-transaction rolls back the whole apply and reports every
intent in that transaction as failed via `ApplyReport` - verified with a live fault-injection test
(no silent partial commit).

**Fetch counting**: `l3_fetch_count` increments once per SQL round-trip (a `batch_get` of N ids
is 1 count, not N) - kept attr-name-compatible with `TieredMemory.get_l3_fetch_count` but **not
the same unit as Mongo's** (Mongo counts `+len(ids)` per batch). See §3 benchmark-validity note.

**`delete()` is a cache-eviction no-op** (mirrors `SqliteMemory.delete`, pops the L1 `__mem__`
entry only, no `DELETE FROM anchors`) - load-bearing for `TieredMemory.abort`, which must not
destroy a merely-dirty-but-failed-request's already-durable row.

## 3. Drift ledger

Every discovery from the recon pass, grouped by classification. One inline fix landed during
review (see the amendment note under UPSTREAM-BUG/topology-cache below); everything else is
report-only, per the locked plan's classification rules.

### SAFE-ADAPT (mechanical, proceeded)

- Top-level `jac-scale/` directory confirmed fully absent (tracked and untracked); only
  `jac/jaclang/scale/` exists on this base. No stale-artifact reconciliation needed.
- Scale self-registers via direct module-level imports (`plugin.jac` from
  `cli/impl/registry.impl.jac` and `jac0core/runtime.jac`) - informs where new backend
  config/CLI surface hooks in; no design change.
- `DatabaseProviderFactory`/`DatabaseType` (raw KV factory) additions would be purely additive -
  not built this round (see fileMap, §1), deferred as out-of-scope.
- `PersistentMemory.apply()` contract (`ChangeSet`/`WriteIntent`/`ApplyReport`/`WriteOp`) is
  byte-identical to what the old port targeted; ported forward mechanically.
- `jac-scale`/config toml surface is a top-level `[scale]` table (config.plugins['scale']), not
  nested under `[plugins.scale]` - matters for any jac.toml examples (see ENV.md).
- `runtimelib/storage/sqlalchemy_memory.jac` (new upstream generic PersistentMemory) confirmed
  unrelated - never wired into `ScaleTieredMemory`'s L3 selection, only into `jac eject` scaffold.
- Existing process-cache pattern (Mongo/Redis) is the correct template for the PG pool; used as-is
  except for adding the lock (see §2).
- `jac.toml` `_parse_toml_data` plugin allow-list (`byllm, scale, client, mcp, desktop`) - doc/
  example-writing fact only, no code blast zone.
- Fresh-worktree jac binary bootstrap (`zig build -Dshim-bin=<path> jacllvm`, reflink-copying a
  prebuilt `.llvm-build`) - standard recipe recorded, no source touched.
- Zero pre-existing Postgres references anywhere in the repo - confirmed genuinely greenfield,
  nothing partially-there to reconcile.
- `jac check` on `memory_hierarchy.jac` gains 5 new static errors from the guarded-import
  `ConnectionPool` symbol (same optional-import shape pymongo's guard already produces for
  Mongo); baseline on that file was already 124 errors/188 warnings, `[precommit] typecheck =
  false` repo-wide - confirmed non-gating, not fixed.
- Global `jac` binary (symlink into the sibling checkout) correctly dev-routes to *this*
  worktree's `jaclang.scale` source as long as commands `cd` into this worktree first - verified
  via `inspect.getsourcefile` probe and the printed "compiler source at .../pgr2/jac" banner.
- `zig build -Ddev` native binary build for this worktree: 1m38s, blocked once on a missing LLVM
  cache (worked around via reflink-copy from the sibling, read-only).

### DESIGN-CHANGE (stopped, reported, not improvised)

- **`ScaleTieredMemory.postinit` backend selection mechanism itself changed** between the old
  port's base and this one: old base had explicit env-driven `JAC_SCALE_BACKEND` + fail-loud
  `PersistenceType` dispatch; this base instead has a generic `get_persistent_memory` provider
  hook + a silent duck-typed Mongo-probe-else-Sqlite fallback with no error on misconfiguration.
  **Decision taken**: reintroduced the fail-loud env-driven `backend` flag as new `elif` branches
  laid *after* the untouched `auto`/hook path (see §2 diff) - preserves both old and new callers.
- **No conformance-test pattern across backends** - each backend has its own bespoke test file
  (no shared parametrized harness). Ported Postgres tests in the same bespoke style as
  `test_field_pushdown_mongo.jac` (own file, own `testcontainers`/live-DB fixture), rather than
  inventing a new shared abstraction.
- **Toml `[optional-dependencies]` extras replaced by a code-based capability registry**
  (`capabilities.jac` `CAPABILITY_SPECS`/`INTENT_RULES`, consumed by `jac install`). Reinstating
  the psycopg dependency required a new `data.postgres` capability entry + `INTENT_RULES`
  keywords instead of a toml edit - this is a cross-cutting shared file (also consumed by byllm,
  k8s deploy, monitoring capability derivation), edited additively only.
- Relatedly: `config_loader.impl.jac`'s `database.backend` key and `capabilities.jac`'s
  `INTENT_RULES` `database.backend` key are two *different* consumers of the same toml field name
  (L3 runtime selection vs. `jac install` dependency-sync intent). They don't conflict today
  (`postgres` isn't in `INTENT_RULES`'s value map so capability derivation just ignores it), but a
  user declaring `backend = "postgres"` as jac.toml *intent* gets no automatic `jac install` sync
  unless `INTENT_RULES`/`CAPABILITY_SPECS` are also extended for that path - not done this round
  (out of scope; env-var/direct-flag path is what the benchmark harness uses, see ENV.md).

### UPSTREAM-BUG (ledger only, not fixed here - pre-existing, not introduced by this transplant)

- **`ScaleTieredMemory.postinit`'s `isinstance(hooked_l3, MongoBackend)` branch** misclassifies
  any non-Mongo hook-provided `PersistentMemory` (incl. a future hook-provided `PostgresBackend`)
  as `PersistenceType.SQLITE`. Only affects the `get_persistent_memory` plugin-hook path, not the
  `backend='postgres'` explicit-flag path this port actually wires (which sets
  `PersistenceType.POSTGRES` directly) - benign for the benchmark harness, flagged for whoever
  builds a hook-based Postgres provider later.
- **Root GTI blob write path has no CAS gate at all.** `topology_index_data` changes are invisible
  to `derive_dirty_fields` (archetype-fields-only scan), so a root anchor whose *only* change is
  its GTI blob falls back to `record_create()` → a blind full-document upsert with zero
  version/CAS protection - a stronger last-writer-wins hazard than the already-known
  FIELD_UPDATE-no-CAS gap. Pre-existing shared Mongo/memory-layer behavior, unrelated to this
  transplant; ledger only.
- **`_pg_merge_write` topology-cache invalidation gap - FIXED INLINE.** Commit `46ed1cb12`
  (`perf(topology): cache decoded topology index per anchor`) landed *after* the old port was cut
  and added `_topology_index_cache = None` invalidation to `SqliteMemory._merge_write`; the
  transplant missed the equivalent line in the new `_pg_merge_write`. Classified SAFE-ADAPT
  (mechanical, line-for-line parity restore) once found - fixed in `8a0eca7b1` (`stored_anchor.
  _topology_index_cache = None;` added to the topology branch). Verified benign-before-fix (cache
  is always cleared fresh by `Serializer._deserialize_anchor`, which always builds a new anchor
  object) but fixed for parity against future serializer identity-map reuse. All 3 conformance
  suites re-ran green after the fix (48/48).
- **`_process_cache` first-build race** on Mongo/Redis (unguarded check-then-set, no lock) predates
  this fork; PostgresBackend correctly uses a lock instead of copying the racy pattern (see §2).
- **`ScaleTieredMemory.batch_get` override skips the L2 write-through pipelining** that commit
  `de2da69fb` added to core `TieredMemory.batch_get`/`execute_plan` (`CacheMemory.batch_put`).
  `ScaleTieredMemory.batch_get` still loops individual `self.l2.put(anchor)` calls, so the
  optimization is inert for any caller going through the scale-tiered override (Mongo, Redis, and
  now Postgres all inherit this gap equally - not something this port introduced or should fix
  alone). **benchmarkImpact: true** - affects id-list/cross-root hydration paths on all three
  backends equally, so it's not a Postgres-specific disadvantage, but it *is* a ceiling that
  applies uniformly and should be understood before attributing any batch-hydration slowness to
  the backend choice itself.
- `RunConfig.ordered_traversal` toml-parse drop - pre-existing, unrelated to this port, and
  `ordered_traversal` is explicitly on the DO-NOT-TOUCH list. Ledger only.

## 4. BENCHMARK VALIDITY - read this before running numbers

Everything in this section is `benchmarkImpact: true` from the discovery/review passes.

1. **Transport parity is the harness's job, not this branch's.** This port's `postgresql_uri`
   accepts any libpq DSN, including a Unix-socket URI (`postgresql:///jactest`, used for *tests*
   in this repo). **Do not use a Unix-socket URI for comparative benchmark runs.** Prior numbers
   on the sibling checkout showed a PG-vs-Mongo −24% gap that was later found to be
   transport-confounded (PG over Unix socket vs. Mongo over Docker TCP, verified via
   `pg_stat_activity`), not a real engine difference. See ENV.md §"Transport parity" for the
   required TCP-URI recipe.
2. **Pushdown is inert on this backend.** `PostgresBackend.capabilities()`/`execute_plan()` are
   not overridden, so they fall to the `Memory` base defaults (empty). All query/sort/filter work
   happens in the runtime after a full anchor materialization - this is a known, accepted,
   *measured* gap (not a bug), and it means any depth/fanout advantage Postgres's SQL engine could
   offer via pushdown is not exercised by this backend as built. Advantage-scaling-with-hop-depth
   claims should account for this.
3. **Fetch-count units are not comparable across engines.** PG's `l3_fetch_count` = +1 per SQL
   round-trip (a batch of N ids = 1); Mongo's `fetch_count` = +len(ids) per batch. Do not diff
   these two counters directly as if they were the same metric.
4. **The `batch_get` L2 write-through pipelining gap (de2da69fb vs `ScaleTieredMemory.batch_get`)
   applies identically to Postgres, Mongo, and Redis** - a uniform ceiling on all three, not a
   Postgres-specific handicap, but worth knowing before attributing hydration-path latency
   differences to backend choice.
5. **Concurrent-write deadlock/loss path** (medium-severity review finding, report-only): PG's
   row-level `SELECT ... FOR UPDATE` makes lock-order deadlocks possible in a way sqlite's global
   `BEGIN IMMEDIATE` lock could not. A deadlock loser's whole transaction correctly rolls back
   (verified, no silent partial commit) but `TieredMemory.commit` only raises on `WriteConflict`
   - a deadlock-losing request today returns HTTP success while all its writes are silently
   dropped (logged only). **Irrelevant to single-user/read-path benchmarks; must be addressed
   before any concurrent-write (Locust) campaign against the Postgres backend.** Candidate fixes
   (not built): sort intents by anchor id within each stage for deterministic lock order, or map
   psycopg's `deadlock_detected` to `WriteConflict` so the boundary replays.
6. **Test suites green, 48/48**, all serial (`JAC_TEST_JOBS=0`) against local
   `postgresql:///jactest`: `test_postgres_backend.jac` (40), `test_postgres_selection.jac` (7),
   `test_postgres_e2e_integration.jac` (1). Plus the shared-seam regression gates (Mongo-backed,
   53/53 across factory/config/memory-hierarchy/OCC-replay suites) and backend-selection gate
   (7/7) - all pass, confirming the transplant did not disturb the Mongo/Sqlite paths.

## 5. See also

- `ENV.md` - TCP-URI transport-parity requirement, docker PG recipe, HANDOFF (env vars + commands
  for the harness session to run the MVP on this branch).
