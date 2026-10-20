# Jac Database Experiment Reproduction

## Result status

- **IC5:** SQL totals exactly reproduce **278,769 →432**. Logging-off Jac median improves **59.04×**, from6,506.320 to110.206 ms; canonical reported-result hashes agree throughout.
- **SNB/TPC-C:** all four canonical SNB arms complete140 warm +2,550 timed requests with 140 matching hashes each. All three TPC-C arms pass the exact900-entry plan and seven truth checks.
- **littleX:** historical CONTROL's original 40-cell recipe passes all samples and oracles. W1 feed growth and Jac's W3 feed_page advantage repeat. **W2 t20 changes ordering:** historical Jac was slightly faster than SQL; current historical-source Jac is slower. Completed write diagnostics quantify current costs and document historical variability; the original cause of the historical t20 ordering is not identified.

Coverage: IC5 source A/B, final-defaults SNB/TPC-C, historical littleX CONTROL/SQL, and the additional final-defaults fresh-state littleX group have local measurements. Historical SNB/TPC-C CONTROL/BEST rows and littleX BEST/SQLAlchemy/Neo4j comparisons remain archived reference results; local SNB/TPC-C Jac rows use Final defaults.

Status date: 2026-10-19. Host: clarity3. All relative paths below are rooted in this reproduction directory unless prefixed `../DBHarness/` or `../jac-db/`.

## 1. Research claims and reproduction targets

The project optimizes persistent Jac applications while preserving their application code and results. This reproduction distinguishes two historical experiments with different runtime revisions:

1. **September 5 IC5 optimization ladder:** compare start-of-session Jac with its final compiler/runtime, holding the walker text fixed. Test canonical JSON result-hash equality on 20 official parameter rows, count warmed SQL statements, and measure paired Jac/hand-SQL latency. The primary work-reduction target is **278,769 → 432 SQL statements over 20 requests**.
2. **September 4 broader workload matrix:** seven SNB read queries; TPC-C W1 New-Order and Payment; littleX feed, writes, and mixed workloads. These use older runtime revisions and CONTROL/BEST flag sets. Reproduce correctness, operation counts, and relative performance with versions stated per cell.

The benchmark's `ic5_new_forums` uses **one-hop friends**, as expressed by its served Jac and SQL implementations. This workload definition is the reproduction target.

### Source identity

| Component | Historical/reproduction revision | Role |
|---|---|---|
| DBHarness checkout | `36f8b291fe24f35d9285869063e912edc0c14446` | Applications, drivers, tracked raw historical results |
| IC5 baseline Jac | `c12ba889d484d7fcdfb3780ac98d416d1e13ec8b` | September 5 start-of-session compiler/runtime |
| IC5 final Jac | `32c5d1dbb9507571235783e78e35b1022cacc4e4` | September 5 final D5 compiler/runtime |
| September 4 SNB/littleX Jac | `ad469c988` | Historical broad-matrix runtime |
| September 4 TPC-C Jac | `fb13cf14e` | Broad-matrix runtime plus `enumerate` object-prefetch matcher fix |
| Historical TPC-C idiom application | DBHarness `06915ac` | Application shape served in final historical TPC-C runs |
| Historical pre-idiom TPC-C application | DBHarness `bb95d9f` | Same-runtime application-shape diagnostic |

Latest-runtime measurements answer how the final compiler behaves on those applications. Exact historical broad-matrix comparisons additionally require the historical runtime and flag set named above. The IC5 baseline/final comparison is a source-revision A/B; historical CONTROL/BEST is a flag A/B.

SNB application SHA256: `60aa325001594bf900a8ebcfa24dd1d36fa0f00d0fd3fc9589a781f37f9a32a7` (`benchmark/snb/jaseci-pg/app.jac`). Keep an application hash with every result set.

## 2. Historical reference results

### 2.1 IC5 ladder: recomputed from raw JSON

Each row below is recomputed from `../DBHarness/session0904/ic5/build/gates/ic5_<tag>.json`: 20 requests, conventional arithmetic median for even-sized samples. These raw-data values are the reference for numerical comparisons. The implementer's prose report contains rounded or different-window headline numbers.

| Raw tag | SQL statements, total | Median statements/request | Jac median ms | Paired PostgreSQL median ms | Result parity |
|---|---:|---:|---:|---:|---:|
| base | 278,769 | 11,256.5 | 7,542.00 | 80.35 | 20/20 |
| A | 656 | 30 | 191.35 | 84.30 | 20/20 |
| AB | 657 | 30 | 120.65 | 64.95 | 20/20 |
| ABC1 | 230 | 12 | 103.45 | 60.65 | 20/20 |
| ABC | 229 | 12 | 104.15 | 60.05 | 20/20 |
| ABCD1 | 229 | 12 | 126.90 | 82.60 | 20/20 |
| FULL | 269 | 14 | 69.25 | 51.10 | 20/20 |
| D4 | 269 | 14 | 78.95 | 63.90 | 20/20 |
| FINAL | 269 | 14 | 109.10 | 75.85 | 20/20 |
| D5 | 432 | 22.5 | 75.50 | 60.05 | 20/20 |

The recorded optimization sequence is batch adjacency prefetch, nested-hop membership/count aggregation, predicate-aware inbound prefetch, field projection, aggregation access-plan changes, SQL Top-K, and delayed object hydration. Mechanism descriptions and commit mappings: `../DBHarness/session0904/ic5/build/REPORT.md` and each rung's `*_IMPL.md`. Historical experiments ran on a busy machine; the implementer treats statement counts and result equality as the hard evidence.

### 2.2 September 4 SNB matrix

Historical client p50 in milliseconds, as banked in `../DBHarness/session0904/run/data/snb/snb_master.csv` and presented in `../DBHarness/session0904/run/AB_TABLE.md`:

| Query | PostgreSQL | SQLAlchemy | Neo4j | Jac CONTROL | Jac BEST |
|---|---:|---:|---:|---:|---:|
| IS1 | 0.91 | 1.30 | 1.47 | 2.66 | 2.44 |
| IS2 | 9.95 | 7.91 | 2.10 | 5.30 | 4.36 |
| IS3 | 1.38 | 1.92 | 1.93 | 4.06 | 3.70 |
| IC1 | 28.33 | 83.62 | 7.42 | 5.84 | 5.67 |
| IC2 | 42.79 | 41.33 | 15.28 | 9.94 | 8.53 |
| IC5 | 73.48 | 61.24 | 17.09 | 4,632.08 | 4,567.20 |
| IC13 | 23.15 | 47.43 | 2.60 | 22.57 | 21.53 |

