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
| `JAC_CROSS_ROOT_RESOLVE` | off | Per-hop foreign-root GTI resolution. |
| `JAC_BATCH_L3` | off | Collapses frontier misses into one `$in`/`ANY()` fetch instead of per-id round-trips. |
| `JAC_READ_ONLY` | off | **WARNING**: silently drops writes at commit. A perf-isolation probe (measures read-path cost with write cost zeroed out), not a safety/dry-run mode - do not enable on anything you want persisted. |
| `JAC_API_LEAN_RESPONSE` | off | Drops the response envelope in the API layer (serialization-size ablation). |
| `JAC_PROJECTION` | unset | Format: `Type:f1,f2;Type2:f3`. Env-only - no `jac.toml` mirror. Supported on mongo (Route A) and postgres-rel (Routes A/B); no-op on postgres KV. |
| `JAC_ORDER_PUSHDOWN` | unset | Format: `NodeType:field:asc|desc`.`postgres-rel` (SQL `ORDER BY`) and, as of feat/housekeeping,`mongo` (Route-A final-hop `cursor.sort()`); no-op on postgres-KV. Malformed values raise ValueError (fail-loud parser in`runtimelib/utils.jac`). Experiment flag; text-sort semantics, so only safe for lexicographically-sortable fields (e.g. ISO-8601 timestamps), not general numeric/typed ordering. |
| `JAC_TOPOLOGY_SQL_CHAIN` | on | `postgres-rel` only, env-only (no toml mirror). Collapses a multi-hop chain into one SQL call instead of one query per hop. |
| `JAC_ORDERED_TRAVERSAL` | off | The `jac.toml` `[run] ordered_traversal` mirror key is wired as of feat/housekeeping (commit c7773bb6e); env var and toml key both work now. |
| `JAC_ACCESS_LOG` | on (truthy) | Uvicorn per-request access-log toggle; env wins over the `[server] access_log` toml key. Set `0` to silence the per-request log line for bench runs (floor-fix port, commit 1111c349a). |

**Pg read-path autocommit is not a flag.** The autocommit behavior on the Postgres read path (lineage: commit `5fbce338e`, `fix/pg-l3-read-trips`) is hardcoded always-on in this branch - there is no env var or toml key to toggle it off.

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
