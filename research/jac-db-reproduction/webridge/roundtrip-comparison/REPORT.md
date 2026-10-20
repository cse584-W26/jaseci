# Jac and WeBridge: complete performance and SQL-combination experiments

[English PDF](jac-webridge-measured-comparison.pdf) · [Verified eight-configuration data](eight-arm-verification.json) · [Detailed WeBridge operation map](webridge-operation-map.md)

Both experiments include eight configurations: original Jac, Jac SQL pushdown, full-behavior Java, full Java through WeBridge, pruned Java, pruned Java through WeBridge, set-oriented Java SQL, and set-oriented Java SQL through WeBridge.

## Experiment 1: latency at three database-delay settings

The fixed nonempty IC5 request uses the same logical 460,984-anchor, 300,901-edge graph. Each cell contains ten warmup and thirty measured requests. The main eight-configuration matrix has 960 checked responses; the set-oriented direct/CALL comparison also has 240 reverse-order responses. Every result equals the input oracle.

| Configuration | 0 ms | +2 ms | +10 ms | SQL / sync cycles |
|---|---:|---:|---:|---:|
| Jac original | 25.89 | 145.26 | 469.42 | 38 |
| Jac SQL pushdown | 5.73 | 39.53 | 160.23 | 14 |
| Java full | 28.75 | 120.74 | 463.64 | 38 |
| WeBridge full | 27.20 | 37.25 | 75.63 | 4 |
| Java pruned | 27.64 | 105.27 | 385.60 | 31 |
| WeBridge pruned | 25.62 | 33.70 | 69.23 | 4 |
| Java set-oriented SQL | 9.56 | 18.79 | 58.82 | 4 |
| WeBridge set-oriented SQL | 9.81 | 18.61 | 53.96 | 4 |

Times are request-execution medians in milliseconds. Settings are 0/2/10 ms injected response-direction delay through the same byte-forwarding proxy. Calibrated persistent SELECT 1 round trips are retained for each run. Jac uses PostgreSQL 18.6 and its HTTP server timer plus commit; Java uses MySQL 5.7.44 and a JDBC request timer. Both exclude result JSON serialization. The Jac runtime uses derived mirror/adjacency structures; the Java programs use the generic MySQL anchor fixture. Cross-system absolute times include these implementation choices.

The set-oriented WeBridge version uses the actual original recording, original Zero symbolic JVM, compiler, unchanged generated procedure, and optimized replay. It passes all twenty original parameterized result gates, with one actual CALL and four outer commands on every input. No SQL frontend change was needed for this query. See [the pipeline report](../alignment/idiomatic/WEBRIDGE.md) and [generated-body mapping](../alignment/idiomatic/webridge-command-mapping.json).

The new paired measurements use direct then CALL in the main table. Reversing phase order produces:

| Delay | Direct first | CALL second | Direct second | CALL first |
|---|---:|---:|---:|---:|
| 0 ms |9.56|9.81|9.57|10.19|
| 2 ms |18.79|18.61|18.51|18.83|
| 10 ms |58.82|53.96|55.40|57.73|

The 10 ms ordering reverses when phase order is reversed. These samples show no consistent WeBridge speedup for the already set-oriented query. Its synchronization count stays four in both implementations.

## Experiment 2: actual synchronization and SQL-operation boundaries

This experiment uses separate instrumented runs, rather than estimating round trips from the latency slope. Twelve measured native Jac requests cover both variants at zero and two milliseconds; eighteen measured MySQL requests cover all six Java/WeBridge arms at two milliseconds. Warmup precedes each group. Exact results, server SQL/PID matching, protocol framing and request boundaries are verified independently.

| Configuration | Serialized command/complete-response cycles | Business/runtime reads represented | Outer transaction commands |
|---|---:|---|---:|
| Jac original |38|35 separate reads|3|
| Jac SQL pushdown |14|11 separate reads|3|
| Java full |38|35 separate reads|3|
| WeBridge full |4|35 original business table operations inside CALL|3|
| Java pruned |31|28 separate reads|3|
| WeBridge pruned |4|28 original business table operations inside CALL|3|
| Java set-oriented SQL |4|1 aggregate SELECT|3|
| WeBridge set-oriented SQL |4|1 aggregate SELECT inside CALL|3|

PostgreSQL traces show named prepared execution after warmup: one Bind, Describe, Execute and Sync group per statement, ending at ReadyForQuery. The next Bind arrives after the prior Ready has been delivered. Thus these requests have exactly 38 and 14 serialized synchronization cycles. The baseline produces 39 backend socket chunks for 38 cycles, and final produces fourteen chunks for fourteen cycles. Frame and chunk counts are recorded separately.

The MySQL decoder reconstructs complete packets across arbitrary socket chunk boundaries and honors the negotiated CLIENT_DEPRECATE_EOF capability. Every command has exactly one received and one delivered complete response. Each next command follows prior complete delivery. The full, pruned and set-oriented pairs therefore measure 38→4, 31→4 and 4→4 cycles. Authentication, connection setup, status observers and warmup are outside the reported request boundaries.

## Which SQL Jac combines, and which remains separate