Historical conclusion: query-dependent performance, including faster Jac IC1/IC2 and a substantial IC5 gap subsequently targeted by the September 5 ladder. All five arms agree on 140 hashes (seven queries × 20 rows). Raw CSV/meta/hash files are under `../DBHarness/session0904/run/data/snb/{postgres,sqlalchemy,neo4j,control,best}/`.

The historical timed schedule uses 750 IS repetitions and 75 IC repetitions over the surviving 20-row parameter set after a full warm pass. Reproduction pilot gates use shorter schedules and retain their actual sample counts.

### 2.3 September 4 TPC-C W1 matrix

Historical client p50 milliseconds:

| Operation | PostgreSQL | SQLAlchemy | Jac CONTROL | Jac BEST |
|---|---:|---:|---:|---:|
| New-Order | 9.97 | 23.30 | 14.05 | 13.78 |
| Payment | 7.98 | 10.66 | 10.82 | 10.65 |

Source: `../DBHarness/session0904/run/data/tpcc/tpcc_master.csv`, per-arm CSV/meta files, and `../DBHarness/session0904/run/AB_TABLE.md`. Historical final Jac cells use `fb13cf14e`; the earlier `ad469c988` cells are retained separately in `data/tpcc_pre_prefetch_fix/`.

Workload: W=1, sequential single-client plan seed 4242, 100 mutating warm transactions +800 timed transactions. The full 900-entry plan yields487 successful New-Order,406 Payment and 7 rollbacks; timed800 includes437 successful New-Order,357 Payment and 6 rollbacks. Raw timing CSV groups those6 rollbacks with New-Order, so its New-Order count is 443.

All historical arms finish at: orders30,487; order_line305,500; new_order9,487; history30,406; next_o_sum30,497; warehouse YTD1,362,049.86; consistency_bad0. Historical conclusion: New-Order places Jac between hand SQL and the ORM. Payment is slightly slower on Jac CONTROL/BEST than the ORM, with a small CONTROL/BEST difference.

### 2.4 September 4 littleX matrix

Historical W1 feed server p50 milliseconds:

| Tweets per user tier | PostgreSQL | SQLAlchemy | Neo4j | Jac CONTROL | Jac BEST |
|---|---:|---:|---:|---:|---:|
| t20 | 4.14 | 9.84 | 26.95 | 12.99 | 16.44 |
| t50 | 10.64 | 24.35 | 67.25 | 22.60 | 23.39 |
| t100 | 21.10 | 50.85 | 137.26 | 41.92 | 43.11 |
| t200 | 42.39 | 122.20 | 282.67 | 84.14 | 85.49 |

The tier label is **tweets per user**, with 100 users and 50 follows per user held fixed. `t50` uses the generator's `uniform` profile. Thus total follows are5,000 in every tier; tweets vary as follows:

| Tier | Users | Follows/user | Total tweets | W1 full-feed tweets/user |
| --- | --- | --- | --- | --- |
| t20 |100|50|2,000|1,000|
| t50 |100|50|5,000|2,500|
| t100 |100|50|10,000|5,000|
| t200 |100|50|20,000|10,000|

Each full feed contains the tweets of the50 followed users. Source: [original generator](../DBHarness/dataset/generate.py:20), and `littlex/run.py` maps`t50`to`uniform`.

Historical W2 exercises create_tweet/follow/like at all four tiers. W3 exercises feed_page and writes at tier200 across write fractions. Every mutating cell uses fresh seeded state and its own operation-count oracle. Historical W2/W3 oracles pass across the recorded arms. Full per-operation numbers, client timing and fraction breakdown are in `../DBHarness/session0904/run/AB_TABLE.md`; raw masters are:

- `../DBHarness/session0904/run/data/littlex_baselines/{w1,w2,w3}_master.csv`
- `../DBHarness/session0904/run/data/littlex_control/{w1,w2,w3}_master.csv`
- `../DBHarness/session0904/run/data/littlex_best/{w1,w2,w3}_master.csv`
- Per-cell correctness: each directory's `oracle_summary.csv` and associated raw artifacts.

Historical conclusions include scaling with tweets per user at fixed follow count, substantial Neo4j feed cost for this implementation, and workload-specific write/CONTROL/BEST differences. The recorded cross-date littleX write regressions compare both different application text and runtime revisions. Reproducing their cause requires the corresponding controlled A/B.

## 3. Reproduction environment and topology

Host inventory: `environment.json`. CPU: Intel Core i9-10900K,10 physical cores/20 logical CPUs; Linux6.8.0-65-generic. Readback of all 20 CPU governor files on 2026-10-19 reports **powersave**; the historical run summary reports **performance**. This is a configuration difference, recorded without changing the host. Evidence: [governor observation](runtime/cpu-governor-observation.json).

### Runtime

Final measured-run interpreter: CPython 3.14.6, PBS 20260610, Clang22.1.3, PGO/LTO/BOLT, matching the Jac launcher's payload archive. Isolated environment: `runtime/venv314`; build configuration and package inventory: `runtime/python314-info.json`, `runtime/python314-packages.txt`. Archive SHA256: `160d3875b56d0d45ae0b3f40c9b821d0bb23d829af0a245193f2127251c9dab4`.

Source-mode wrappers select final/baseline Jac source explicitly and isolate compiler caches. They use the pinned interpreter and content caches instead of the historical sealed launcher/precompiled JIR. Both variants require warm startup and requests. The initial setup environment used Python 3.12.11; its pilot timing has separate provenance.

### Dependency provenance

The tracked shared benchmark lock resolves SQLAlchemy 2.0.51. The original September 4 runner starts all SNB/TPC-C SQL and ORM servers using `benchmark/.venv/bin/uvicorn` (`../DBHarness/session0904/final_runner.sh`, lines488/502/534/535/541), identifying the environment associated with that lock. Its last recorded lock change is commit `20e019f` on 2026-08-10.

