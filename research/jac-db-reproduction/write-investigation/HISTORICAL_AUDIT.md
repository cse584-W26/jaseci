# W2 write investigation: historical evidence and repeated baseline

## Exact historical target

Historical server p50 is Jac total-header plus separately reported commit, versus PostgreSQL total-header. The client measurement is separate. Original percentile is `sorted[round(q*(N-1))]`: index250 for500samples. No available evidence identifies a different headline definition for t20 versus t50/t100.

| Tier | Operation | PG server p50 | Jac server p50 | PG p95 | Jac p95 | Jac/PG | Completion gap seconds |
|---|---|---:|---:|---:|---:|---:|---:|
|t20|like|8.928|7.676|9.177|8.239|0.860|2664|
|t20|follow|9.032|8.302|9.355|9.046|0.919|2663|
|t20|create_tweet|8.931|7.779|9.433|8.362|0.871|2664|
|t50|like|6.555|10.390|6.843|11.014|1.585|2770|
|t50|follow|6.532|11.011|6.723|11.824|1.686|2774|
|t50|create_tweet|6.579|10.378|6.869|11.011|1.577|2777|
|t100|like|6.560|7.759|6.846|8.312|1.183|2934|
|t100|follow|6.565|8.428|6.766|9.106|1.284|2936|
|t100|create_tweet|6.606|7.801|6.877|8.373|1.181|2938|
|t200|like|6.597|10.122|6.872|10.897|1.534|3220|
|t200|follow|6.616|10.879|7.002|11.910|1.644|3224|
|t200|create_tweet|6.794|8.127|7.129|10.987|1.196|3227|

All24 arm/tier/operation summary rows have500 timed requests, zeroerrors and database-count delta610/610. Combined with the driver formula, this supports110 successful warm writes. Operations run like→follow→create_tweet after one tier reseed; the earlier writes remain present for later operations.

## Headline scope across arms

The header names do not establish identical start boundaries. In historical Jac `server.impl.jac`, `_run_function_with_occ` starts `_t0` **before** `_abegin_user_request_context`; it reports whole−commit−serialization, and the driver adds commit back. The effective headline is therefore whole−serialization and includes user-context setup inside that span. PostgreSQL handlers start`t0` inside the handler, after FastAPI's JWT dependency has completed; its response-model/HTTP serialization happens afterward. PostgreSQL's handler span includes the autocommit statement completion. Source confirms a boundary distinction across arms, while the same definitions apply at every tier. Historical per-stage samples are unavailable to quantify its contribution to September4t20. New stage/span measurements can quantify current contributions; they cannot backfill missing historical timing.

## Historical time/source/config facts

- UTC master timestamps are result completion/aggregation times, not exact request-start times. PGt20 finishes07:49:08–07:49:21Z; Jact20 finishes08:33:32–08:33:45Z. Matching operations finish approximately44min24s apart. Later tiers have still larger separations, listed above. Cohort reseed bounds are retained in `historical-w2.json`.
- PG t20 is the first PG W2cohort. Its8.928–9.032ms medians and9.177–9.433ms p95 values are elevated relative to PG t50/t1006.532–6.606ms medians. This is a distribution-level shift in recorded summaries, not a conclusion about its cause.
- Jac t50 also has higher recorded medians than Jac t20/t100. Data tier and execution time move together in these one-pass historical results; their individual effects cannot be separated by these summaries.
- Historical Jac source is ad469c988. Historical app SHA25689366720… is recovered from DBHarness `b94e08e^:littleXs/jaseci-pg/app.jac`. The later b94e08e commit at09:12EDT retires flags/unused app code after these runs. The recovered app matches the historical recipe; current HEAD app has a different hash.
- PG app SHA256 is recorded in `historical-w2.json`; its last source change is August21. It uses psycopg autocommit. Like normally executes one UPDATE, follow one INSERT ON CONFLICT, create_tweet one INSERT SELECT RETURNING. Autocommit transaction completion is not a separate SQL COMMIT event.
- Historical CONTROL: lazy transactions unset/off for ad469; PostgreSQL edge-only-dirty unset/on. Performance governor and launch-time low load/logging-off assertions are recorded in PROGRESS.log. They are not per-request CPU/protocol traces.
- Shared state is intentional: t20 starts2000tweets/5000follows/0likes, like adds610likes, follow adds610follows, create adds610tweets. No old row snapshots are retained to independently reconstruct every bound target. The610count oracles rule out the particular silent no-op interpretation for these successful PG/Jac rows.

