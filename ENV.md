# ENV - flag reference for bench/all-flags

## Postgres backend selection

| Env var | Effect |
|---|---|
| `JAC_SCALE_BACKEND` | `auto` (default, untouched historical hook→Mongo→Sqlite path) \| `postgres` \| `postgres-rel` \| `mongodb` \| `sqlite`. Unknown value or unavailable backend on a non-`auto` value **raises** - no silent fallback. |
| `POSTGRESQL_URI` | libpq connection string. Required when `JAC_SCALE_BACKEND=postgres` or `postgres-rel` - missing URI raises (never falls back to ambient libpq env like `PGHOST`). |
| `JAC_TOPOLOGY_SQL` | `postgres-rel` only: `0`/`false` disables the SQL hop resolver (rel storage stays, hops go back to GTI blob/walk). Default on. Ablation control - see `PORT_NOTES_REL.md`. |

`postgres-rel` = the edges-as-rows backend (KV anchor store + `edges` index table answering
hops via indexed SQL; works with `JAC_TOPOLOGY_INDEX=0`, i.e. no GTI blobs at all). Seed through
it (walkers/apply or put) - a KV-seeded database has NO edge rows, so selecting postgres-rel on
one yields empty traversals. Rel test suites use database `jactest_rel` (`POSTGRESQL_REL_URI`),
disjoint from the KV suites' `jactest`.

Env wins over `jac.toml`'s `[scale.database]` table (`backend`, `postgresql_uri` keys - top-level
`[scale]`, **not** `[plugins.scale]`).

## Other flags

| Env var | Default | Scope / notes |
|---|---|---|
| `JAC_TOPOLOGY_INDEX` | on | Gates the GTI **write** hooks only (`on_edge_created/destroyed`, `on_node_saved/destroyed`) - reads always use whatever GTI blobs already exist, flag has no read-path effect. |
| `JAC_CROSS_ROOT_RESOLVE` | off | Foreign-root GTI resolution, two tiers. (1) Whole-chain: unsliced multi-hop chains with predicate-free prefixes resolve in index space via a frontier of `(index, ids)` groups (`TopologyIndex.resolve_chain_cross_root`, ported from `fp-new-main`) -- each hop resolves inside the owner root's index, so 3+ hop chains through foreign territory stay off the walk; one batched foreign-root fetch per hop; foreign index decode goes through gti_cache when `JAC_GTI_CACHE` is on. A node-field predicate on the *final* hop is fine: the chain resolves structurally, then the predicate applies at the materialization boundary (backend field pushdown where caps allow, retained post-filter otherwise). A final-hop *edge* predicate resolves the prefix on the frontier and walks only the last hop. Any load failure bails to the per-hop path (never undercounts). (2) Per-hop: `_resolve_hop_cross_root`, engages when the whole-chain gate doesn't (mid-chain predicates, slicing); maps foreign ids through the home root's index each hop, so it falls to the walk once a hop yields nodes the home index has never seen. toml mirror `[run] cross_root_resolve`. |
| `JAC_BATCH_L3` | off | Collapses frontier misses into one `$in`/`ANY()` fetch instead of per-id round-trips. |
| `JAC_GTI_CACHE` | off | Process-level cache of decoded GTI: `root_id -> (blake2b(blob), TopologyIndex)` LRU (`runtimelib/gti_cache.jac`). Read-path only (resolver local + cross-root index decode); digest check makes stale hits impossible, root-id keying replaces superseded versions. Cached entries are frozen (mutators raise). Known tradeoff: write hooks still decode a private copy, so a write-after-read request pays one extra decode by design. Backend-agnostic. Cap: `JAC_GTI_CACHE_SIZE` (env-only, default 1024 roots, fail-loud parse). toml mirror `[run] gti_cache`. |
| `JAC_READ_ONLY` | off | **WARNING**: silently drops writes at commit. A perf-isolation probe (measures read-path cost with write cost zeroed out), not a safety/dry-run mode - do not enable on anything you want persisted. |
| `JAC_API_LEAN_RESPONSE` | off | Drops the response envelope in the API layer (serialization-size ablation). |
| `JAC_PROJECTION` | unset | Format: `Type:f1,f2;Type2:f3`. Env-only - no `jac.toml` mirror. Supported on mongo (Route A) and postgres-rel (Routes A/B); no-op on postgres KV. |
| `JAC_ORDER_PUSHDOWN` | unset | Format: `NodeType:field:asc|desc`.`postgres-rel` (SQL `ORDER BY`) and, as of feat/housekeeping,`mongo` (Route-A final-hop `cursor.sort()`); no-op on postgres-KV. Malformed values raise ValueError (fail-loud parser in`runtimelib/utils.jac`). Experiment flag; text-sort semantics, so only safe for lexicographically-sortable fields (e.g. ISO-8601 timestamps), not general numeric/typed ordering. |
| `JAC_TOPOLOGY_SQL_CHAIN` | on | `postgres-rel` only, env-only (no toml mirror). Collapses a multi-hop chain into one SQL call instead of one query per hop. |
| `JAC_ORDERED_TRAVERSAL` | off | The `jac.toml` `[run] ordered_traversal` mirror key is wired as of feat/housekeeping (commit c7773bb6e); env var and toml key both work now. |
| `JAC_ACCESS_LOG` | on (truthy) | Uvicorn per-request access-log toggle; env wins over the `[server] access_log` toml key. Set `0` to silence the per-request log line for bench runs (floor-fix port, commit 1111c349a). Also gates the function-endpoint request echo (`Executing function '<name>' with params: ...` console.print in serve.endpoints) - same per-request-logging concept, resolved once at endpoint registration. |