| Package | Historical benchmark lock | Pilot baseline inventory | Primary locked baseline |
| --- | --- | --- | --- |
| sqlalchemy | 2.0.51 | 2.1.5 | 2.0.51 |
| greenlet | 3.5.5 | 3.5.6 | 3.5.5 |
| psycopg | 3.3.4 | 3.3.6 | 3.3.4 |
| psycopg-binary | 3.3.4 | 3.3.6 | 3.3.4 |
| psycopg-pool | 3.3.1 | 3.3.3 | 3.3.1 |
| fastapi | 0.141.1 | 0.115.11 | 0.141.1 |
| starlette | 1.6.0 | 0.46.2 | 1.6.0 |
| pydantic | 2.13.4 | 2.14.1 | 2.13.4 |
| pydantic-core | 2.46.4 | 2.50.1 | 2.46.4 |
| uvicorn | 0.52.1 | 0.34.0 | 0.52.1 |
| pyjwt | 2.13.0 | 2.10.1 | 2.13.0 |
| neo4j | 6.2.0 | 5.28.8 | 6.2.0 |

Sources: [historical benchmark lock](../DBHarness/benchmark/uv.lock), [historical dependency declarations](../DBHarness/benchmark/pyproject.toml), [reproduction inventory](runtime/python314-packages.txt), [static dependency audit](runtime/historical-dependency-audit.json).

The lock establishes resolved dependency versions; an installed-package snapshot from the historical execution would establish the packages actually imported. The inspected tracked files provide the lock and launcher paths, while historical freeze/dist-info metadata remains unavailable. The separate `littleXs/sqlalchemy/uv.lock` also resolves SQLAlchemy 2.0.51 but has different FastAPI/Starlette/Uvicorn versions; it belongs to a different project environment. The historical shared-benchmark Python major/minor is not recorded in the inspected boot/reset logs or tracked project metadata. Its `requires-python>=3.12` constraint does not identify the execution interpreter; the build log’s Python 3.14 refers to Jac’s embedded payload. Current locked baseline Python 3.14 matches our Jac interpreter choice, while the historical shared-benchmark interpreter remains unspecified.

The primary SQL/ORM/Neo4j HTTP baseline results now use `runtime/venv-benchmark-locked`: all 28 registry distributions exactly match that benchmark lock and its archive hashes, with the same pinnedPBS3.14 interpreter. The original dependency-unmatched pilot results remain archived. Package equality, interpreter configuration and pip-check evidence are recorded in [locked environment provenance](runtime/benchmark-lock-provenance.json), [locked package freeze](runtime/benchmark-locked-packages.txt), and [locked Python information](runtime/benchmark-locked-pythoninfo.json). The completed serial rerun is [locked stage progress](results/locked-stage-progress.json). This rerun changes the baseline dependency stack as a whole; individual package effects require separate controlled comparisons.

### Jac and baseline HTTP stacks

Jac serves these walker requests through its own stdlib-asyncio HTTP server, routing/model/serialization code, HS256 authentication and connection pool. Its measured request path uses external `psycopg`/`psycopg-binary`3.3.6; FastAPI, Uvicorn, Pydantic, PyJWT and `psycopg_pool` are outside that path. SQL and ORM baseline servers use those external web/auth/pool packages. Their locked package versions therefore describe the baseline stack, while Jac keeps its own stack and psycopg3.3.6. Source and mapped-native-library evidence: [HTTP/request dependency audit](runtime/HTTP_STACK.md). The compared Jac revisions have unchanged HTTP/auth/driver source in the audited paths.

### Services

| Component | Address / storage | Role |
|---|---|---|
| Jac SNB HTTP | 127.0.0.1:18109 | Baseline/final source A/B |
| Jac TPC-C HTTP | 127.0.0.1:18108 | Dedicated W1 application |
| Jac PostgreSQL 18.6 | Unix socket `/tmp/jacpg-d6275e76eb`, `dbcache/pg/main` | Dedicated per-project Jac databases |
| Hand SQL PostgreSQL 16 | 127.0.0.1:55436 | Dedicated relational SNB/TPC-C databases |
| Hand SQL SNB HTTP | 127.0.0.1:18111 | Original SQL handlers |
| Hand SQL TPC-C HTTP | 127.0.0.1:18112 | Original SQL handlers |
| Neo4j5 | HTTP17474 / Bolt17687 | Loaded canonical graph baseline; completed pilot and locked HTTP-driver runs |

Exact commands, PIDs and Jac environment are saved in `logs/*-launch.json`; configuration code is `scripts/manage.py`. SQLAlchemy uses SNB HTTP18113 andTPC-C HTTP18115; Neo4j HTTP app18114. Their original handler implementations use the selected locked interpreter. Neo4j compose is `optional-baselines/compose.yml`.

Measured latest-runtime Jac cells are labeled **Final defaults**. The manager unsets`JAC_LAZY_TXN`; in final`32c5d1dbb`and IC5 baseline`c12ba889d`, the language runtime interprets an unset value as **on**. In historical broad-matrix`ad469c988`, unset means **off**, corresponding to its CONTROL setting; historical BEST enables lazy transactions. Final defaults therefore differs from historical CONTROL in both revision and effective configuration. The IC5 baseline/final source A/B shares lazy-default-on behavior in both revisions. Edge-only-dirty is already default-on for PostgreSQL in`ad469c988`: its predicate is`_EDGE_ONLY_DIRTY_ENV != '0' and _edge_only_dirty_pg()`. Final32 uses the PostgreSQL default directly. Consequently, unset edge-only-dirty is not an off→on difference between these runs; the lazy-transaction default is the relevant CONTROL/default distinction.

Current configuration also explicitly selects psycopg, the Jac-owned pool, ensure cache, promoted predicates, CTE traversal, sticky deny, timing headers and lean responses. Effective values depend on source revision as well as environment strings; an absent environment variable does not imply an off switch. Source: [current lazy-transaction default](../jac-db/jac/jaclang/runtimelib/impl/context.impl.jac:11); read-only`git show c12ba889d:jac/jaclang/runtimelib/impl/context.impl.jac`and`git show ad469c988:jac/jaclang/runtimelib/impl/context.impl.jac`establish the historical difference. Historical CONTROL comparisons in this report are explicit cross-version/configuration references. A flag-by-flag source review is recorded in [littleX environment review](littlex/ENV_REVIEW.md).

SNB mirror/index provisioning and schema readiness evidence: `logs/provision-runtime-*.json`, `logs/vacuum-snb.log`, `logs/autovacuum-state-restored.json`, and `runtime/MIRROR_WARMUP.md`. A warm request can create persistent physical structures; final performance gates require completed provisioning and zero structural SQL during the measured phase.

### Data and initialization