| Logical/database operation | Original Jac SQL | Final Jac SQL | Actual emitted form |
|---|---:|---:|---|
| START / SET / COMMIT |3|3|Three separate commands|
| Root, person, friend batches, forum hydration |5|5|Five separate SELECTs remain|
| Post-batch and creator hydration |2|0|Absent from final request|
| Knows outgoing/incoming |2|2|Two separate traversal SELECTs remain|
| HasMember traversal |10|1|One batched query over ten friends|
| Standalone HasMember / Forum ancestry probes |0|2|Two separate type-registry SELECTs remain|
| ContainerOf / HasCreator traversal |1 + 15|0|Represented in fused aggregate below|
| Count / ordering / LIMIT aggregate |0|1|Member-driven relational SQL|
| Total |38|14|Every measured profile request agrees|

The exact reduction is **38 − 9 membership queries − 15 post/creator queries − 2 hydration queries + 2 ancestry probes = 14**. The single qualifying forum is hydrated before the fused aggregate in this observed request.

The final compiler/runtime recognizes the batch membership frontier and the post-count/order/top-K pattern. It emits the two Knows traversals, five remaining hydration SELECTs, two ancestry probes and transaction commands separately. [The SQL catalog](../jac-comparison/roundtrip-profile/results/sql-catalog.json) preserves complete statements; [the operation map](../jac-comparison/roundtrip-profile/results/operation-map.json) identifies every sequence position and stable SQL ID. [Source anchors](../jac-comparison/roundtrip-profile/source-anchors.json) locate the code generation, runtime fast paths, type probes and hydration code.

## Which SQL each WeBridge version captures and combines

The configured recording region begins after SET and ends before COMMIT. All original business SELECTs inside that region are captured. The three outer transaction commands stay outside that region and execute separately.

Actual nested Performance Schema events, generated cursor declarations, literal parameters and observed cursor IDs establish the following business table-operation counts inside the CALL:

| Business operation inside CALL | Full | Pruned | Set-oriented |
|---|---:|---:|---:|
| Hydration |7|0|0|
| Knows |2|2|Included in aggregate|
| HasMember |10|10|Included in aggregate|
| ContainerOf |1|1|Included in aggregate|
| HasCreator |15|15|Included in aggregate|
| Set-oriented aggregate |0|0|1|
| Business table-operation total |35|28|1|

Thus the full and pruned WeBridge procedures retain the original graph-traversal query sequence inside a single client CALL. Jac batches membership and replaces post/creator traversal with a relational aggregate. Compared with set-oriented Java and its WeBridge procedure, Jac still emits friend traversal, membership, hydration and ancestry reads as separate SQL statements; the set-oriented query includes friend, membership and post/creator joins in its one aggregate SELECT.

The complete observed CALL additionally contains generated result/parameter work:

| Direct child event category | Full | Pruned | Set-oriented |
|---|---:|---:|---:|
| Business table SELECTs |25|24|1|
| Business cursor materializations |10|4|0|
| Result/parameter metadata SELECTs |11|5|1|
| Variable/control instrumentation events |2,447|1,510|12|

Cursor materialization executes the original business query. Variable/control totals are stored-program instrumentation events. Counts use direct CALL children so nested descendants are accounted for once. The generated set-oriented procedure keeps the original aggregate, records FOUND_ROWS and returns one QUERY_ID/parameter metadata result set. Exact line mapping and generated-body SHA256 are retained.

## Actual result protocol traffic

| MySQL implementation | Sync cycles | Response protocol frames | Result sets | Response wire bytes |
|---|---:|---:|---:|---:|
| Java full |38|276|35|29,286|
| WeBridge full |4|970|36|68,300|
| Java pruned |31|176|28|6,798|
| WeBridge pruned |4|608|29|30,547|
| Java set-oriented SQL |4|9|1|220|
| WeBridge set-oriented SQL |4|17|2|495|

All three measured requests per arm agree on these counts. Frames are MySQL protocol packets, rather than TCP packets. Bytes include those protocol headers and complete responses for the request, excluding setup/status observers. One CALL reduces serialized exchanges while returning multiple result sets and frames. These traffic measurements are separate from the quiet latency experiment.

## Evidence, verification and cleanup

- [Verified eight-configuration matrix](eight-arm-verification.json): all 24 latency cells and all eight protocol rows.
- `verify_eight_arms.py`: result/count/timing/cleanup checks for both experiments.
- `analyze_mysql.py`: request boundaries, command-complete-response sequencing, result-set/frame/byte counts.
- `audit_operation_map.py`: independent raw protocol and actual nested procedure-operation audit.
- [PG operation map](../jac-comparison/roundtrip-profile/results/operation-map.json), [certified flights](../jac-comparison/roundtrip-profile/results/certified-flights.json) and `analyze.py`: SQL/PID/protocol matching.
- `test_mysql_parser.py`: legacy/deprecated EOF, empty result sets, multiple result sets and arbitrary frame fragmentation.
- `build_pdf.py`: builds the English PDF from verified data and measured operation maps.

The initial MySQL instrumentation attempt assumed a legacy column EOF marker. The driver negotiated deprecated EOF instead; parser consistency checks rejected those counts. The corrected parser reads negotiated capabilities and passes fresh profiles with zero overlap, termination or response-completion errors. That initial attempt remains separately labeled and excluded from all reported measurements.

All benchmark services and delay proxies are stopped. Database logging settings are restored. Raw request rows, payload-free protocol metadata, SQL catalogs, procedure sources, server profiles and cleanup receipts are retained with the results.
