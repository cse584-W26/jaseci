# WeBridge reproduction and Jac baseline alignment

## Complete eight-configuration comparison and measured SQL combination

Both requested experiments now cover all eight configurations, including actual set-oriented Java through WeBridge. The main timing matrix verifies960 responses, with240 additional reverse-order responses. The separate protocol experiment verifies30 measured profiles and maps each emitted query or stored-procedure operation.

Start with the [English PDF](roundtrip-comparison/jac-webridge-measured-comparison.pdf), [complete report](roundtrip-comparison/REPORT.md), and [independently verified matrix](roundtrip-comparison/eight-arm-verification.json). The earlier seven-configuration results below remain an earlier measurement cohort.

## Conventional Java SQL and complete latency sweep

A new Java baseline expresses IC5 using one set-oriented SQL query. It passes all twenty original inputs and the selected small nonempty input. Seven implementations now have a common 0/2/10 ms response-delay sweep, each with ten warmup and thirty measured requests. All840 request results pass independent verification.

| Implementation | 0 ms | +2 ms | +10 ms | Warm SQL commands |
|---|---:|---:|---:|---:|
| Jac original | 25.89 | 145.26 | 469.42 | 38 |
| Jac SQL pushdown | 5.73 | 39.53 | 160.23 | 14 |
| Java full | 28.75 | 120.74 | 463.64 | 38 |
| WeBridge full | 27.20 | 37.25 | 75.63 | 4 |
| Java pruned | 27.64 | 105.27 | 385.60 | 31 |
| WeBridge pruned | 25.62 | 33.70 | 69.23 | 4 |
| Java set-oriented SQL | 9.57 | 18.63 | 56.89 | 4 |

Times are medians in milliseconds. All settings use the same proxy path; actual persistent SELECT1 RTT is calibrated separately for each database. Jac uses PostgreSQL and its runtime-derived structures; Java/WeBridge uses MySQL. See [the full latency report](latency-comparison/REPORT.md), [verified data](latency-comparison/comparison.json) and [PDF chart](latency-comparison/comparison.pdf).

## Native Jac comparison on matched graph data

The native Jac baseline and SQL-pushdown implementation now run on a PostgreSQL copy of the same 460,984 anchors and 300,901 edges used by the Java/WeBridge experiment. The fixed small nonempty IC5 input and every returned result match. Each timing arm uses 10 warmup requests followed by 30 measured requests, with SQL duration logging disabled. SQL counts come from separate instrumented requests.

| System | Local median request execution (ms) | Warm database commands |
|---|---:|---:|
| Native Jac baseline | 22.2975 | 38 |
| Native Jac SQL pushdown | 4.5230 | 14 |
| Full-behavior Java baseline | 26.3263 | 38 |
| WeBridge full-behavior stored procedure | 26.7108 | 4 |
| Pruned Java baseline | 24.5277 | 31 |
| WeBridge pruned stored procedure | 25.0072 | 4 |

Jac improves **4.93x** within the same PostgreSQL service and fixture. The warm SQL trace contains a combined `WITH`/`GROUP BY`/`ORDER BY`/`LIMIT` query for the IC5 post-count operation. WeBridge executes the captured operations inside a stored procedure and reduces client commands to four; its local experiment retains the underlying table-access operations and shows approximately unchanged latency. Under the separately measured approximately 2.19 ms database RTT, WeBridge improves 3.34x (full behavior) and 2.96x (pruned).

Jac uses PostgreSQL 18.6 and its HTTP server; Java/WeBridge uses MySQL 5.7.44 and an in-process JDBC driver. The table compares complete implementations on matched logical data. The within-Jac 4.93x ratio measures Jac's optimization under a common database and request stack. Jac execution time is the server-total header plus commit time; HTTP client medians are 23.2514 ms and 5.4076 ms. Java timing includes identity/root resolution, execution, result construction and commit. Both execution measures exclude response JSON serialization.

All 80 native Jac timing responses and six census responses pass the independent result checks. Database logging settings were restored and both benchmark services stopped. See [independent verification](jac-comparison/independent-verification.json), [fixture reproduction](jac-comparison/fixture/README.md), and [Jac comparison report](jac-comparison/REPORT.md).

## Baseline construction

The comparison follows two stages defined in [BASELINE_PROTOCOL.md](BASELINE_PROTOCOL.md).

The full Java port matches all 20 Jac inputs in result, per-input SQL count, and query-category counts. The cold sweep executes 278,773 commands; the historical warm sweep executes 278,769. The four-command cold difference consists of one identity lookup and three schema-initialization commands. A repeated warm request for input 0 executes 24 commands, compared with 28 on its first cold execution. See `alignment/alignment-gate.json` and `alignment/verification.json`.

