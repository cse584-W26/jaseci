# Jac and WeBridge on seven existing SNB workloads

The six-query extension covers IS1, IS2, IS3, IC1, IC2 and IC13, alongside the completed IC5 study. It measures eight configurations and distinguishes relational query combination from moving a database-access sequence inside a stored procedure.

**Observed native result:** original and final Jac emit identical ordinary SQL sequences for all six new representative inputs. Their measured latencies remain close. IC5 is the observed case where the final runtime reduces the sequence from 38 to 14 SQL cycles.

## Method and correctness

Original twenty-row parameter collections and historical canonical hashes are frozen. All 240 native original/final, 240 full/pruned Java and 120 conventional SQL result gates pass. Generated procedures are validated on the declared original index0 input; direct-program gates cover twenty inputs. Timing uses original index0, with nonempty outputs for every query, ten warmups and thirty measured requests for fast cells at 0/2/10 ms added database response delay. Slow generated procedures receive three actual fifteen-second bounded attempts per condition, with censored durations and verified server-session cleanup. Actual returned result objects accompany completed timing rows.

The query-complete matched fixture has 1,475,843 anchors: all Person/Knows records, the relevant authored messages and full ReplyOf ancestor/author closure, locations, endpoints and owner roots. Thirteen logical fields round-trip exactly through both loaders. All Java arms share the materialized adjacency/person/message relations and uniform UUID collation. The IC5 companion study uses its separate 460,984-anchor fixture.

Jac runs on PostgreSQL and the Java/WeBridge configurations run on MySQL 5.7. Within each pair, source, engine and data stay fixed. Jac timing adds the server request and commit spans; Java timing measures its JDBC request span. HTTP client latency and Java thread CPU are retained separately. The delay proxy path is shared across the 0/2/10 conditions, with actual SELECT1 calibration. Instrumented protocol/P_S runs are separate from quiet timing.

Full Java follows the ordinary native access sequence. IC13 also has an observed periodic PostgreSQL schema guard, retained separately in native profiles. Pruned Java removes the declared Jac identity/ACL/schema/hydration overhead. Conventional SQL expresses query-specific joins, projections and bounded topK/path work. IS2/IC2 already use explicit Jac database builtins; these source choices belong to the baseline.

## Latency matrix

Completed cells report median request milliseconds. Censored cells record three first requests beyond the fifteen-second bound, before SP warmup completes.

### IS1

| Configuration | 0 ms | +2 ms | +10 ms | Actual sync cycles |
|---|---:|---:|---:|---|
| Jac original | 2.011 | 18.078 | 79.838 | 7 |
| Jac final | 2.053 | 17.574 | 79.594 | 7 |
| Java full | 2.408 | 18.808 | 80.703 | 7 |
| WeBridge full | 2.920 | 11.743 | 45.319 | 4 |
| Java pruned | 1.871 | 12.684 | 57.552 | 5 |
| WeBridge pruned | 2.008 | 11.272 | 50.028 | 4 |
| Java set-oriented | 0.980 | 10.497 | 44.651 | 4 |
| WeBridge set-oriented | 1.230 | 10.637 | 48.204 | 4 |

### IS2

| Configuration | 0 ms | +2 ms | +10 ms | Actual sync cycles |
|---|---:|---:|---:|---|
| Jac original | 6.441 | 68.232 | 272.709 | 24 |
| Jac final | 6.405 | 66.826 | 270.710 | 24 |
| Java full | 6.222 | 62.727 | 270.265 | 24 |
| WeBridge full | 5.260 | 13.682 | 48.707 | 4 |
| Java pruned | 2.438 | 18.640 | 81.819 | 7 |
| WeBridge pruned | 3.362 | 11.987 | 46.225 | 4 |
| Java set-oriented | 1.538 | 11.473 | 45.339 | 4 |
| WeBridge set-oriented | 1.888 | 10.964 | 44.382 | 4 |

### IS3

