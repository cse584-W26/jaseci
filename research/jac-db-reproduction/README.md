# Jac database experiment reproduction

Reproduce the colleague's database experiments on clarity3, starting 2026-10-19. Copied applications, isolated services, datasets and raw evidence live here.

**Main report:** [REPORT.md](REPORT.md). **Stage status:** [scripts/STATUS.md](scripts/STATUS.md).

## Targets

- IC5 compiler/runtime A/B: baseline `c12ba889d` vs final `32c5d1dbb`, unchanged walker, 20 official parameter rows, canonical result hashes, SQL census and paired latency.
- Seven SNB query classes: 140 canonical hashes plus the original 140-warm / 2,550-timed schedule.
- TPC-C W1: seed 42 data, seed 4242 plan, 100 warm + 800 timed transactions, seven database-truth checks.
- littleX W1 feed, W2 writes and W3 mixed workloads with fresh state and per-cell oracles.

Current final-runtime Jac measurements use **Final defaults**. Unset `JAC_LAZY_TXN` means on in both IC5 c12 and final32 revisions. Historical `ad469c988` CONTROL has lazy transactions off. Edge-only-dirty is already default-on for PostgreSQL in ad469. Historical broad-matrix revisions are SNB/littleX `ad469c988` and TPC-C `fb13cf14e`; their source/configuration labels remain separate.

## Completed core evidence

- Exact IC5 SQL totals **278,769 → 432**, zero structural SQL in both census windows and all outputs matching.
- Logging-off IC5 median **6,506.320 → 110.206 ms**, with 40 baseline and 60 final paired requests.
- Canonical SNB completed on four arms: Jac Final defaults and dependency-locked PostgreSQL, SQLAlchemy and Neo4j. Each has 140 warm requests, 2,550 timed requests, zero errors and all 140 historical hashes matching.
- TPC-C Jac and locked PostgreSQL/SQLAlchemy each complete the exact 900-entry plan, seven expected rollbacks, all seven truth checks and the historical golden final counts.
- Official SF1 inputs have checksums; W1 data was generated twice with byte-identical hashes. The locked baseline environment exactly matches all 28 registry packages from the original shared benchmark lock.
- Independent offline validation: [core-artifact-validation.json](results/core-artifact-validation.json). Run `runtime/venv314/bin/python scripts/verify_core_artifacts.py` to recheck counts, schedules, hashes, plan identity and golden counts without database requests.
- Historical littleX CONTROL original-recipe collection passes all 40 cells,24,000 timed requests and sample/state/PID/oracle checks. Its W1/W3 trends repeat; W2 t20 ordering differs from the historical reference. Completed diagnostics quantify the present common commit cost, Jac execution overhead and the historical-reference variability. Final32 fresh-state measurements are retained separately.

Completed controlled diagnostics identify missing planner statistics behind the additional fresh-fixture t20 feed gap, and a projection retry cooldown behind the short-warm page-profile gap. Logged INSERT+COMMIT medians are1.240 ms on PG16 and 1.211 ms native, versus recorded historical 6.399/6.340 ms. See [diagnostic synthesis](littlex/DIAGNOSTIC_REPORT.md).

All workload collection is finished. Owned benchmark API services are stopped; databases, snapshots and raw artifacts remain available. Both clusters have logging off, no database logging overrides and fsync/synchronous_commit on: [final state](logs/final-state.json). Earlier dependency-unmatched pilots and the failed first locked startup attempt remain archived.

## Topology and provenance

JacSNBHTTP18109;JacTPC-CHTTP18108;handSQLSNBHTTP18111;handSQLTPC-CHTTP18112. Jac's owned cluster lives in `dbcache/pg/main`,socket`/tmp/jacpg-d6275e76eb`. Dedicated PostgreSQL 16 container`jac-db-reproduction-pg16` is reached on 127.0.0.1:55436.

Runtime/source inventory: [runtime/README.md](runtime/README.md), [environment.json](environment.json). Per-launch commands and flags: `logs/*-launch.json`. Dataset checksums: [data/manifest.json](data/manifest.json), [benchmark/tpcc/data/manifest.json](benchmark/tpcc/data/manifest.json).

## Independent rerun order

Commands below run from `/home/baichuan/jaseci/reproduction`, using `runtime/venv314/bin/python`. Run one measurement sequence at a time. Loading steps target fresh experiment state; loaders reset their named relational database or add their defined Jac cohorts. Preserve existing raw results under a new tag/directory when repeating.