The second-stage implementation removes individually declared Jac runtime services under the benchmark fixture assumptions. All five configurations pass all 20 result, independent SQL-count, and retained domain-hop gates, plus a warm repeat of input 0: 105 validated requests. Exact per-input category-delta verification also passes.

| Cumulative configuration | Cold 20-input commands | Input-0 warm repeat | Additional removal |
|---|---:|---:|---|
| Full Jac behavior | 278,773 | 24 | Reference |
| Remove identity lookup | 278,772 | 24 | 1 cold lookup |
| Also remove ACL owner-root loads | 278,752 | 23 | 20 loads |
| Also remove schema initialization | 278,749 | 23 | 3 cold queries |
| Also remove full-anchor hydration | 247,930 | 20 | 30,819 loads |

Across all removals, the reduction consists of 30,839 full-anchor loads and four cold identity/schema commands. All 247,870 domain-hop commands and 60 transaction commands remain. See `alignment/removal-ledger.json`, `alignment/ablations/20261020T190438Z/summary.json`, and `exact-removal-verification.json`. These runs validate behavior and work counts; their concurrent diagnostic timings are recorded separately from controlled latency experiments.

## Original My-Blog latency experiment

The original WeBridge custom JVM, JDBC interception, graph capture, synthesizer, generated stored procedures, My-Blog application, and WeBench driver were built and executed. The source revision is `ae2e4c2642815ee8622e4af955d406859f718795`. Build and artifact repairs are scripted in `build_toolchain.sh` and `repair_upstream.py`.

Each arm used 300 seconds of warmup followed by 600 measured seconds, one client thread, 5,000 blogs, and MySQL 5.7.25. GI, BD, and EB were driven with equal probabilities. Database egress delay was configured to 2.1 ms; measured ICMP RTT averaged 2.145 ms. The experiment ran on one physical host with separate physical-core groups for application, database, and client. The paper used separate machines; the complete local conditions and workload choices are in `paper/protocol.json`.

| API | Original samples | WeBridge samples | Original p50 (ms) | WeBridge p50 (ms) | p50 speedup |
|---|---:|---:|---:|---:|---:|
| GI: index | 7,871 | 22,907 | 24.148246 | 10.564202 | 2.286x |
| BD: blog details | 7,828 | 22,842 | 17.622282 | 5.855443 | 3.010x |
| EB: edit blog | 8,049 | 22,898 | 27.247385 | 8.869907 | 3.072x |

This table describes one paired run. Quantiles use the original driver's upper-index definition. All 92,395 measured callbacks completed without driver-reported errors. Independent validation reproduces every overall and per-period quantile, sample index, and throughput value from saved raw nanosecond samples. Actual measured durations were 600.008 and 600.006 seconds. Receipts, sample hashes, and p90/p99 values are in `paper/pair-20261020T181922/summary.json` and `independent-validation.json`.

The WeBridge server logged four fallback events during warmup and five during measurement. All concern blog 4, whose sole retained comment takes an additional count-query path. The captured trace expects the configuration query at that position; SQL validation detects the mismatch and switches to ordinary execution. The five measured events represent 0.0219% of the 22,842 BD requests and are included in the reported latency samples. Source locations, generated SQL, log timestamps, and the comment-row oracle are retained in `fallback-independent.json`.

Post-run normal/optimized probes verified this fallback path separately. In each arm, eight warm and three instrumented requests increased the view count by exactly eleven. Every instrumented request executed exactly one blog UPDATE and increased views by one. All six saved HTML responses display the same title and comment; their bytes match after normalizing the displayed view count. The probe receipt and SQL/HTML evidence are in `paper/postformal-blog4-20261020T185432/`. The formal run's after-state was archived before these probes.

## SQL commands and database work

The separate instrumented census checked results and database effects for three requests per API and arm. Actual application business commands changed as follows:

| API | Original top-level commands | WeBridge top-level commands | Table-access statement executions in either arm |
|---|---:|---:|---:|
| GI | 7 | 1 CALL | 7 |
| BD | 6 | 1 CALL | 6 |
| EB | 10 | 2 CALLs | 7 |

Connection-pool `SELECT 1` validation commands are counted separately. General-log observations were cross-checked with Performance Schema account counters and nested statement history. Generated procedures retain table-access statements and add server-side control/result-return operations. Row and index-read counters separately measure the cost of those statements. These observations identify a reduction in application/database exchanges while preserving the number of executed table-access statements. See `paper/sql-census-comparison.json` and `paper/sql-work-classification.json`.

A serialized-roundtrip model provides a quantitative cross-check: saving 6/5/8 commands at the measured 2.145 ms RTT predicts 12.870/10.725/17.160 ms for GI/BD/EB. Observed p50 differences are 13.584/11.767/18.377 ms. This model omits execution, transfer and runtime costs; its inputs and residuals are in `roundtrip-model.json`. The census and timed samples are separate measurements.