- Official SNB SF1 CsvBasic LongDateFormatter snapshot and original substitution parameters: `data/manifest.json` contains source URLs, SHA256,35 CSV file row counts and all 14 Interactive parameter headers. Input snapshot archive230,446,796 bytes; SHA256`3c34eca7f8e8632d5f3bf95921d3adc9cf0dce080acd6a94e3d2624ab704eb63`.
- TPC-C W1 generator seed 42 and fixed2026-01-01 epoch: `benchmark/tpcc/data/manifest.json`. Seven JSONL files are byte-identical across two independent generations.
- Jac TPC-C seeding uses the original HTTP `seed.py`; elapsed 456 seconds. Its customer seeder also creates the initial30,000 History nodes. Initial count evidence: `results/tpcc-seed-counts.json`, log`logs/jac-tpcc-seed.log`.
- Relational data loads and Jac full load are logged separately under `logs/load-*.log` and `logs/jac-full-load.log`.

## 4. Statistical and correctness definitions

1. **Canonical result hash:** SHA256 of `json.dumps(result, sort_keys=True).encode()`, matching the historical driver. The compared object contains the normalized reported result fields extracted by the driver; HTTP response envelopes and serialized wire bytes are outside this equality check. Compare every selected parameter key against both live hand SQL and the tracked PostgreSQL hashes. Use all seven query classes and first 20 official parameter rows.
2. **Conventional median:** for evenN, mean of the two middle sorted values (`statistics.median`). **Historical banked p50:** upper-middle order statistic `sorted(values)[int(N*0.5)]`. Retain both when comparing small 20-row IC5 samples.
3. **Latency ratio:** median Jac / median paired PostgreSQL; identify whether client or server time is used. This is distinct from the median of individual request ratios.
4. **Client time:** HTTP request wall time. **Server time:** original timing headers; Jac commit duration is added when separately reported, as in original `issue_snb`. littleX historical headlines use server time; SNB/TPC-C historical headlines use client time.
5. **SQL census:** use `scripts/db_settings.py census` to change cluster logging and reload without restarting warmed apps; isolate each Jac request's log interval. Count PostgreSQL `LOG: execute` and `LOG: statement` lines using the harness's original definition. Store per-request and total counts. Disable logging for latency-only runs.
6. **Structural SQL:** separately track CREATE/ALTER/DROP and mirror-population statements. Complete provisioning before final timing; census artifacts retain any observed structural activity.
7. **Warmup:** SNB uses the same complete request-shape pass per arm. TPC-C's100 warm entries mutate state and are included in truth-oracle deltas but excluded from timed CSV. Each write cell starts from a fresh load.
8. **TPC-C truth oracle:** compare before/after orders, order_line, new_order, history, sum(d_next_o_id), warehouse YTD, and per-district `next_o_id=max(order_id)+1`. Expected deltas for 900-plan entries are487,4746,487,406,487 and 1,062,049.86 respectively; consistency violations0. Record errors and expected rollbacks separately.
9. **Causal explanation:** support a claimed mechanism with measured SQL work, query plans/buffers, database statement durations or CPU profiles from the same revision/configuration. The report records unexplained timing differences as observations until that evidence is collected.

## 5. Completed reproduction evidence

### Initial SNB correctness and IC5 work count

`results/final-initial-parity/summary.json`, `rows.json`, `hashes.json`, and `pg-hashes.json` record140/140 historical hash matches and 140/140 live Jac/SQL parity. IC5 total is **432 statements**, matching final historical D5 exactly. This setup-stage census also observed 9 structural SQL events on IS2; this prompted the later explicit provisioning/warmup work.

These initial pilot times came from the setup environment and earlier relational setup. Final tables below are populated from the pinned 3.14 interpreter, PostgreSQL 16 baseline, completed provisioning, and dedicated measurement windows.

### TPC-C PostgreSQL 16

Completed: `results/tpcc-postgres16/tpcc_postgres.csv`, `.warm.csv`, `.meta.json`, and `.oracle.json`. All7 truth checks pass,100 warm+800 timed rows complete, zero request errors,7 expected rollbacks across the full plan. Final counts exactly match the historical metadata. Plan SHA256`769147b46ac2a157a378e061089b7f8e043d5f261c361aebbe9ce9a196cf8501`.

`results/tpcc-postgres/` retains the earlier PostgreSQL 18 pilot. Keep database versions distinct when selecting final results.

### Completed collection and retained state

Baseline IC5 census has completed:20/20 live parity,20/20 historical hashes,**278,769 statements** and**0 structural SQL**. Evidence: `results/baseline-census/{rows.json,summary.json,hashes.json}`, `logs/gate-baseline-census.log`. Census latency is recorded with logging enabled; formal latency comes from the separate logging-off stage.

The SNB matrix has completed baseline/final census, paired latency and profiles. Original canonical schedules are complete for Jac, locked PostgreSQL, locked SQLAlchemy and locked Neo4j:140 warm +2,550 timed requests per arm and 140 matching hashes each. Jac, locked PostgreSQL and locked SQLAlchemy each pass the golden 900-entryTPC-C plan and all seven truth checks. Stage manifests: `results/snb-stage-progress.json`, `results/remaining-stage-progress.json`, `results/locked-stage-progress.json`. The original-recipe historical littleX matrix, commit-floor probe and controlled write/readiness/statistics diagnostics are complete. Root has stopped owned benchmark API services; databases and snapshots are retained. Final logging/durability settings are recorded in [final-state.json](logs/final-state.json).

Independent offline verification of completed core artifacts: [core-artifact-validation.json](results/core-artifact-validation.json). The verifier checks both IC5 revisions, all four canonical SNB arms and all three golden-plan TPC-C arms from raw CSV/JSON. Entry point: `runtime/venv314/bin/python scripts/verify_core_artifacts.py`.

## 6. Final reproduced results

The marked sections below are reserved for completed measured artifacts. Each row includes its schedule, sample counts, correctness and raw artifact path. Versions/topology are specified above; IC5 final, SNB and TPC-C Jac rows use `32c5d1dbb`, pinned CPython 3.14.6 and Jac PostgreSQL 18.6. littleX primary rows use historical `ad469c988` CONTROL; their additional fresh-state group uses final32 defaults. SNB/TPC-C non-Jac baselines use the exact shared benchmark dependency lock with the same3.14 interpreter; their SQL/ORM stores use PostgreSQL 16. littleX SQL and driver environments instead use their separate original locks on Python 3.13.16. Earlier paired-request IC5 comparisons retain their original baseline environment and are labeled separately. Refresh only marked blocks with `runtime/venv314/bin/python scripts/update_report_tables.py`.