## Available evidence and unknowns

Available: source, script semantics, original W2masters with p50/p95/p99/client/RPS/oracles; cohort logs; global launch/settings statements. Referenced original `harness/.run/night/w2_*.csv/.log` unit files and per-request samples were not found in this clone. The September4W2masters do not retain per-request commit, backend CPU, application CPU or stage distributions. Earlier night0823stage/CPU descriptions cover different runs/tier combinations; they cannot supply missing September4t20/t50/t100measurements.

Consequently no historical paired client-minus-server distribution, COMMIT distribution, CPU attribution or request-level SQL timeline can be reconstructed from those medians. A difference of client/server medians is not a paired residual. The old6.3ms scratch result is a separate measurement with an unrecovered loop/timer boundary. These are specific evidence gaps rather than an explanation named "noise".

## Fresh repeated baseline: independently recalculated

Three rounds, two arms, three operations;110warm+500timed per cell. All18cells/9000raw samples pass original percentile, PID/shared-state, affinity, sequence and count-oracle checks.

|Round|Operation|PG p50|Jac p50|PG p95|Jac p95|Jac/PG|
|---|---|---:|---:|---:|---:|---:|
|1|like|1.311|2.706|1.533|3.089|2.064|
|1|follow|1.346|3.406|1.570|3.822|2.530|
|1|create_tweet|1.378|2.549|1.652|2.857|1.850|
|2|like|1.407|2.722|1.632|2.998|1.935|
|2|follow|1.397|3.395|1.600|3.848|2.430|
|2|create_tweet|1.411|2.570|1.620|2.814|1.821|
|3|like|1.353|2.694|1.576|3.007|1.991|
|3|follow|1.309|3.373|1.513|3.720|2.577|
|3|create_tweet|1.398|2.548|2.265|2.830|1.823|

Per-cell mean/p99/min/max and paired client-minus-server p50/p95/p99 are retained in `rerun-baseline.json`/CSV. The paired residual includes serialization, transport and other work outside the headline; it is not attributed entirely to network.

## Stage and duration profiles: completed aggregates

All12cells/1200profiled requests pass oracle, row order and CPU-sum recomputation. Stage mode has SQL duration logging off; duration mode adds SQL logs. Each profile arm starts with a fresh cohort; like, follow and create_tweet then share one process and database state, with 100 warm and 100 measured calls per operation. Baseline cohorts use 110 warm and 500 timed calls per operation. Their difference is not a matched instrumentation-only overhead experiment.

|Mode|Arm|Operation|Server median|Server mean|Client median|App CPU total|Backend CPU total|Mean protocol wall|Mean SQL events|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
|stage|postgres|like|1.470|1.491|2.064|30|0|N/A|N/A|
|stage|postgres|follow|1.403|1.376|2.007|40|0|N/A|N/A|
|stage|postgres|create_tweet|1.429|1.431|2.040|40|10|N/A|N/A|
|stage|jaseci|like|3.199|3.214|4.728|190|90|N/A|N/A|
|stage|jaseci|follow|3.829|3.848|5.455|220|130|N/A|N/A|
|stage|jaseci|create_tweet|2.946|2.980|4.527|180|80|N/A|N/A|
|duration|postgres|like|1.392|1.388|2.021|40|0|0.04094|1|
|duration|postgres|follow|1.462|1.451|2.095|40|0|0.05292|1|
|duration|postgres|create_tweet|1.413|1.427|2.028|30|30|0.0591|1|
|duration|jaseci|like|3.291|7.439|4.990|250|140|5.94259|10.96|
|duration|jaseci|follow|4.187|4.168|5.899|230|170|2.638|12|
|duration|jaseci|create_tweet|3.235|3.258|4.987|200|100|2.12675|9|

