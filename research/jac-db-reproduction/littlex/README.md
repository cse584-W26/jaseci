# littleX reproduction

This reproduces the colleague's W1/W2/W3 Jac-versus-hand-SQL matrix using
the original application and Python drivers. The current runtime target is
`32c5d1dbb`; historical full littleX results used `ad469c988`.

## Prepare and inspect (no services)

```sh
python reproduction/littlex/run.py --prepare
```

The plan contains 40 cells: four feed tiers × two arms, four tiers × three
write operations × two arms, and four mixed-write fractions × two arms.
Copies live here; original DBHarness files remain untouched.

## Run after the SNB load and other timed experiments finish

```sh
reproduction/runtime/venv/bin/python reproduction/littlex/run.py --run
```

The exact Python3.14 PBS runtime can be selected explicitly:

```sh
LITTLEX_JAC_BIN="$PWD/reproduction/runtime/bin/jac314" \
LITTLEX_PYTHON="$PWD/reproduction/runtime/venv314/bin/python" \
LITTLEX_SQL_PYTHON="$PWD/reproduction/runtime/venv-littlex-sql-locked/bin/python" \
LITTLEX_DRIVER_PYTHON="$PWD/reproduction/runtime/venv-littlex-driver-locked/bin/python" \
reproduction/runtime/venv314/bin/python reproduction/littlex/run.py --run
```

`LITTLEX_SQL_PYTHON` selects the SQL app and loader interpreter. It defaults
to the littleX-specific locked environment shown above. The original runner
used `uv run` from `littleXs/postgres`, whose own `uv.lock` pins FastAPI0.139.0,
uvicorn0.49.0standard (uvloop0.22.1,httptools0.8.0), psycopg3.3.4,
psycopg-pool3.3.1, Pydantic2.13.4, Starlette1.3.1 and PyJWT2.10.1.

HTTP drivers originally used the separate `harness/uv.lock` (httpx0.28.1,
psycopg3.3.4,PyJWT2.10.1). Optional `LITTLEX_DRIVER_PYTHON` selects that
interpreter for HTTP seeds, token export, counters, correctness and timing
drivers; default is the locked driver environment shown above. Both baseline
environments use isolated CPython3.13.16 PBS20261013, matching the original
littleX Python3.13 project requirement. Jac uses its existing Python3.14 launcher.
The SNB/TPC-C `benchmark/uv.lock` defines a different baseline dependency set.
Completion records include both selected Python paths and source lock hashes.

## Optional reusable Jac fixtures

Append `--reuse-fixtures` to seed each tier once through the original HTTP
seed walkers, then restore its PostgreSQL database before each measurement.
The stable app path preserves the runtime's path-derived project identity.
The template contains all graph and identity tables, so the original user
tokens and native target IDs continue to refer to the same fresh seed state.

Each tier has an owned project name `lx_repro_fixture_<tier>` and a fixture
directory keyed by seed/app/binary/source-commit hashes. Its snapshot database
is named `lx_repro_snapshot_<tier>_<hash>` and refuses client connections.
Before every cell, with the app stopped and no active DB connections, the
wrapper drops only that exact computed fixture project database and recreates
it using `CREATE DATABASE ... TEMPLATE ...`. The immutable snapshot is retained.
A new server process starts afterward; seed counts and the full feed/page
oracle run again before the unchanged warmup and request plan.

The wrapper never terminates other database sessions to force a restore.
Active sessions or an incomplete fixture cause an error. A process lock
prevents two fixture-based collections from overlapping. Each completion
record names the reset method, snapshot, fixture metadata hash and application
hashes. SQL cells retain the original TRUNCATE/reload path on PostgreSQL16.

This option changes setup/reset work outside timed spans. The restored
fixture smoke passed; see `FIXTURE_REVIEW.md` and `smoke/20261019T190254Z`.

## Aggregate and validate

```sh
python reproduction/littlex/aggregate.py
```

