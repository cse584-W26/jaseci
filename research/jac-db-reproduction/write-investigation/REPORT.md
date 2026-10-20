# Why the reproduced littleX writes are slower in Jac

The t20 write gap is stable across three interleaved fresh-state repetitions. On this machine Jac performs substantially more request setup, anchor loading and traversal work than the hand-SQL service. The measured DML itself takes approximately0.1ms, and no trigger work executes in these captured write paths. The clearest operation-specific difference is follow's additional traversal work: approximately0.55ms more application-side traversal wall time than create. Repeated request configuration parsing contributes a further0.15–0.18ms per request.

![Measured write costs](/home/baichuan/jaseci/reproduction/write-investigation/write-costs.png)

[PDF figure](/home/baichuan/jaseci/reproduction/write-investigation/write-costs.pdf)

## Experimental recipe

The primary rerun uses historical runtime **ad469c9889dabcdf70bbf6cfc033c0f8a3d0399e** and recovered application SHA **89366720a196c275712ccda73c2db06b17ea509c645a87c87ef84e5409821df0**. Historical CONTROL exports STREAM_LATERAL/SQL_ACL/FUSED_FEED/STICKY_DENY=1, leaves LAZY_TXN and EDGE_ONLY_DIRTY unset, and sets RO_WALKERS empty. On this runtime LAZY defaults off and PG EDGE_ONLY_DIRTY defaults on.

The original seed has100users,20tweets/user,50follows/user. Each arm receives a fresh seed per cohort. Within the cohort, one server and database persist through **like→follow→create_tweet**. Every operation runs110warm requests followed by500timed requests, with the original driver/payload/TargetPlan and original delta oracle. All18cells and9000timed samples pass; each operation adds exactly610of its corresponding entity, and the post-operation database counts match cumulative cohort state.

The three arm orders are SQL→Jac, Jac→SQL, SQL→Jac. SQL runs under the original Python3.13 frozen lock with server CPUs6–13, PostgreSQL16/TCP on127.0.0.1:55436. Jac uses Python3.14, its native PostgreSQL18 Unix socket and the original unpinned server placement; both drivers are unpinned. Per-cell PIDs, actual affinity, reset provenance, state before/after and configuration are retained.

The original500-sample percentile rule is `sorted[round(q*(N-1))]`, so p50 selects index250. Independent recalculation verifies every baseline percentile from raw samples.

## Stable baseline

Values are server p50 / full client p50, in milliseconds.

| Round | Arm | Like | Follow | Create |
|---|---|---:|---:|---:|
|1|SQL|1.311 /1.894|1.346 /1.937|1.378 /1.988|
|1|Jac CONTROL|2.706 /4.103|3.406 /4.838|2.549 /3.990|
|2|Jac CONTROL|2.722 /4.119|3.395 /4.839|2.570 /3.995|
|2|SQL|1.407 /2.009|1.397 /1.969|1.411 /2.015|
|3|SQL|1.353 /1.903|1.309 /1.907|1.398 /1.994|
|3|Jac CONTROL|2.694 /4.098|3.373 /4.792|2.548 /3.961|

Jac's higher cost persists in full client latency, approximately4.1ms for like,4.8ms for follow and4.0ms for create, versus approximately1.9–2.0ms for SQL.

Server headline scopes differ: SQL starts its handler timer after the JWT dependency; Jac includes request identity/root setup inside its server span. The Jac server emits whole−commit−serialization and the original driver adds commit, yielding whole−serialization. Full client latency supplies the common outer observation. Client-minus-server statistics are calculated from paired raw observations, rather than subtracting independent medians.

A separate final32-defaults cohort on the **same historical seed fixture**, with the same110+500recipe, also passes:

| Operation | Final32 server p50 | Final32 client p50 |
|---|---:|---:|
|Like|3.021|3.986|
|Follow|3.704|4.680|
|Create|2.821|3.807|

The current runtime retains the same broad client-latency gap. Its different transaction/timing behavior makes full client latency particularly useful for this comparison.

## Instrumentation cost

A separate matched control uses100warm+100timed requests per operation, the same seed, operation order, shared cohort state and payload plan. All diagnostic groups use100warm+100measured calls. Stage/CPU and protocol helpers have **zero deliberate inter-request sleep**. The table recomputes conventional medians from each100-row raw sample set, consistently across groups.

Values below are full client medians, in milliseconds. Parentheses give the ratio to the matched uninstrumented control.