<!-- BEGIN FINAL_IC5_RESULTS -->
Logging-off paired-request latency; conventional medians. Census is a separate 20-request logging-on run.

| Revision | Latency N | Jac ms | Paired SQL ms | Jac / SQL | Census SQL total | Structural SQL | Latency parity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 40 | 6506.320 | 45.425 | 143.231× | 278,769 | 0 | 40/40 |
| final | 60 | 110.206 | 57.266 | 1.924× | 432 | 0 | 60/60 |

The baseline / final Jac median ratio is **59.04×** in these runs. Census totals exactly reproduce the historical **278,769 → 432** reduction.

Final per-row statement counts match 18/20 historical rows. Differences (zero-based idx, historical, reproduced, delta): `[(3, 27, 28, 1), (13, 24, 23, -1)]`. Retained SQL windows show the current idx 3 count 28 consists of one schema-existence guard plus 27 other statements. The guard explains that request’s +1. A controlled same-input probe observed 29/27/29 after an immediate repeat and a 5.5-second delay; schema guard and identity lookup counts 1/0/1 each account for the two-statement variation, with 27 other statements constant. Historical idx 13’s extra statement remains unclassified because its original SQL window is unavailable. Evidence: [census SQL classification](results/final-census/sql-windows/classification.json), [probe summary](results/ic5-ttl-probe/summary.json), [probe SQL classification](results/ic5-ttl-probe/classification.json).

Evidence: [results/baseline-census/summary.json](results/baseline-census/summary.json), [results/baseline-latency/summary.json](results/baseline-latency/summary.json), [results/final-census/summary.json](results/final-census/summary.json), [results/final-latency/summary.json](results/final-latency/summary.json).
<!-- END FINAL_IC5_RESULTS -->

<!-- BEGIN FINAL_SNB_RESULTS -->
Earlier paired rounds (60 requests/query) used the initial SQL baseline environment. Their results remain in [results/final-latency/summary.json](results/final-latency/summary.json). The canonical table below is the primary full-schedule comparison.

**Primary baselines: original benchmark dependency lock.** Jac retains its original final-runtime result. Each arm completed 140 warm +2,550 timed requests, serially. Historical upper-middle client p50 is shown; all 140 result hashes per arm match the tracked SQL reference.

| Query | N / arm | Jac Final defaults client ms | SQL client ms | ORM client ms | Neo4j client ms | Jac / SQL |
| --- | --- | --- | --- | --- | --- | --- |
| is 1 | 750 | 2.407 | 0.881 | 1.324 | 1.432 | 2.732× |
| is 2 | 750 | 4.859 | 10.463 | 9.164 | 2.117 | 0.464× |
| is 3 | 750 | 3.505 | 1.465 | 2.004 | 1.541 | 2.392× |
| ic1 | 75 | 5.319 | 34.638 | 88.055 | 8.913 | 0.154× |
| ic2 | 75 | 9.842 | 33.852 | 35.037 | 20.877 | 0.291× |
| ic5 | 75 | 109.032 | 54.462 | 45.914 | 17.250 | 2.002× |
| ic13 | 75 | 34.653 | 28.365 | 43.958 | 1.401 | 1.222× |

Raw timing: [results/snb-canonical/jac/snb_jaseci-pg.csv](results/snb-canonical/jac/snb_jaseci-pg.csv), [results/locked/snb-canonical/postgres/snb_postgres.csv](results/locked/snb-canonical/postgres/snb_postgres.csv), [results/locked/snb-canonical/sqlalchemy/snb_sqlalchemy.csv](results/locked/snb-canonical/sqlalchemy/snb_sqlalchemy.csv), [results/locked/snb-canonical/neo4j/snb_neo4j.csv](results/locked/snb-canonical/neo4j/snb_neo4j.csv). Sibling `.meta.json`/`.hashes.json` files establish complete schedules, zero errors and 140 matching hashes. Raw CSV also retains server time.

The earlier dependency-unmatched baseline runs remain under `results/snb-canonical/{postgres,sqlalchemy,neo4j}/`. The failed first locked PostgreSQL attempt is retained at `results/locked/snb-canonical/postgres-startup-race/`; the table uses the completed replacement at `results/locked/snb-canonical/postgres/`.
<!-- END FINAL_SNB_RESULTS -->

<!-- BEGIN FINAL_TPCC_RESULTS -->
**Primary baselines: original benchmark dependency lock.** Jac retains the original final-runtime run. Each arm starts from freshly loaded state and executes the original 100 warm + 800 timed plan. Upper-middle p50 matches the historical statistic; New-Order client timing includes six expected timed rollbacks.

| Arm | Operation | Timed N | Client p50 ms | Server p50 ms | Truth checks | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| PostgreSQL 16 | new_order | 443 | 7.099 | 6.353 | 7/7 | 0 |
| PostgreSQL 16 | payment | 357 | 3.070 | 2.345 | 7/7 | 0 |
| Jac Final defaults | new_order | 443 | 10.418 | 9.331 | 7/7 | 0 |
| Jac Final defaults | payment | 357 | 6.496 | 5.440 | 7/7 | 0 |
| SQLAlchemy | new_order | 443 | 17.437 | 16.660 | 7/7 | 0 |
| SQLAlchemy | payment | 357 | 5.093 | 4.348 | 7/7 | 0 |

All three arms reproduce the golden 900-entry plan: 487 successful New-Order, 406 Payment, 7 rollbacks; final orders 30,487, order_line 305,500, new_order 9,487, history 30,406, next_o_sum 30,497, YTD 1,362,049.86, consistency violations 0.

New-Order places Jac between hand SQL and SQLAlchemy. Payment is slower on Jac than SQLAlchemy (6.496 vs 5.093 ms, 27.5% relative difference). Historical CONTROL Payment was 10.82 vs 10.66 ms. Dependency-aligned results support the present ordering; cross-date changes also include runtime, database and host configuration differences.

Evidence: [results/locked/tpcc-postgres/tpcc_postgres.oracle.json](results/locked/tpcc-postgres/tpcc_postgres.oracle.json), [results/tpcc-jac/tpcc_jaseci-pg.oracle.json](results/tpcc-jac/tpcc_jaseci-pg.oracle.json), [results/locked/tpcc-sqlalchemy/tpcc_sqlalchemy.oracle.json](results/locked/tpcc-sqlalchemy/tpcc_sqlalchemy.oracle.json). Sibling CSV/meta files retain request timing and schedule. Earlier baseline artifacts are retained in `results/tpcc-postgres16/` and `results/tpcc-sqlalchemy/`; the PostgreSQL 18 setup pilot remains in `results/tpcc-postgres/`.
<!-- END FINAL_TPCC_RESULTS -->

