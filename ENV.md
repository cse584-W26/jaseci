# ENV - environment setup for feat/postgres-l3-r2

## Postgres backend selection

| Env var | Effect |
|---|---|
| `JAC_SCALE_BACKEND` | `auto` (default, untouched historical hook→Mongo→Sqlite path) \| `postgres` \| `mongodb` \| `sqlite`. Unknown value or unavailable backend on a non-`auto` value **raises** - no silent fallback. |
| `POSTGRESQL_URI` | libpq connection string. Required when `JAC_SCALE_BACKEND=postgres` - missing URI raises (never falls back to ambient libpq env like `PGHOST`). |

Env wins over `jac.toml`'s `[scale.database]` table (`backend`, `postgresql_uri` keys - top-level
`[scale]`, **not** `[plugins.scale]`).

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

Branch: `feat/postgres-l3-r2` (worktree `/home/aaron/Dev/Research/DatabaseResearch/JaseciFork-pgr2`).

```bash
cd /home/aaron/Dev/Research/DatabaseResearch/JaseciFork-pgr2   # always cd first - dev-mode
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

- `jac --version` / startup banner should say "compiler source at .../JaseciFork-pgr2/jac".
- `psql "$POSTGRESQL_URI" -c 'select 1'` succeeds over TCP (not a bare `psql dbname` peer-auth
  shortcut) before starting the harness.
- A misconfigured/unreachable Postgres with `JAC_SCALE_BACKEND=postgres` must raise at startup,
  not silently serve off Sqlite - if it doesn't raise, something regressed (see `PORT_NOTES_R2.md`
  §2/§3, fail-loud selection is load-bearing for benchmark trust).

See `PORT_NOTES_R2.md` for what shipped, the OCC/pool design, the full drift ledger, and the
BENCHMARK VALIDITY section (read before attributing any latency number to the backend).