| Configuration | 0 ms | +2 ms | +10 ms | Actual sync cycles |
|---|---:|---:|---:|---|
| Jac original | 3.330 | 33.403 | 136.969 | 12 |
| Jac final | 3.266 | 35.419 | 137.074 | 12 |
| Java full | 4.734 | 31.768 | 139.823 | 12 |
| WeBridge full | 5.130 | 12.898 | 45.761 | 4 |
| Java pruned | 2.781 | 14.020 | 56.580 | 5 |
| WeBridge pruned | 3.051 | 11.751 | 45.263 | 4 |
| Java set-oriented | 1.665 | 10.946 | 46.460 | 4 |
| WeBridge set-oriented | 2.099 | 11.188 | 44.850 | 4 |

### IC1

| Configuration | 0 ms | +2 ms | +10 ms | Actual sync cycles |
|---|---:|---:|---:|---|
| Jac original | 37.598 | 68.814 | 184.089 | 13 |
| Jac final | 37.442 | 68.512 | 189.191 | 13 |
| Java full | 185.078 | 214.639 | 337.793 | 13 |
| WeBridge full | timeout >15s | timeout >15s | timeout >15s | incomplete CALL |
| Java pruned | 184.122 | 200.352 | 282.086 | 8 |
| WeBridge pruned | timeout >15s | timeout >15s | timeout >15s | incomplete CALL |
| Java set-oriented | 269.244 | 284.882 | 361.322 | 7 |
| WeBridge set-oriented | timeout >15s | timeout >15s | timeout >15s | incomplete CALL |

### IC2

| Configuration | 0 ms | +2 ms | +10 ms | Actual sync cycles |
|---|---:|---:|---:|---|
| Jac original | 10.528 | 97.359 | 379.500 | 33 |
| Jac final | 10.595 | 100.314 | 385.696 | 33 |
| Java full | 23.347 | 103.517 | 392.594 | 33 |
| WeBridge full | 22.395 | 31.227 | 72.781 | 4 |
| Java pruned | 19.901 | 34.654 | 100.207 | 7 |
| WeBridge pruned | 19.819 | 28.040 | 68.986 | 4 |
| Java set-oriented | 15.531 | 26.611 | 74.892 | 5 |
| WeBridge set-oriented | 15.347 | 24.403 | 68.806 | 4 |

### IC13

| Configuration | 0 ms | +2 ms | +10 ms | Actual sync cycles |
|---|---:|---:|---:|---|
| Jac original | 35.142 | 69.981 | 216.228 | 14–15 |
| Jac final | 34.987 | 70.251 | 210.078 | 14–15 |
| Java full | 168.090 | 200.801 | 326.093 | 14 |
| WeBridge full | 2247.407 | 2232.176 | 2314.678 | 4 |
| Java pruned | 166.789 | 183.268 | 263.404 | 8 |
| WeBridge pruned | 2256.630 | 2243.120 | 2291.719 | 4 |
| Java set-oriented | 1.531 | 11.033 | 44.452 | 4 |
| WeBridge set-oriented | 1.898 | 11.244 | 44.478 | 4 |

## Which operations are combined?

All native profiles match SQL against the request-owned backend log and prove the next command follows prior ReadyForQuery delivery. Ordinary counts are IS1 7, IS2 24, IS3 12, IC1 13, IC2 33 and IC13 14. In one +2ms profile per native variant, IC13 executes a schema TTL guard and reaches 15 cycles.

### IS1

Jac emits three full-anchor loads and one location traversal, alongside three transaction commands. The original/final sequence is identical. Compare the actual generated CALL against the full and pruned direct sequences; the nested operation map records retained table operations. Conventional SQL combines the Person/location projection with a LEFT JOIN in one business query. Full object hydration remains separate in Jac.

| Native category | Actual executions per profiled request |
|---|---:|
| traversal.generic | 1 |
| transaction.commit | 1 |
| transaction.begin | 1 |
| transaction.setting | 1 |
| hydration.full_anchor | 3 |

### IS2