### Separate request diagnostics

<!-- BEGIN FINAL_PROFILE_RESULTS -->
These are separate **duration-logging-on diagnostic runs** for heavy IC5 parameter row 19. Latency conclusions use the logging-off tables above.

Baseline repeat 0: client wall 28733.448 ms; application CPU 6360.000 ms; PostgreSQL Bind 17486.072 ms and Execute 3069.384 ms over 45,426 executions. The complete protocol sum is 20555.456 ms.

Final full-profile medians across five repetitions:

| Measurement | Median ms |
| --- | --- |
| Client wall | 210.334 |
| Server wall | 208.448 |
| Application process CPU | 90.000 |
| Database Bind wall | 5.470 |
| Database Execute wall | 101.816 |
| Complete logged protocol wall | 107.554 |
| Tracked backend CPU | 120.000 |

CPU and protocol wall time are different measurements and are not additive partitions. Application CPU comes from server-process user/system ticks; backend CPU covers discovered existing client backends. The client-minus-protocol residual includes application/driver/transport work and does not identify network time. The data supports a reduction in SQL execution count and substantial measured Bind processing in the baseline.

Evidence: [results/baseline-profile/protocol-offline-00.json](results/baseline-profile/protocol-offline-00.json), [results/baseline-profile/profile.json](results/baseline-profile/profile.json), [results/final-full-profile/profile.json](results/final-full-profile/profile.json). Raw `postgres-00.log` etc. preserve protocol duration events; `/proc` CPU deltas have 10 ms resolution.
<!-- END FINAL_PROFILE_RESULTS -->

<!-- BEGIN FINAL_LITTLEX_RESULTS -->
**Primary littleX group: historical ad469c988 CONTROL, original process/cohort recipe.** Run 20261019T193716Z completes 40/40 cells and 24,000 timed raw requests, with zero request/warmup errors. Each W1/W2 operation has 110 warm +500 timed requests; each W3 fraction has 110 warm +1,000 timed requests.

One SQL server process persists across all 12 SQL cohorts. Jac uses 12 separate cohort processes. Within each W2 tier, like→follow→create_tweet shares its process and accumulating database state; each operation has its own 110-request warmup. SQL phase order is W2→W3→W1; Jac order is W3→W1→W2. SQL server affinity is 6–13, Jac/driver affinity0–19. SQL app and HTTP driver use their separate original locks on Python 3.13.16; Jac uses the historical source with the pinned 3.14 interpreter. No extra feed probes precede the prescribed warmup; fixture full/page validation is followed by reset.

Server p50 milliseconds. Historical ratio is the recorded September 4 CONTROL/SQL ratio for the same tier/fraction/operation.

| Phase | Tweets/user tier | Write % | Operation | Historical-source CONTROL ms | SQL ms | Current ratio | Historical ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W1 | t20 |  | feed | 14.954 | 5.417 | 2.76× | 3.14× |
| W1 | t50 |  | feed | 27.263 | 13.249 | 2.06× | 2.12× |
| W1 | t100 |  | feed | 48.102 | 26.327 | 1.83× | 1.99× |
| W1 | t200 |  | feed | 106.018 | 52.708 | 2.01× | 1.98× |
| W2 | t20 |  | like | 2.690 | 1.291 | 2.08× | 0.86× |
| W2 | t20 |  | follow | 3.349 | 1.375 | 2.44× | 0.92× |
| W2 | t20 |  | create_tweet | 2.598 | 1.322 | 1.97× | 0.87× |
| W2 | t50 |  | like | 2.701 | 1.390 | 1.94× | 1.59× |
| W2 | t50 |  | follow | 3.479 | 1.378 | 2.52× | 1.69× |
| W2 | t50 |  | create_tweet | 2.532 | 1.441 | 1.76× | 1.58× |
| W2 | t100 |  | like | 2.687 | 1.393 | 1.93× | 1.18× |
| W2 | t100 |  | follow | 3.467 | 1.327 | 2.61× | 1.28× |
| W2 | t100 |  | create_tweet | 2.560 | 1.394 | 1.84× | 1.18× |
| W2 | t200 |  | like | 2.728 | 1.388 | 1.97× | 1.53× |
| W2 | t200 |  | follow | 3.575 | 1.382 | 2.59× | 1.64× |
| W2 | t200 |  | create_tweet | 2.562 | 1.433 | 1.79× | 1.20× |
| W3 | t200 | 0 | feed_page | 3.523 | 4.735 | 0.74× | 0.77× |
| W3 | t200 | 5 | feed_page | 3.581 | 4.737 | 0.76× | 0.74× |
| W3 | t200 | 5 | like | 3.152 | 1.840 | 1.71× | 1.49× |
| W3 | t200 | 5 | follow | 3.972 | 1.571 | 2.53× | 1.56× |
| W3 | t200 | 5 | create_tweet | 3.123 | 1.972 | 1.58× | 1.46× |
| W3 | t200 | 15 | feed_page | 3.503 | 4.747 | 0.74× | 0.75× |
| W3 | t200 | 15 | like | 2.802 | 1.500 | 1.87× | 1.56× |
| W3 | t200 | 15 | follow | 3.695 | 1.566 | 2.36× | 1.65× |
| W3 | t200 | 15 | create_tweet | 2.766 | 1.510 | 1.83× | 1.55× |
| W3 | t200 | 30 | feed_page | 3.540 | 4.794 | 0.74× | 0.77× |
| W3 | t200 | 30 | like | 2.887 | 1.456 | 1.98× | 1.58× |
| W3 | t200 | 30 | follow | 3.682 | 1.523 | 2.42× | 1.68× |
| W3 | t200 | 30 | create_tweet | 2.747 | 1.474 | 1.86× | 1.57× |

Evidence: [littlex/original-recipe/20261019T193716Z/complete.json](littlex/original-recipe/20261019T193716Z/complete.json), [littlex/original-recipe/summary/validation.json](littlex/original-recipe/summary/validation.json), [results/littlex-original-independent-validation.json](results/littlex-original-independent-validation.json), [littlex/original-recipe/summary/comparison.csv](littlex/original-recipe/summary/comparison.csv). Every comparison row points to its cohort results/raw CSV. Independent checks cover operation order, shared PID/state, affinity snapshots, sample counts, dependency provenance,100-user parity logs and write-delta oracles.