Measured-window CPU samples show average application/database core usage of 0.094/0.168 for Original and 0.163/0.363 for WeBridge. The optimized arm completes more requests in the same measurement period. Sampled application RSS peaks are approximately 686/695 MiB. These CPU intervals cover 595.12 and 595.08 seconds inside their respective 600-second windows. The 5-second host samples and saved sample endpoints are archived in `paper/host-samples.jsonl` and `paper/pair-20261020T181922/resource-profile.json`.

## WeBridge integration with the full Jac port

Experiments identified concrete interface boundaries in the public implementation:

1. Generic JDBC replay reaches unimplemented result-set metadata and `getObject` methods. A typed-access derivative preserves the selected values and is validated separately.
2. Whole-request synthesis encounters the explicit `START TRANSACTION READ ONLY` statement. An explicit body-region derivative retains initialization and transaction commands in the complete request and supplies its traversal body to WeBridge.
3. Body synthesis reaches unsupported `IN (SELECT ...)` type-inheritance predicates. An offline AST audit also found nested/UNION projections being accumulated into the outer return-column list. The actual outer query returns two columns.
4. An isolated SQL frontend extension successfully synthesizes the unchanged 21-query tiny body graph. Actual invocation then exposes numeric narrowing: the captured Java `Long` timestamp `1348704000000` becomes an `INT` procedure parameter and MySQL rejects it as out of range. Preserving the Java type through parsing and renaming fixes the declaration to `BIGINT`. A clean synthesis context and actual invocation then return the expected empty result with one procedure CALL and no fallback. This is a functional invocation check; cold runtime initialization is tracked separately from inference latency.

Captured graphs, exact failures, adapter changes, and source hashes are retained under `integration/`. SQL frontend extensions are tracked independently from the two baseline stages. The My-Blog measurements above evaluate the original application; Jac IC5 performance is reported after its compatibility and all-input gates pass.

The first nonempty input's complete cold request records 3,942 commands (3,938 in its historical warm context) and returns the expected 20 rows. Its initial cached concolic replay was terminated by the experiment supervisor after 31.400 seconds when sampled process-group RSS exceeded the configured 12 GiB threshold. It had consumed 3,132 of 3,935 body results. A completed graph was not produced in that attempt. A separate retry raised the sampled RSS budget to 24 GiB while retaining the same input, recording, heap limit, and 300-second timeout; each attempt has its own receipt.

The 24 GiB retry terminated after 33.698 seconds with the original JVM assertion `guarantee(ret < MAX_SYM_RID) failed: sym_rid limitted`. Its sampled peak RSS was approximately 14.316 GB. The implementation fixes `MAX_SYM_RID` at 100,000. It had consumed 3,321/3,935 cached results; the supervisor's memory/time/disk thresholds were not reached. A separate capacity-extended JVM is being evaluated, preserving the original binary and this failure evidence.

The independent capacity variant changes that constant to 1,000,000. Source-manifest comparison identifies this single changed source file, and disassembly verifies the new guard in the binary. Its replay passed the original ID boundary and began graph serialization. The supervisor requested a stop at 49.196 seconds and sampled RSS of 24.038 GiB, but an identified wrapper-cleanup bug allowed the native JVM to continue after the timing wrapper exited. Actual JVM RSS later reached 61,197,287,424 bytes (approximately 57 GiB) before explicit process-group termination. No completed graph was returned. `cleanup-verification.json` records the live JVM and subsequent zero-RSS zombie state; the last completed serialization log entry is SQL index 662. The initial supervisor receipt records the trigger point, rather than a valid resource maximum for this attempt.

The supervisor now checks the entire owned process group on every exit path, immediately kills that group on resource thresholds, and verifies cleanup independently of the wrapper. Regression tests cover timeout with a child ignoring termination, RSS-limit termination, and a normally exiting parent that leaves a background child; all three pass. Receipts are under `integration/capacity-1m/supervisor-test-20261020T192102/`.

A separate diagnostic binary appends the actual RapidJSON buffer byte count to the existing per-statement serialization log. With the corrected supervisor, the full-input run stops at 70.889 seconds and 25,778,556,928 sampled RSS bytes; cleanup verifies an empty active process group. Between SQL serialization indices 22 and 173, buffer contents increase by 6.025 GB and process-group RSS increases by 6.090 GB. RSS is already approximately 19.428 GB before the first observed serialization progress sample. The measurement identifies substantial payload growth during serialization while preserving the earlier memory contribution as a separate quantity. Buffer bytes measure written content, rather than allocator capacity. See `integration/capacity-1m-bufferdiag/` for the raw samples, analysis, CSV and PDF.