Jac already uses explicit jtopk and jroot_many builtins: lateral topK and promoted reply roots. Fifteen full-anchor loads, author projection/traversal and guest resolution remain. The Java port preserves the ordinary native sequence. Its MySQL topK adaptation uses finite per-origin branches because MySQL 5.7 lacks LATERAL. One conventional query joins the message mirror, reply-root message and both authors, orders by date/ID, and limits to ten. All twenty historical outputs pass.

| Native category | Actual executions per profiled request |
|---|---:|
| reply_root.promoted_column | 1 |
| projection.person_fields_acl | 1 |
| traversal.generic | 1 |
| transaction.commit | 1 |
| transaction.begin | 1 |
| identity.guest_resolution | 2 |
| transaction.setting | 1 |
| hydration.full_anchor | 15 |
| topk.lateral | 1 |

### IS3

Jac already projects friend fields in two directional Knows queries. Root/Person loads, type discovery, root permissions and guest resolution remain separate. Actual full capture required column aliases and scalar JSON/type metadata compatibility fixes. Each attempt and the selected source snapshot are retained. Conventional SQL combines both incident-edge directions and Person projection in one UNION ALL query. It returns the same twenty historical results.

| Native category | Actual executions per profiled request |
|---|---:|
| acl.root_permissions | 2 |
| type_registry | 1 |
| transaction.commit | 1 |
| transaction.begin | 1 |
| transaction.setting | 1 |
| identity.guest_resolution | 2 |
| hydration.full_anchor | 2 |
| projection.graph_hop_acl | 2 |

### IC1

Jac performs three adjacency-frontier expansions, endpoint filtering and a Person projection. Three anchor loads and two guest lookups remain separate. The final sequence matches the original. This case measures synthesis over an actual frontier-based graph traversal. Capture and synthesis outcomes are recorded at their executed stages. The measured conventional reference retains frontier BFS. A finite-depth UNION alternative passed twenty outputs but had a higher diagnostic median, so BFS was selected.

| Native category | Actual executions per profiled request |
|---|---:|
| projection.person_fields_acl | 1 |
| transaction.commit | 1 |
| transaction.begin | 1 |
| transaction.setting | 1 |
| closure.endpoint_filter | 1 |
| closure.frontier_adjacency | 3 |
| identity.guest_resolution | 2 |
| hydration.full_anchor | 3 |

### IC2

Jac already requests topK explicitly. Twenty-five full-anchor loads, two Knows traversals, a HasCreator traversal and a type probe remain separate. Full Java retains the observed object-loading sequence; the declared pruned form removes Jac-specific loading while preserving the query output. Conventional SQL first selects friends, then unions bounded per-author/type top-20 candidates and applies global top-20. Both candidate and selected outputs were measured against all twenty historical hashes.

| Native category | Actual executions per profiled request |
|---|---:|
| type_registry | 1 |
| traversal.generic | 3 |
| transaction.commit | 1 |
| transaction.begin | 1 |
| transaction.setting | 1 |
| hydration.full_anchor | 25 |
| topk.lateral | 1 |

### IC13

Actual execution uses indexed adjacency-frontier BFS. Three frontiers reach the selected endpoint; a periodic schema guard can add one cycle. Full/pruned generated BFS procedures contain about 4.85 million row-index checks at the captured cursor sizes. Their actual quiet latencies and observed table operations are reported separately. The conventional alternative uses ordered CASE/EXISTS for lengths zero through six, matching the benchmark cap. All twenty outputs pass; its diagnostic median was lower than the BFS candidate.

| Native category | Actual executions per profiled request |
|---|---:|
| projection.person_fields_acl | 1 |
| transaction.commit | 1 |
| transaction.begin | 1 |
| identity.guest_resolution | 2 |
| transaction.setting | 1 |
| closure.endpoint_filter | 1 |
| closure.frontier_adjacency | 3 |
| schema.ttl_guard | 0–1 |
| hydration.full_anchor | 4 |

## Actual WeBridge pipeline and profiling