**Additional group: final32 Final defaults with fresh state per cell.** All40 cells pass their recorded sample, seed/parity and write-count checks. This group restores/reloads independently per operation and uses different process/state boundaries from the historical-recipe primary group; their difference is not a runtime-only A/B. W1 example:

| Tweets/user tier | Final defaults ms | SQL ms | Ratio |
| --- | --- | --- | --- |
| t20 | 23.466 | 5.130 | 4.57× |
| t50 | 28.060 | 12.963 | 2.16× |
| t100 | 49.667 | 26.543 | 1.87× |
| t200 | 107.435 | 54.130 | 1.98× |

Full additional matrix: [littlex/summary/REPORT.md](littlex/summary/REPORT.md), [littlex/summary/comparison.csv](littlex/summary/comparison.csv), [littlex/summary/validation.json](littlex/summary/validation.json).

Both groups reproduce increasing W1 feed cost with tweets per user, and W3 feed_page remains faster on Jac than SQL. Current historical-source CONTROL/SQL write ratios differ from the recorded September 4 ratios. Commit-floor and write-path diagnostics below characterize current costs and the specific initialization/statistics gaps.
<!-- END FINAL_LITTLEX_RESULTS -->

<!-- BEGIN FINAL_WRITE_DIAGNOSTICS -->
### Controlled t20 feed gap: planner statistics

The unchanged continuous driver uses 110 round-robin warm requests and 100 timed requests. The first four controls use the same historical fixture; the final fresh fixture is measured before/after an ANALYZE-only intervention on a restored disposable database.

| Control | Server p50 ms |
| --- | --- |
| ad-control | 14.909 |
| ad-lazy1 | 15.14 |
| final-lazy0 | 15.056 |
| final-lazy1 | 15.296 |
| final-fresh-fixture | 23.527 |
| final-fresh-fixture + ANALYZE anchors | 15.312 |

The fresh fixture starts with `anchors` planner metadata reltuples−1/pages0. **Only `ANALYZE anchors`** changes this to9303/pages795 and reduces server median 23.527→15.312 ms, matching the15.296 ms final-runtime control on the historical fixture. This controlled intervention identifies missing planner statistics as the source of that additional-group t20 gap. Stored snapshots and formal result artifacts remain unchanged. The source×LAZY controls on the common fixture stay near 15 ms, rather than the23 ms fresh-fixture result.

Evidence: [littlex/continuous-controls/20261019T195630Z/complete.json](littlex/continuous-controls/20261019T195630Z/complete.json), [littlex/continuous-controls/20261019T200053Z/complete.json](littlex/continuous-controls/20261019T200053Z/complete.json), [littlex/continuous-controls/20261019T200053Z/final-fresh-fixture/analysis-intervention.json](littlex/continuous-controls/20261019T200053Z/final-fresh-fixture/analysis-intervention.json). Before/after EXPLAIN artifacts: `littlex/explain/20261019T200019Z/` and `20261019T200127Z/`.

### Early page-profile gap: projection retry readiness

The 10-warm diagnostic starts 0.321 seconds after a Tweet endpoint-projection lock-timeout refusal and finishes its tenth capture 1.256 seconds after it. The source schedules the first retry after 2 seconds; all captured calls therefore use the generic two-hop top-K SQL. The 110-warm capture starts 3.303 seconds after its refusal and uses global_topk. Continuous110-warm controls measure 3.630 ms on historical CONTROL and 3.780 ms on final32, consistent with the formal warmed3.5–3.8 ms page results. SQL text, timestamps and source conditions are recovered in [littlex/PAGE_BRANCH_RECEIPT.md](littlex/PAGE_BRANCH_RECEIPT.md). This explains the initialization-profile difference separately from the W1 statistics intervention.

### Logged INSERT + COMMIT and write-path work

| Cluster | Current INSERT+COMMIT ms | Current explicit COMMIT ms | Historical scratch total ms |
| --- | --- | --- | --- |
| pg16 | 1.240 | 1.097 | 6.3992 |
| native | 1.211 | 1.136 | 6.3395 |

The current probe uses an ordinary logged scratch table, one reused connection/cluster and 5 warm +40 timed transactions. Both clusters report fsync=on,synchronous_commit=on,wal_sync_method=fdatasync,checkpoint_timeout=5 min,max_wal_size=1 GB. The historical log records40 COMMIT-inclusive samples; its original scratch code/raw CSV is unavailable, so that timer boundary and warmup remain unspecified. The measurements establish a much lower present common commit-inclusive cost than the recorded6.3 ms reference; they do not assign the difference to a storage mechanism or identify the historical t20 ranking cause.

Evidence: [results/commit-floor/summary.json](results/commit-floor/summary.json), [results/commit-floor/pg16.summary.json](results/commit-floor/pg16.summary.json), [results/commit-floor/native.summary.json](results/commit-floor/native.summary.json), [runtime/COMMIT_FLOOR_METHOD.md](runtime/COMMIT_FLOOR_METHOD.md). Per-arm raw CSV and read-only host/storage metadata are retained beside the summaries.

| create_tweet diagnostic | Historical Jac CONTROL | Hand SQL |
| --- | --- | --- |
| Instrumented server p50 ms | 4.645 | 2.347 |
| Application CPU total /100 calls ms | 610.0 | 170.0 |
| Tracked backend CPU total /100 calls ms | 310.0 | 10.0 |
| Mean logged protocol wall /call ms | 3.617 | 0.259 |
| Mean logged execute events /call | 9 | 1 |

These 100-warm +100-profiled calls are instrumented diagnostics, separate from formal server medians 2.598/1.322 ms. Aggregate CPU totals reflect 10 ms tick resolution; wall times and CPU totals are not additive. Jac has additional measured application/backend/protocol work. The SQL app uses autocommit: implicit transaction completion has no separate COMMIT command, so a zero explicit-COMMIT log count is not a zero durability-cost measurement. Jac explicit COMMIT protocol median is 1.439 ms. Source evidence and timing-boundary details: [littlex/DIAGNOSTIC_REPORT.md](littlex/DIAGNOSTIC_REPORT.md).

### Historical t20 write ordering