This checks the canonical40-cell sample/oracle evidence and writes
`summary/validation.json`, `summary/comparison.csv` and `summary/REPORT.md`.
The comparison includes the colleague's original0904JacCONTROL and hand-SQL
server p50 values and Jac/SQL ratios. Add `--allow-incomplete` while collecting.

For an initial end-to-end smoke:

```sh
reproduction/runtime/venv/bin/python reproduction/littlex/run.py \
  --run --tiers t20 --phases W1 --requests 10 --warmup 110
```

Successful cells are resumable via `data/<cell>/complete.json`. Each rerun
creates a new attempt directory. Use `--rerun` for a fresh measurement of
completed cells; use separate copies of this directory for smoke versus
canonical runs, or explicitly rerun smoke cells in the canonical collection.

## Isolation and checks

- Jac HTTP port 18120; hand-SQL HTTP port 18121. An occupied port is an error.
- Jac uses the reproduction-owned `dbcache` native PostgreSQL18 cluster;
  requires that cluster already bootstrapped by the main reproduction.
- Hand SQL uses PostgreSQL16.9 in the reproduction-owned Docker container
  `jac-db-reproduction-pg16`, reached over TCP at `127.0.0.1:55436`. This follows
  the original hand-SQL Docker/TCP topology (original port5433), separate from
  Jac's native cluster. The container is managed by the main reproduction.
- SQL admin connection defaults to
  `postgresql://postgres@127.0.0.1:55436/littleX`; override with
  `LITTLEX_SQL_ADMIN_DSN` (`LITTLEX_SQL_ADMIN_DSN` also accepted).
- Hand SQL uses only target database `littlex_reproduction_sql`; its loader
  truncates the three littleX tables before each SQL cell. Target database
  connection inherits the explicit admin DSN's TCP host/port/user settings.
- Jac uses a new copied app directory per cell attempt, hence a separate
  path-derived project database and fresh identity store. No database is dropped.
- Only processes launched by this script are terminated, by recorded process group.
- Seed files are generated locally from seed42 and the copied tweet pool.
- Every cell checks seed DB counts and seed-derived full-feed membership (W1)
  or ordered top20 parity (W2/W3) before timing.
- W2/W3 retain the original DB-truth write-delta oracle. Any nonzero timed
  request errors or failed oracle causes the cell to fail.
- Original defaults: 500 timed W1/W2 requests, 1000 W3, 110 untimed warmup.
- Every cell saves server/driver/oracle logs, per-request raw timings, summary
  CSV, source/binary hashes, and a completion record.

Do not run alongside SF1 loading, builds, or other timed benchmark cells.
The first SQL cell requires `psycopg` in the Python interpreter launching
this wrapper, as provided by `runtime/venv`.

## Initial smoke topology

The retained `smoke-complete.json` records used native PostgreSQL18/Unix socket
for the SQL arm during initial harness validation. They are diagnostic smoke
artifacts; canonical SQL measurements use the PostgreSQL16 Docker/TCP arm.

## Tier and configuration semantics

The tier labels mean **tweets per user**, with100 users and50 follows per user fixed. `t50` maps to the generator's `uniform` profile:

| Tier | Total follows | Total tweets | W1 full-feed tweets/user |
| --- | --- | --- | --- |
| t20 |5,000|2,000|1,000|
| t50 |5,000|5,000|2,500|
| t100 |5,000|10,000|5,000|
| t200 |5,000|20,000|10,000|

Source: `dataset/generate.py` profile definitions and the profile mapping in`run.py`.

The measured Jac revision`32c5d1dbb`uses **Final defaults**. With `JAC_LAZY_TXN`unset, this revision enables lazy transactions. Historical`ad469c988`CONTROL uses off and BEST uses on. Comparison against the historical CONTROL column spans both runtime revision and effective configuration. The separate IC5 c12/final32A/B has lazy transactions on in both revisions. Current run settings and historical references remain recorded separately.
