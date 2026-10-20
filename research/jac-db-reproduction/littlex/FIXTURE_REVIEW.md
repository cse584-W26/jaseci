# Fixture reuse: review and runtime smoke

## Topology

- Jac: final source32c5d1dbb, Python3.14 PBS launcher, native PostgreSQL18,
  reproduction-owned `dbcache`, HTTP18120.
- Hand SQL: PostgreSQL16 Docker/TCP `127.0.0.1:55436`, own target database
  `littlex_reproduction_sql`, HTTP18121.
- The SQL loader, token mint/export, app pool and count oracle all receive
  the target DATABASE_URL produced from the explicit admin DSN.

## Why database restore preserves identity

Runtime `project_db_name` (`session.impl.jac`) computes
`jac_<manifest project name>_<sha1(absolute app path)[:8]>`.
The fixture uses one stable app path and project name per tier/version.
Auth identity rows, roots and graph anchors are in this same project DB.
Cloning all its tables preserves the original JWT subjects, roots and native
target IDs; token-map hashes are checked before reuse. Every cell repeats
authenticated requests for all100users through the seed-derived feed/page oracle.

## Reset safety

- Only the exact path-derived `jac_lx_repro_fixture_*` database is dropped.
- Snapshot name is explicitly `lx_repro_snapshot_*`; provenance binds seed,
  all Jac sources, manifest, seeding driver, launcher and source commit.
- The snapshot rejects client connections; restore checks it exists and
  `datallowconn=false` before dropping the mutable project database.
- Source/target DBs must have zero active connections before cloning.
- No `pg_terminate_backend`, forced drop, shared-cluster reset, or global kill.
- A lock serializes fixture users; each measurement restarts the app process.
- Seed counts are checked after every restore before correctness and warmup.
- A missing mutable DB after an interrupted clone can be recovered from the
  retained snapshot; incomplete initial seeding requires inspection.

## Window command

Plan inspection (no services/load):

```sh
python reproduction/littlex/fixture_smoke.py
```

Execute only in the main agent's assigned nonoverlapping window:

```sh
reproduction/runtime/venv314/bin/python \
  reproduction/littlex/fixture_smoke.py --execute
```

The diagnostic runs t20 Jac W1, three W2 operations, W1 again, and PG16 W1.
Each has110warm+10timed requests. This validates restored auth, count reset,
unchanged feed/page semantics and write-delta oracles after mutations.
Completion artifacts are archived under `smoke/<timestamp>/` and removed
from canonical resumable markers. Original per-attempt logs/rawCSV are retained.

## Runtime validation

The assigned smoke completed successfully at `smoke/20261019T190254Z`:

- t20 initial seed:100profiles,2000tweets,5000follows.
- Initial clone and restore:100-user feed oracle,110warm+10timed,zeroerrors.
- CreateTweet,Follow,Like: each started from the same seed counts; each
  database-truth delta120 matched110warm+10timed successful writes.
- Post-write restore: original seed counts and100-user full-feed oracle passed.
- PostgreSQL16 TCP arm: seed counts and100-user feed oracle passed.
- All diagnostic completion records were archived outside canonical markers.

Canonical aggregation is available via `python littlex/aggregate.py` after
collection; `--allow-incomplete` produces a progress report. It verifies40cells,
500/1000timed requests, raw timing counts, warmup, errors, seed/feed/write
oracles, fixture hashes and the SQL topology, and compares historical CONTROL
and hand-SQL server p50 values.