Every selected procedure comes from the original record/replay/synthesis/install pipeline. The configured capture region is after the session SET and before COMMIT; START/SET/COMMIT remain three outer client commands. Cold callable-statement metadata queries remain in warmup records; measured requests check actual query counts, one CALL and procedure activation through the request end. Concrete compiler failures, compatibility overlays, graph/source/class hashes and selected cases are preserved.

MySQL traces count command-to-complete-response cycles separately from frames, result sets and bytes. Performance Schema collection unions thread/event IDs and checks the observed CALL range before assigning nested operations. Business table SELECTs and cursor materializations, replay/result SELECTs and stored-program control events have separate categories. Parent CALL timers include descendants.

## Measured IC1 procedure overhead

The pruned IC1 generated procedure has cursor loops with 10, 2,750 and 9,009 independent row-dispatch IF branches. Each loop scans all branches for every counter value through its exit: sum N(N+1) = 88,736,450 equality checks. One instrumented CALL completed with the correct result, using 129.396 seconds inside MySQL (129.883 seconds at the JDBC request boundary). Raw Performance Schema counters and generated-source bounds support the explanation. A separate control with statement/sp instrumentation disabled exceeded the fifteen-second request bound and was terminated on its verified owned connection. The completed instrumented duration and quiet censored samples retain distinct labels.

## IC1: actual query work on the same MySQL fixture

Full/pruned Java first selects twenty first-name candidate IDs, expands three frontiers, then projects eighteen matching people. The conventional reference expands the same frontiers and applies its final predicate over 9,036 visited UUIDs. Its last query examines 9,932 Person rows and returns eighteen. The raw P_S query flag records NO_INDEX_USED=1 for that conventional projection.

| Java variant | Quiet 0ms request median | Profile frontier statements | Profile final projection | Final rows examined |
|---|---:|---:|---:|---:|
| full | 185.078ms | 176.253ms | 0.237ms | 18 |
| pruned | 184.122ms | 177.553ms | 0.240ms | 18 |
| conventional | 269.244ms | 177.491ms | 86.639ms | 9932 |

These columns retain separate quiet and instrumented windows. Each profiled frontier sequence examines 175,262 rows and returns 11,769 rows. Native original/final quiet IC1 medians are about 37 ms, while their logging/protocol profiles have materially larger timings; the measured same-engine SQL contrast above isolates a different per-query work choice. See ic1-cost-breakdown.json and ic1-same-engine-comparison.json for paired per-request quantities and exact SQL hashes.

## IC13: actual remaining procedure interval

| Variant | Profile CALL median | Instrumented child statements | Paired remaining CALL interval |
|---|---:|---:|---:|
| full | 2290.671ms | 164.126ms | 2126.545ms |
| pruned | 2265.886ms | 162.593ms | 2103.747ms |
| conventional | 0.861ms | 0.793ms | 0.067ms |

Full/pruned profiles observe actual table statements and cursor opens with stored-program control events disabled. Their remaining approximately 2.1 seconds include uninstrumented cursor/control and other procedure runtime work. The generated source has approximately 4.85 million row-index checks at recorded cursor sizes. The conventional CASE/EXISTS query instead performs bounded path tests inside one scalar-returning SQL statement. Exact observed operations, instrument settings and per-request residual calculations are in ic13-cost-breakdown.json.

## Reproduction and evidence

Run `python benchmark-comparison/verify_results.py --java-timing`, then `python benchmark-comparison/collect_results.py` and `python benchmark-comparison/build_pdf.py`. The independent receipts rehash actual outputs against `historical-hashes.json` and recompute reported values from raw data. See [artifact guide](README.md), [results JSON](results.json), [new-query PDF](jac-webridge-snb-comparison.pdf), and the [IC5 companion report](../roundtrip-comparison/REPORT.md).

`archive-manifest.json` in the parent directory records included SHA256 values. Query source snapshots, generated procedures, actual timing rows, payload-free framing, SQL catalogs, failure logs, calibration and cleanup receipts accompany this report.