The primary current CONTROL/SQL ratios for t20 create/follow/like are1.97/2.44/2.08; historical ratios were0.87/0.92/0.86. The original [../DBHarness/session0904/run/AB_TABLE.md](../DBHarness/session0904/run/AB_TABLE.md) itself marks t20 PostgreSQL writes34–36% slower than its banked night0823 reference: approximately8.9 ms at t20 versus 6.5–6.8 ms at the other tiers. [../DBHarness/night0823/FINDINGS.md](../DBHarness/night0823/FINDINGS.md) also records that proposed write-flag improvements did not reproduce in interleaved fresh-boot A/B. These are recorded historical variations, not a new causal measurement of that run. The present commit and write-work measurements characterize the current costs; the historical ranking reversal remains a documented comparison whose original cause is not identified.

All workloads and diagnostics are complete. Owned benchmark API servers are stopped and statement logging is off. Data, fixture snapshots, raw result groups, controlled interventions and failed/pilot artifacts are retained.

Final state: [logs/final-state.json](logs/final-state.json). Later diagnostic host observations are retained in `logs/littlex-host/`; these time series describe the sampled windows, while earlier runs retain their available launch/affinity/configuration artifacts.
<!-- END FINAL_WRITE_DIAGNOSTICS -->

## 7. Hard verification checklist

- [x] Preserve source revisions and unchanged SNB application hash.
- [x] Acquire official SF1 snapshot and substitution parameters with checksums.
- [x] Verify all 7 SNB queries ×20 rows against live SQL and historical 140 hashes in initial gate.
- [x] Reproduce final IC5 total 432 statements in initial gate.
- [x] Generate deterministic W1 data twice and verify byte identity.
- [x] Seed Jac W1 and verify all initial database counts.
- [x] Complete PostgreSQL 16W1 run and pass all 7 truth checks.
- [x] Finish baseline IC5 census: total 278,769,20/20 parity,20/20 historical hashes,structural SQL0.
- [x] Final IC5 census under pinned 3.14:432 total,20/20 parity,structural SQL0.
- [x] Logging-off baseline/final paired timing:40 baseline IC5 requests and 60 final requests per query.
- [x] Final seven-query paired and original canonical schedules complete;140 historical hashes agree.
- [x] Jac W1 fresh-state golden 900-entry plan: matching plan hash,all seven truth checks,seven expected rollbacks.
- [x] Label all measured final-runtime cells as Final defaults and distinguish historical source/configuration references; historical littleX CONTROL and Final defaults now have separate completed local result groups.
- [x] Complete historical littleX original-recipe40-cell matrix and the separate final-defaults fresh-state group, including all sample/count/parity oracles.
- [x] SQLAlchemy/Neo4j canonical schedules complete with original locked baseline dependencies and 140 matching hashes each.
- [x] Retain launch/configuration records, measured affinity snapshots and physical schema/readiness evidence; retain host CPU/load time series for the later diagnostic controls where sampled. Final-state checks confirm both clusters have logging off, no database logging overrides, and fsync/synchronous_commit on.
- [x] Collect protocol/application/backend CPU evidence for IC5 and exact SQL-window evidence for current census variation; cross-date causal claims remain tied to controlled comparisons.
- [x] Populate completed core/littleX tables from raw artifacts and retain run manifests.
- [x] Integrate completed commit-floor/write diagnostics and controlled statistics/readiness interventions; characterize the W2 t20 rank reversal with present measured costs and recorded historical variability.

## 8. Independent rerun entry points

Follow the command sequence in [README.md](README.md#independent-rerun-order). It separates data loading, offline canonical provisioning, process warmup, SQL census, logging-off latency and profiling. Current operations are recorded in [scripts/STATUS.md](scripts/STATUS.md).

Important warmup property: `PgStore.ensure_mirror` memoizes readiness **inside each process**. Restarting an HTTP process clears that memo and can rescan/backfill the full anchors table even if durable mirrors already exist. Offline provisioning establishes complete physical structures; a newly launched process still needs its own warmup and a structural-SQL readiness check. See [runtime/MIRROR_WARMUP.md](runtime/MIRROR_WARMUP.md).

## Follow-up W2 write investigation

Three new uninstrumented rounds reproduce the local t20 ordering across all 18 cells and 9,000 timed requests: PostgreSQL server medians are 1.309–1.411 ms; historical-source Jac CONTROL medians are 2.548–3.406 ms. A separate final-defaults cohort has 500 timed requests per operation, with medians 3.021 / 3.704 / 2.821 ms for like / follow / create_tweet.

The measured request paths explain where current extra work occurs. Jac executes approximately 10.96 / 12 / 9 SQL statements per like / follow / create request, versus one for the SQL implementation. Corrected driver spans show follow performs two traversals and three worker anchor loads, versus one traversal and one worker anchor load for create. Anchor loads request individual UUIDs; neighbor-ID traversal does not establish that every neighbor object is hydrated. Main-thread initialization also parses TOML twice per request, measured at 0.154–0.181 ms wall in the lighter configuration-span capture. Nested spans describe inclusive boundaries and must not be summed.

DML replay medians are only 0.099–0.134 ms for Jac and 0.036–0.081 ms for SQL, with no Jac trigger events and zero shared read blocks. Jac emits more WAL in these replays; the WAL measurements alone do not attribute the millisecond request gap. The baseline, protocol, CPU, driver and function records distinguish these costs. A matched 100-warm/100-measured control also quantifies instrumentation overhead; function-profile client medians are 2.45–2.66 times uninstrumented values.

The historical t20 arm summaries were collected about 44 minutes apart. Their original per-request raw files and commit/CPU profiles are unavailable in the archived checkout, so the original ranking's unique cause cannot be recovered from current profiles. Exact historical timing boundaries and source hashes are retained in the audit.

[Investigation report](write-investigation/REPORT.md), [historical and independent raw-data audit](write-investigation/HISTORICAL_AUDIT.md), [function and corrected SQL-category spans](littlex/WRITE_FUNCTION_SPANS.md), [cost figure (PNG)](write-investigation/write-costs.png), [cost figure (PDF)](write-investigation/write-costs.pdf).

The final follow-up spans contain 300 measured requests, the final-defaults cohort 1,500 timed requests, and matched instrumentation aggregates cover 2,100 samples. All six DML arm/operation combinations have three replay measurements. Collection is complete; ports 18120/18121 are closed, scratch databases removed, workload state restored, and logging/durability settings recorded in [follow-up final state](write-investigation/final-state.json).