### 1. Prepare runtime, data and owned database services

Follow [runtime/README.md](runtime/README.md) for the pinned interpreter/source wrappers. Use the official URLs and checksums in `data/manifest.json`, and generateTPC-C with:

```sh
runtime/venv314/bin/python benchmark/tpcc/gendata.py --out benchmark/tpcc/data
```

The dedicated PostgreSQL 16 container must be available at55436,and Jac's native cluster must be bootstrapped by its runtime. Existing container identity and database names must match this reproduction's launch records. [REPORT.md](REPORT.md#3-reproduction-environment-and-topology) records topology.

### 2. Load hand SQL and Jac SNB

```sh
export JAC_CACHE_HOME="$PWD/dbcache"
runtime/venv314/bin/python scripts/load_postgres.py
runtime/venv314/bin/python scripts/manage.py start pg
runtime/venv314/bin/python scripts/manage.py start jac --variant final
runtime/venv314/bin/python benchmark/scripts/pg_bulk_load.py --bench snb --app "$PWD/benchmark/snb/jaseci-pg" --base http://127.0.0.1:18109 --mode init
runtime/venv314/bin/python benchmark/scripts/pg_bulk_load.py --bench snb --app "$PWD/benchmark/snb/jaseci-pg" --base http://127.0.0.1:18109 --mode control
runtime/venv314/bin/python benchmark/scripts/pg_bulk_load.py --bench snb --app "$PWD/benchmark/snb/jaseci-pg" --base http://127.0.0.1:18109 --mode mini-bulk
runtime/venv314/bin/python scripts/manage.py start jac --variant final
runtime/venv314/bin/python benchmark/scripts/pg_bulk_load.py --bench snb --app "$PWD/benchmark/snb/jaseci-pg" --base http://127.0.0.1:18109 --mode gate3
runtime/venv314/bin/python benchmark/scripts/pg_bulk_load.py --bench snb --app "$PWD/benchmark/snb/jaseci-pg" --base http://127.0.0.1:18109 --mode full --data "$PWD/data/social_network-sf1-CsvBasic-LongDateFormatter"
```

Set `JAC_CACHE_HOME="$PWD/dbcache"` for all direct Jac-database helpers, including `pg_bulk_load.py`, so their socket autodetection selects the owned cluster. The `manage.py` process sets this itself. Read full loader logs and verify counts before proceeding. The REST arms also need `benchmark/snb/tokens.json` with a `svc` HS256 token (payload `{"svc": "snb_svc"}`, secret matching the original apps' `JWT_SECRET`, default `supersecretkey_for_testing_only!`). Keep Jac's separately registered `svc_token.json` and generated target maps from the loader.

### 3. Provision canonical physical structures offline

For the current copied app the database is `jac_snb_bench_pg_fbdb3a2c`; discover and substitute the name if the absolute project path changes. `vacuum_control.py` currently names this exact database and should be updated before relocating the reproduction.

```sh
runtime/venv314/bin/python scripts/manage.py stop jac
runtime/venv314/bin/python scripts/vacuum_control.py pause
runtime/venv314/bin/python scripts/provision_runtime.py --database jac_snb_bench_pg_fbdb3a2c --execute
runtime/venv314/bin/python scripts/vacuum_control.py restore
runtime/venv314/bin/python scripts/vacuum_control.py vacuum
```

Restore autovacuum even if provisioning fails. Inspect saved `logs/provision-runtime-*.json` for each method's success; supported resume options are documented in [runtime/MIRROR_WARMUP.md](runtime/MIRROR_WARMUP.md).

### 4. Warm the baseline process and collect its SQL census

```sh
runtime/venv314/bin/python scripts/db_settings.py off
runtime/venv314/bin/python scripts/manage.py start jac --variant baseline
runtime/venv314/bin/python scripts/warm_snb.py
runtime/venv314/bin/python scripts/gate.py --tag baseline-warmup --queries is1,is2,is3,ic1,ic2,ic5,ic13 --warm 1 --rounds 1
runtime/venv314/bin/python scripts/db_settings.py census
runtime/venv314/bin/python scripts/gate.py --tag baseline-census --warm 1 --rounds 1 --census
runtime/venv314/bin/python scripts/db_settings.py off
```

`warm_snb.py` is an initial warm pass, **not a complete readiness proof**. A process restart resets mirror memos and can trigger full base-table scans despite pre-existing durable mirrors. Projection lock retries also have cooldowns. Inspect warm logs and repeat requests after cooldown until relevant projections are complete; require structural SQL0 in the measured census. [runtime/MIRROR_WARMUP.md](runtime/MIRROR_WARMUP.md) explains the exact checks. Keep the process alive between census and logging-off latency.

### 5. Run the serialized measurement sequence

```sh
runtime/venv314/bin/python scripts/run_snb_matrix.py
```

This runner assumes the baseline process is already warmed and its census is complete. It measures baseline IC5 with statement logging off, checks remaining-query parity, profiles the baseline, restarts the final variant, pays final warmup, collects final census, turns logging off, and collects all seven final query timings and profiles. Every stage writes its own log; `results/snb-stage-progress.json` records exit codes and elapsed time. A nonzero stage stops the runner. Check final structural SQL before interpreting a final timing table. Keep profiling results separate from latency-only results.

### 6. TPC-C and littleX

TPC-C loading, authentication, driver and oracle commands: [scripts/TPCC_RECIPE.md](scripts/TPCC_RECIPE.md). Run each arm from a fresh load; `scripts/tpcc_gate.py` emits raw100 warm+800 timedCSV plus7 truth checks. Jac seeding:

```sh
runtime/venv314/bin/python scripts/manage.py start tpcc
runtime/venv314/bin/python benchmark/tpcc/jaseci-pg/seed.py --base-url http://127.0.0.1:18108 --data benchmark/tpcc/data
```

littleX's canonical matrix and fixture/reset mechanism: [littlex/README.md](littlex/README.md). Optional SQLAlchemy/Neo4j setup: [optional-baselines/README.md](optional-baselines/README.md). Coordinate their starts,loadsandmeasurementswith the main sequence; optional SQLAlchemy must use an unused HTTP port because18112 belongs toTPC-C.

## Evidence locations

- [Initial final SNB summary](results/final-initial-parity/summary.json)
- [Completed baseline census](results/baseline-census/summary.json)
- [TPC-C PostgreSQL 16 truth oracle](results/tpcc-postgres16/tpcc_postgres.oracle.json)
- [Jac TPC-C seed counts](results/tpcc-seed-counts.json)
- Final consolidated comparisons: [REPORT.md](REPORT.md#6-final-reproduced-results)

## littleX tier meaning

`t20`/`t50`/`t100`/`t200` means20/50/100/200 tweets per user. Every tier has 100 users and 50 follows per user (5,000 total follows). Total tweets are2,000/5,000/10,000/20,000; W1 full feeds contain1,000/2,500/5,000/10,000 tweets per user. The `t50` case uses the generator's `uniform` profile. See [generator](../DBHarness/dataset/generate.py:20) and [littleX instructions](littlex/README.md).

## Original-recipe littleX primary group

Historical `ad469c988` CONTROL uses the original cohort/process boundaries: one SQL server across12 cohorts,12 fresh Jac cohort processes, and W2 like→follow→create_tweet sharing state within each tier. Entry points (only during an allocated measurement window):

```sh
runtime/venv314/bin/python littlex/original_recipe.py
runtime/venv314/bin/python littlex/original_recipe.py --run
runtime/venv314/bin/python littlex/aggregate_original.py
runtime/venv314/bin/python scripts/verify_littlex_original.py
```

The first command prints the plan. Fixed completed run: `littlex/original-recipe/20261019T193716Z`. Independent audit: [littlex-original-independent-validation.json](results/littlex-original-independent-validation.json). The separate `littlex/run.py` fresh-state collection is an additional group with different reset/process boundaries.

## Completed W2 follow-up

Three uninstrumented rounds validate 18 cells and 9,000 timed requests. The current write gap is stable; measured extra SQL, lookups, follow traversal and configuration parsing characterize its execution costs. The archived historical t20 arms were collected roughly 44 minutes apart, and their original per-request profiles do not identify a unique historical cause.

[Detailed investigation](write-investigation/REPORT.md), [independent audit](write-investigation/HISTORICAL_AUDIT.md), [function spans](littlex/WRITE_FUNCTION_SPANS.md), [figure PDF](write-investigation/write-costs.pdf). All follow-up workloads are finished; HTTP ports 18120/18121 are closed, scratch databases removed and the fixture restored: [follow-up final state](write-investigation/final-state.json).
