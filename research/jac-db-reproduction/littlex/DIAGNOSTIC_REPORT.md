# littleX reproduction and measured explanations

The historical CONTROL recipe completed all 40 cells with zero request errors. The validator confirms the original phase order, one persistent SQL server, 12 Jac cohort servers, shared like→follow→create_tweet state within each W2 tier, 110 warm requests, and the original 500/1000 measured request counts. Jac uses ad469c988 and the recovered app SHA89366720; SQL and drivers use their original frozen Python3.13 locks. Results are in `original-recipe/summary/`.

## Conclusions against the historical measurements

- **W1 scaling reproduces.** CONTROL/SQL server-median ratios are2.76,2.06,1.83,2.01 at20/50/100/200 tweets per user; historical ratios are3.14,2.12,1.99,1.98. Both systems' uncapped feed cost grows with feed size.
- **W3 paged-feed advantage reproduces.** At0/5/15/30% writes, Jac page medians are3.523/3.581/3.503/3.540ms versus SQL4.735/4.737/4.747/4.794ms: ratios0.74–0.76, versus historical0.74–0.77.
- **W2's t20 historical ranking changes.** Current CONTROL/SQL ratios are1.97/2.44/2.08 for create/follow/like, versus historical0.87/0.92/0.86. Higher-tier writes remain slower in Jac. The original `session0904/run/AB_TABLE.md` itself flags t20 PostgreSQL writes as34–36% slower than the banked night0823 measurements; `night0823/FINDINGS.md` reports that fresh-boot interleaved A/B did not reproduce the proposed write-flag speedup. This historical variation and the current measured costs should accompany any write-performance claim.

## Why the final fresh-cell t20 feed was23ms

Continuous controls use the unchanged original driver,110 round-robin warm requests and100 continuous measured requests, without stage/SQL profiling or per-call sampling sleeps. On the same historical t20 fixture:

| Runtime | LAZY | Server median ms |
|---|---|---:|
|ad469 CONTROL|unset|14.909|
|ad469|1|15.140|
|final32|0|15.056|
|final32|1|15.296|
|final32, original final fresh fixture|1|23.527|
|final32, same fresh fixture after ANALYZE anchors|1|15.312|

Artifacts: `continuous-controls/20261019T195630Z` and `20261019T200053Z`.

The two fixtures have the same seed and SQL shape and identical index definitions. Before intervention, historical `anchors` has planner reltuples8735, while the final fresh fixture has reltuples−1/pages0. Relation bytes are identical. Captured custom-plan EXPLAIN executions take4.90–6.70ms on the historical fixture and13.17–15.10ms on the final fresh fixture; both use only shared-buffer hits and have no JIT section. Running **only ANALYZE anchors** on a restored disposable final database changes its estimate from−1 to9303 (pages0→795) and reduces continuous end-to-end server median23.527→15.312ms. This isolates missing planner statistics as the source of this gap. Stored snapshots and formal results remain unchanged.

Plans, buffer counts, planner settings, indexes and column statistics are in `explain/20261019T200019Z` and post-intervention `explain/20261019T200127Z`.

## Why the first page profile was much slower

The10-warm fixed-user profile captured a different SQL execution path from the warmed formal benchmark. Its server log records Tweet endpoint-column DDL failing on a lock timeout at19:53:25.099874Z. The measured calls ran0.321–1.256 seconds later. Source `_memo_refuse` schedules the first retry after2seconds, so all10 calls still use the generic two-hop top-K join. The dominant SELECT execute takes approximately27ms.

With110 round-robin warm requests, measurement begins3.303seconds after the same initial refusal, and the SQL changes to the global-top-K path. Continuous110-warm controls reproduce page medians3.630ms on historical CONTROL and3.780ms on final32, close to the formal3.5–3.8ms. The early profile measures initialization/retry behavior rather than the formal warmed path. Source conditions and timestamps are documented in `PROFILE_USER_SCOPE.md` and the runtime analysis notes.

## Write costs measured on this machine

The dedicated logged INSERT+COMMIT probe uses5warm+40timed samples per cluster. Total medians are1.240ms for PG16/TCP and1.211ms for nativePG18; explicit commit medians are1.097/1.136ms. Historical scratch medians were6.399/6.340ms. The original scratch source/raw samples were unavailable, so the current method is explicitly recorded in `results/commit-floor/summary.json` and `runtime/COMMIT_FLOOR_METHOD.md`.

Separate100-warm+100-profiled create_tweet diagnostics measure:

| Metric | Historical Jac CONTROL | Hand SQL |
|---|---:|---:|
|Server median ms|4.645|2.347|
|Aggregate app CPU ms/100calls|610|170|
|Aggregate observed client-backend CPU ms/100calls|310|10|
|Mean logged protocol wall ms/call|3.617|0.259|
|Mean logged execute events/call|9|1|

These are instrumented diagnostic timings, distinct from formal2.598/1.322ms medians. CPU tick resolution is10ms; aggregate totals are the useful comparison. The SQL app uses autocommit (`postgres/app.py:94`), so its implicit transaction completion is not logged as a separate COMMIT command: zero independent COMMIT events does **not** mean zero durability cost. Jac's explicit COMMIT protocol median is1.439ms. SQL's stage DB wall includes the implicit transaction completion; protocol records alone do not partition its full DB span.

The measurements establish additional Jac execution/CPU/protocol work on this host. The lower present commit-inclusive cost is a measured cross-date difference. It cannot by itself explain the historical t20 ranking reversal.

Artifacts: `results/littlex-diagnostics/20261019T195241Z/write-ad469-control`, `write-final-lazy1`, and `results/littlex-sql-write/20261019T200000Z`.

## Timing boundaries and observation scope

The server headline is whole request span minus serialization: the server emits whole−commit−ser, and the original driver adds commit. The stage build bucket includes serialization as a sub-timer. Therefore use **auth+prep+db+build+commit−ser ≈ server**, rather than adding ser again. Read-profile per-request residuals after this correction are at most0.021ms in the initial grid. Stage/SQL profiling has visible overhead and intermittent pauses; continuous original-driver controls establish the latency direction.

Passive host CPU/load/iowait and top-process observations during the later controls are retained in `logs/littlex-host/samples-20261019T195622Z.jsonl`. External processes were observed and left untouched. These records describe measurement conditions; no external-process cause is inferred.

The primary comparison is historical CONTROL versus hand SQL. The40-cell final-default fresh-state matrix is a separate comparison. The littleX SQLAlchemy/Neo4j arms and a full historical CONTROL-versus-BEST matrix have historical reference data; this reproduction establishes the Jac-versus-hand-SQL W1/W2/W3 conclusions above. The source×LAZY controls isolate that particular factor and do not substitute for the full BEST configuration.