CPU totals are aggregate milliseconds over100calls with10ms tick resolution. Wall time and CPU totals are not additive. Duration means and medians are both shown because outlying calls can materially change means. Stage buckets and paired residuals are retained in `profile-aggregates.json`; stage-mode unobserved protocol duration is N/A, not an actual zero.

Full multiline SQL reconstruction: `sql-work-20261019T212529Z.json`, generated by root`s `sql_work.py`, preserves fingerprint, category, protocol-phase counts and timings. SQL execution count is not a network-packet count. Function and span profiles are collected separately.

## DML execution and WAL: rollback-only replay

The captured DML statements were replayed three times with EXPLAIN in fresh-seed scratch databases, with each replay rolled back. These measurements exclude COMMIT, preceding reads, traversal, hydration, access checks and Python execution. Each table value is the median of three sums across the captured DML commands.

|Arm|Operation|DML execution (ms)|WAL bytes|Shared blocks read|Trigger events|
|---|---|---:|---:|---:|---:|
|jaseci|like|0.103|1197|0|0|
|jaseci|follow|0.099|1303|0|0|
|jaseci|create_tweet|0.134|2331|0|0|
|postgres|like|0.036|433|0|0|
|postgres|follow|0.081|255|0|2|
|postgres|create_tweet|0.063|273|0|1|

Jac generates more WAL in this replay, while its summed DML execution medians remain 0.099–0.134 ms. No Jac trigger events appear in these plans. These observations localize the remaining millisecond-scale gap to work beyond the measured DML bodies; attributing it requires the read, driver, hydration and dispatch profiles. WAL size alone does not measure its contribution to request latency. Raw repeat measurements and scope are preserved in `dml-summary.json`, with plans under `dml-explain/`.

## Matched instrumentation comparison

A separate uninstrumented cohort uses the same fresh-per-arm reset, shared operation order and 100 warm plus 100 measured requests per operation as the profiles. The table recomputes conventional medians from raw samples for every mode. Client elapsed time supplies the common boundary. Modes run sequentially in separate cohorts; the ratios describe observed overhead in these runs.

|Mode|Arm|Operation|Client median (ms)|Server median (ms)|Client / uninstrumented|
|---|---|---|---:|---:|---:|
|none|postgres|like|1.961|1.356|1.000|
|none|postgres|follow|1.966|1.395|1.000|
|none|postgres|create_tweet|2.015|1.389|1.000|
|none|jaseci|like|4.143|2.756|1.000|
|none|jaseci|follow|4.987|3.512|1.000|
|none|jaseci|create_tweet|4.014|2.588|1.000|
|stage|postgres|like|2.064|1.470|1.052|
|stage|postgres|follow|2.007|1.403|1.020|
|stage|postgres|create_tweet|2.040|1.429|1.012|
|stage|jaseci|like|4.728|3.199|1.141|
|stage|jaseci|follow|5.455|3.829|1.094|
|stage|jaseci|create_tweet|4.527|2.946|1.128|
|duration|postgres|like|2.021|1.392|1.031|
|duration|postgres|follow|2.095|1.462|1.065|
|duration|postgres|create_tweet|2.028|1.413|1.006|
|duration|jaseci|like|4.990|3.291|1.205|
|duration|jaseci|follow|5.899|4.187|1.183|
|duration|jaseci|create_tweet|4.987|3.235|1.243|
|function|jaseci|like|11.025|6.712|2.661|
|function|jaseci|follow|12.226|7.945|2.452|
|function|jaseci|create_tweet|10.542|6.072|2.627|

Function profiling raises observed Jac client medians to 2.45–2.66 times the matched uninstrumented values. Its function times describe the instrumented execution; baseline latency comes from the uninstrumented runs. The unsuccessful first function collector (`212632Z`) is excluded; the complete collector is `212828Z-function`. `compare_matched.py` exports all 2,100 samples as per-cell aggregate statistics to `matched-overhead.json`.

## Regeneration

`python write-investigation/audit_history.py` exports historical12pair/8cohort evidence. `python write-investigation/recalculate_rerun.py littlex/w2-investigation/20261019T212400Z-baseline` independently recomputes the completed repeated baseline. Neither issues database requests.