| Arm / operation | None | Stage+CPU, logging off | Stage+CPU+SQL duration | Function profiler+spans |
|---|---:|---:|---:|---:|
|SQL like|1.961|2.064(1.05×)|2.021(1.03×)|—|
|SQL follow|1.967|2.007(1.02×)|2.095(1.07×)|—|
|SQL create|2.015|2.040(1.01×)|2.028(1.01×)|—|
|Jac like|4.143|4.728(1.14×)|4.990(1.20×)|11.025(2.66×)|
|Jac follow|4.987|5.455(1.09×)|5.899(1.18×)|12.226(2.45×)|
|Jac create|4.014|4.527(1.13×)|4.987(1.24×)|10.542(2.63×)|

Function profiling has large overhead. Its call counts and call graph locate executed work; the lighter spans quantify wall/CPU costs. Protocol durations, application driver wall time, backend CPU and request CPU have different boundaries and are reported separately.

## Multiple SQL operations and driver work

Reconstructed complete protocol logs show approximately9executed statements per Jac create,12per follow and10.96per like, versus one SQL-service DML statement for each operation (UPDATE for like, INSERT for follow/create). The reconstruction includes multiline query bodies; classification uses full SQL rather than an empty first-line prefix.

Every Jac request has a main-thread BEGIN, SET and two anchor loads. Worker work then performs further loads, graph traversal, anchor persistence, a type-registry write and COMMIT. The following authoritative lightweight spans classify each `PgStore._run` call by its SQL text. Graph traversals containing graph_types subqueries remain classified as traversals.

Values are calls per request / mean application-side driver wall milliseconds. Each operation has100measured requests.

| Worker SQL category | Create | Follow | Like |
|---|---:|---:|---:|
|Anchor traversal|1 /0.451|2 /1.004|1 /0.456|
|Anchor load|1 /0.157|3 /0.373|2.96 /0.439|
|Anchor INSERT|1 /0.241|1 /0.186|1 /0.197|
|Type-registry INSERT|1 /0.094|1 /0.074|1 /0.087|
|COMMIT|1 /1.428|1 /1.384|1 /1.470|

Follow performs two traversals versus create's one and three worker anchor loads versus create's one. Traversal wall alone increases by **0.553ms**, with an additional0.068ms thread CPU. That directly measured difference accounts for a substantial portion of follow's higher cost. Driver wall includes waiting, conversion and SQL execution; these data do not isolate a network contribution.

The SQL service expresses like directly as an UPDATE, and follow/create as INSERT operations, with the applicable relational constraints/conflict behavior. Jac additionally resolves identities and graph anchors, traverses/checks graph relationships and persists the graph's representation. These executed operations explain concrete additional work rather than relying on a generic claim that graph storage is expensive.

## Request CPU and function-level evidence

The first lightweight cross-thread capture measures the complete Jac dispatch, including routing, request context/auth, argument decoding, walker, commit and response construction. CPU is measured separately on each thread using `time.thread_time`.

| Operation | Dispatch wall ms | Main CPU ms | Worker CPU ms | Combined CPU ms |
|---|---:|---:|---:|---:|
|Create|4.195|1.075|0.816|1.891|
|Follow|4.983|1.054|1.099|2.153|
|Like|4.234|1.024|0.875|1.899|

Main-thread work accounts for roughly half of the request's application CPU. Its Session.batch_get spans approximately0.49–0.51ms wall and0.36–0.37ms CPU per request. This includes loading/hydrating request graph objects; a walker-only profile misses it.

Function profiling identifies **two TOML parses per request**: Session initialization calls `promotions_for`, and lease construction calls `retention_days_for`; both call `_toml_section`, open jac.toml and invoke tomllib. A separate lightweight capture bounds their direct combined cost at **0.154–0.181ms wall /0.155–0.182ms CPU per request**. This is a recurring fixed cost, smaller than the full write gap. `get_config` itself is inexpensive in the captured profile; its cost should not be conflated with the repeated TOML reads.

The profiler also records208–209 archetype attribute assignments per request, including generated object initialization, Session/Store/context setup, response construction and dirty tracking. Those counts establish executed object-management work. The heavily instrumented0.2ms exclusive assignment CPU is a profiler measurement, rather than an uninstrumented latency component.

Profiles preserve separate main-dispatch, worker-walker and worker-aux lanes. Python3.14 requires transferring the global profiling slot at `asyncio.to_thread` boundaries; the successful capture pauses the main profiler while the worker owns that slot. The original failed instrumentation attempt is retained separately from successful results.

## DML, triggers and WAL