| `JAC_READ_AUTOCOMMIT` | on (truthy) | Postgres read-path autocommit (lineage: commit `5fbce338e`). Default-on: reads take connections in autocommit so the pool return check finds them IDLE, saving a ROLLBACK round trip per read. Set `0` to restore pre-fix behavior for A/B ablation. Covers both postgres and postgres-rel via `PostgresBackend._read_conn`. |
| `JAC_LAZY_HYDRATION` | off | Floor/walk-path (`_materialize_ids`) lever: hands callers id-only NodeAnchor stubs (marker `_lazy_stub`) and defers archetype hydration until a field is read; the deferred `populate()` is an L1 hit (the batch_get already fetched + cached), so it is batched, never a per-anchor L3 refetch. Env-only, backend-agnostic. **Note:** inert on the GTI/topology fast path -- mid-chain pass-through nodes are already resolved as bare UUID sets there, no anchor is built, so there is nothing to defer; it only engages when a hop falls to the walk fallback (GTI off / cross-root miss). Composes with `JAC_PROJECTION` (distinct markers; projection materializes via the pushdown path, lazy via the floor path). |
| `JAC_REPORT_ECHO` | on (truthy) | Gates the per-`report`-statement console echo in `JacBuiltin.log_report` (jac0core). Default ON = upstream behavior (CLI walker reports print to stdout). The echo str-formats the FULL report payload inside the timed span and was the dominant source of the multi-hundred-MB bench server logs (one full-feed repr line per feed request). Resolved once at module import - set before boot; `0` to silence for bench runs. |
| `JAC_MEM_POOL` | off | Reuses a per-worker free-list of `ScaleTieredMemory` instances across requests instead of rebuilding one per request (backend selection + Redis probe + l1 registration). On checkout and on release the instance's L1 (`__mem__`) and pending `changes` are scrubbed, preserving the multi-tenant isolation invariant (no request-N data visible to request N+1). Env-only; scale server only (`JScaleExecutionContext`). |

## Transport parity - TCP URI required for comparative runs

**Use a TCP URI (`postgresql://user@host:port/db`) for any benchmark/comparison run. Do not use
a Unix-socket URI (`postgresql:///dbname`) for comparative numbers.**

Why: the harness's other engines (Mongo via Docker) are reached over Docker's TCP bridge network,
which pays real socket/kernel-network overhead that a local Unix-socket Postgres connection does
not. Mixing transports previously produced a PG-vs-Mongo −24% latency gap that was entirely
transport noise, not an engine difference (verified via `pg_stat_activity`). Unix-socket URIs are
fine for **tests only** (this repo's test suites use local `postgresql:///jactest` deliberately,
since they're checking correctness, not latency).

### Docker Postgres recipe (TCP, matches the Mongo container's network shape)

```bash
docker run -d --name jacdb-pg \
  -e POSTGRES_USER=jac -e POSTGRES_PASSWORD=jac -e POSTGRES_DB=jacbench \
  -p 5432:5432 \
  postgres:16

# wait for readiness
until docker exec jacdb-pg pg_isready -U jac; do sleep 1; done

export JAC_SCALE_BACKEND=postgres
export POSTGRESQL_URI="postgresql://jac:jac@127.0.0.1:5432/jacbench"
```

If Mongo runs in the same `docker network` / compose file, put Postgres on it too rather than
`-p`-publishing to the host, so both engines cross the same bridge (host-published `-p 5432:5432`
is fine as a fallback - still real TCP/loopback, not a Unix socket - but same-network is closer
to how the Mongo container is reached).

## HANDOFF - running the MVP on this branch

Branch: `bench/all-flags`. Worktrees: main checkout `/home/aaron/Dev/Research/DatabaseResearch/JaseciFork`
(on `bench/all-flags`), plus `/home/aaron/Dev/Research/DatabaseResearch/JaseciFork-lean`
(`feat/lean-response`) and `/home/aaron/Dev/Research/DatabaseResearch/JaseciFork-pgrel`
(`feat/pg-rel-mvp`). `JaseciFork-pgr2` does not exist - superseded, do not look for it.

```bash
cd /home/aaron/Dev/Research/DatabaseResearch/JaseciFork   # always cd first - dev-mode
                                                             # source resolution is cwd-relative

# 1. Postgres reachable over TCP (see recipe above), then:
export JAC_SCALE_BACKEND=postgres
export POSTGRESQL_URI="postgresql://jac:jac@127.0.0.1:5432/jacbench"

# 2. Deps (once per venv/global site - mirrors project/capabilities.jac's data.postgres pins):
jac install "psycopg[binary,pool]" --global   # or: jac install (if jac.toml declares the capability)

# 3. Run the app - jac dev-mode routes to THIS worktree's jaclang.scale as long as cwd is here:
jac start <your_app>.jac
```

Sanity checks before trusting numbers:

- `jac --version` / startup banner should say "compiler source at .../JaseciFork/jac" (or the
  worktree you `cd`'d into).
- `psql "$POSTGRESQL_URI" -c 'select 1'` succeeds over TCP (not a bare `psql dbname` peer-auth
  shortcut) before starting the harness.
- A misconfigured/unreachable Postgres with `JAC_SCALE_BACKEND=postgres` must raise at startup,
  not silently serve off Sqlite - if it doesn't raise, something regressed (see `PORT_NOTES_R2.md`
  §2/§3, fail-loud selection is load-bearing for benchmark trust).

See `PORT_NOTES_R2.md` for what shipped, the OCC/pool design, the full drift ledger, and the
BENCHMARK VALIDITY section (read before attributing any latency number to the backend).