The Pruned workload, with the recorded-result UTF-8 conversion adapter, consumes all 3,352 body results and writes a complete native JSON file of 3,406,074,911 bytes (SHA-256 `70564d8f7d80437d49952afd3b9b403395a569758b924cdbb3ed490d20a02805`). Native-to-Java return then raises `NegativeArraySizeException`. Separately invoking the original synthesizer on this preserved file raises `OutOfMemoryError: Required array size too large` at `Files.readAllBytes` in 0.828 seconds. This establishes an implementation boundary at whole-file Java array/string conversion. The original 20-input correctness/count set remains the reference; the smaller nonempty diagnostic below supplies an end-to-end executable comparison.

## Independent small nonempty diagnostic

The diagnostic keeps original input 1's person and raises `min_date` from 1347062400000 to 1347527525888. It retains one forum, fifteen posts, and all fifteen creator traversals. Its result is `[[2061584375281, "Album 7 of Jie Xie", 0]]`. The original Jac baseline returns this result on three real requests with SQL counts 42/38/38; full Java matches those counts and results. Pruned Java executes 31 commands per request. The diagnostic's selection, fixture-subset proof, actual Jac protocol logs, and independent Java counters are under `alignment/small-diagnostic/`.

The original engine captures the Pruned body into a 263,210-byte graph, synthesizes and installs a procedure, and actually executes it with the expected result and no fallback. The first call receives nine client commands; subsequent calls receive four (three retained transaction commands plus one CALL), compared with 31 ordinary commands. On the initial ASCII-UUID schema, complete-request times are 22.452/22.188/22.159 seconds. This slow outcome is retained in `integration/cases/small-pruned-webridge-20261020/`.

An identical-SQL/value control measures the character-set effect:

| UUID binding | `Handler_read_next` delta | Diagnostic CLI wall time (s) |
|---|---:|---:|
| Literal value | 13 | 0.0577 |
| UTF-8 stored-program variable | 601,802 | 0.8320 |
| ASCII stored-program variable | 13 | 0.0481 |

The UTF-8-variable EXPLAIN contains `convert(e.src using utf8mb4)` and chooses the broad `kind_type` access path. UUID columns use ASCII while the database and generated local variables use UTF-8. Counter deltas and saved plans establish the access-path difference; the CLI times include connection/process overhead. A separate uniform-UTF-8 database clone applies equally to baseline and generated procedures. Its 460,984 anchors have the same count and aggregate row checksum as the original. The initial schema, generated procedure, slow calls, and control remain preserved.

Both full and Pruned small-input programs successfully complete capture, synthesis, installation and actual invocation using the original native engine with the documented SQL-scope, numeric-width and recorded-JDBC compatibility overlays. The full version has 35 body queries and a graph of approximately 72 MiB; the Pruned version has 28 body queries and a 263,210-byte graph. Controlled measurements on the uniform-character-set clone give:

| Configuration | No added delay: Java / WeBridge (ms) | Added 2.1 ms delay: Java / WeBridge (ms) | Received commands: Java / WeBridge |
|---|---:|---:|---:|
| Full Jac behavior | 26.326 / 26.711 | 118.552 / 35.489 | 38 / 4 |
| Remove Jac-specific runtime work | 24.528 / 25.007 | 101.388 / 34.287 | 31 / 4 |

Each phase has ten warmup requests and thirty measured requests in the same JVM, with logging disabled. All results match and every optimized request remains on the generated procedure. Observed mean ICMP RTT is 0.040 ms before delay, 2.190 ms during delay, and 0.049 ms after restoration. The delayed p50 speedups are approximately 3.34x and 2.96x. Initial and reversed-order runs without added delay are retained: the full baseline/SP medians range 25.318–26.563/26.711–28.922 ms; Pruned ranges 24.338–25.149/24.822–26.284 ms. These repeated observations show the network-dependent benefit.

The separate instrumented census observes full baseline server-statement time of 22.09–22.15 ms and optimized time of 24.03–24.11 ms. Pruned server times are approximately 21.4–22.1 ms in both arms. Inclusive CALL time is kept separate from nested statement times. During uninstrumented full requests, Handler key/next/random-next counts are 222/1443/771 for Java and 227/1443/825 for WeBridge; Pruned counts are 193/1443/771 and 194/1443/797. Retained traversal reads and extra stored-program/result materialization explain why fewer client commands provide little benefit at local RTT. Added delay makes the reduced command count valuable while server execution remains of similar duration.

`integration/timing/independent_verify.py` independently validates all 480 measured and 160 warmup requests, recomputes every reported median from raw samples, checks generated-procedure activation and exact received-command counts, and writes the standalone English `comparison.pdf`. Raw command lines, input/source hashes, CPU samples, network setup/restoration and the instrumented census are retained under `integration/timing/`, `integration/census/` and `integration/small-final-cleanup/`.