Captured DML was replayed on disposable databases cloned from matching fresh seeds. Each EXPLAIN uses ANALYZE, BUFFERS, WAL, SETTINGS and JSON, then rolls back. Each captured statement is measured three times; actual commits are outside this experiment. The clones were dropped afterward.

| Arm / operation | Median summed DML execution ms | Median WAL bytes |
|---|---:|---:|
|SQL create|0.063|273|
|SQL follow|0.081|255|
|SQL like|0.036|433|
|Jac create|0.134|2331|
|Jac follow|0.099|1303|
|Jac like|0.103|1197|

All captured Jac DML plans report **zero trigger executions**, and all replayed plans use zero shared-buffer reads. The native DML takes approximately0.1ms. Jac generates more WAL in these statements, but that observation does not establish WAL as the cause of the millisecond request gap. The measurements prioritize the additional loads, traversal, driver/request processing and fixed setup work above.

The SQL app's pool uses autocommit. Its implicit transaction completion has no separate COMMIT protocol record, whereas Jac explicitly executes COMMIT. An absence of standalone SQL COMMIT events is not a measurement of zero durability cost. The separate logged INSERT+COMMIT floor probe measured total medians1.240ms for SQL PG16/TCP and1.211ms for native PG18, compared with historical scratch medians6.399/6.340ms.

## What the historical comparison establishes

The original t20 SQL write medians are8.928/9.032/8.931ms for like/follow/create, versus Jac7.676/8.302/7.779ms. Original result timestamps are approximately**44minutes24seconds apart**; they are completion timestamps, not paired starts. The historical report marks those t20 SQL values as34–36% slower than its banked SQL baseline. Its earlier interleaved fresh-boot A/B also reports that the proposed write-flag advantage did not reproduce.

The new interleaved repetitions establish a stable current-machine Jac write disadvantage with unchanged historical runtime and application semantics. They identify the current additional work in detail. The historical raw request/protocol/host traces needed to uniquely identify the old t20 ranking reversal are unavailable in the inspected collection. The lower current commit floor is a measured cross-date difference; a common reduction alone cannot change the sign of the Jac-minus-SQL difference. The historical timing gap, differing commit floor and recorded SQL anomaly describe the evidence; assigning the reversal to a particular checkpoint, network or storage event would exceed it.

## Artifact index and cleanup

All paths below are absolute.

- [Independent historical and rerun audit](/home/baichuan/jaseci/reproduction/write-investigation/HISTORICAL_AUDIT.md)
- [Primary three-round raw results and per-cell provenance](/home/baichuan/jaseci/reproduction/littlex/w2-investigation/20261019T212400Z-baseline/complete.json)
- [Independent baseline recalculation:18cells,9000samples](/home/baichuan/jaseci/reproduction/write-investigation/rerun-baseline.json)
- [Matched none/stage/duration/function overhead](/home/baichuan/jaseci/reproduction/write-investigation/matched-overhead.json)
- [Complete SQL reconstruction/classification](/home/baichuan/jaseci/reproduction/write-investigation/sql-work-20261019T212529Z.json)
- [Function and lightweight span analysis](/home/baichuan/jaseci/reproduction/littlex/WRITE_FUNCTION_SPANS.md)
- [Successful function-profile metadata and adjacent pstats/call graphs](/home/baichuan/jaseci/reproduction/littlex/w2-investigation/20261019T212828Z-function/1-jaseci/functions/metadata.json)
- [Authoritative SQL-category spans](/home/baichuan/jaseci/reproduction/littlex/w2-investigation/20261019T213148Z-spans/1-jaseci/functions/sql-category-analysis.json)
- [DML replay aggregate](/home/baichuan/jaseci/reproduction/write-investigation/dml-summary.json) and [raw replay directory marker](/home/baichuan/jaseci/reproduction/write-investigation/dml-explain/20261019T212747Z/complete.json)
- [Final-defaults baseline cohort](/home/baichuan/jaseci/reproduction/littlex/w2-investigation/20261019T212804Z-final-baseline/complete.json)
- [Passive host observations summary](/home/baichuan/jaseci/reproduction/write-investigation/host-summary.json)
- [Final service/database state verification](/home/baichuan/jaseci/reproduction/write-investigation/final-state.json)

Final verification confirms HTTP18120/18121closed, no disposable DML databases, no owned per-database logging overrides, global statement logging disabled, and fsync/synchronous_commit enabled on both dedicated clusters. The native t20 project database was restored to its stored original seed. All earlier measurements, failed diagnostic attempts and successful retries remain available.
