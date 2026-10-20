# IC5 integration and native-capture profiling

The Java port passes result and independently counted SQL gates. The nonempty idx1 compiler experiments identify separate symbolic-ID capacity, native serialization memory and Java array-size boundaries. The tables below describe capture/synthesis diagnostics; their wall times are compiler-stage measurements. The original My-Blog latency pair remains a separate experiment in [../RESULTS.md](../RESULTS.md).

## Baseline and intervention boundaries

The full port's source SHA is `acc9b168a3fb579829f2c52c8a07b7be3361a9be9d983bfd9bec0412003246a2`. All twenty inputs plus a repeated input0 match Jac results, independent MySQL statement totals and query categories: 278,773 statements in the cold twenty-input sweep and 24 for the warm repeat. The historical warm total is 278,769; the four-command cold increment is one identity lookup and three schema-initialization commands. [Alignment gate](../alignment/alignment-gate.json), [verification](../alignment/verification.json).

Stage 2 removes runtime services through explicitly declared flags while retaining domain traversal, predicates, sorting, limit and transaction behavior. Its exact-removal verification covers five configurations, each with twenty cold inputs and one warm repeat, including independent server counts and result oracles:

| Cumulative configuration | Cold20 statements | Warm input0 statements |
|---|---:|---:|
| Full | 278,773 | 24 |
| Remove auth | 278,772 | 24 |
| Remove auth and ACL | 278,752 | 23 |
| Also remove schema discovery | 278,749 | 23 |
| Also remove full hydration | 247,930 | 20 |

The validated Pruned source SHA is `32d67d833ed0624809316029af67586cd50f1b0f55bdc7446bb560fac0c2a3e7`. [Exact category-delta verification](../alignment/ablations/20261020T190438Z/exact-removal-verification.json). These removals are distinct from the following compatibility and diagnostic changes:

| Layer | Change and evidence |
|---|---|
| JDBC access | Typed getters replace generic metadata/getObject paths unsupported by recorded result sets. The final getLong/wasNull adapter preserves all 21 request oracles/categories/counts, cold-20 total = 247,930, repeat input0 = 20: [getLong gate](cases/pruned-region-getlong-gate-20261020/gate-20261020T191708057203Z/verification.json). |
| Recorded JDBC strings | Actual recording contains 6,376 rows/13,396 cells; all 322 Forum rows have Long column3 and byte[] column4. An isolated recorded-result overlay decodes UTF8 byte arrays and stringifies Number values, preserving null/String behavior and serialVersionUID. [Tests and source provenance](jdbc-string/README.md), [provenance](jdbc-string/provenance.json). |
| Compilation region | The explicit body begins after transaction setup and ends before COMMIT. Complete-request counters retain the SQL outside that region. |
| SQL frontend | Metadata resolution handles outer projections, nested IN/UNION scopes and original positional bindings while preserving SQL AST text. [Frontend tests/provenance](sql-frontend/README.md). |
| Numeric width | The native J symbol and its renamed expressions retain Java-long width/bounds. [Width provenance](numeric-width/provenance.json). |
| Native capacity | A separate image raises MAX_SYM_RID 100,000→1,000,000. A subsequent separate image adds one buffer-size log line. Original engine images and failed attempts remain intact. [Capacity source audit/build](capacity-1m/README.md), [buffer diagnostic](capacity-1m-bufferdiag/README.md). |

## Immutable nonempty full idx1 recording

The [original full idx1 record](cases/nonempty-idx1-region-width-20261020/record-20261020T190413476273Z/report-0.json) passes its result oracle and independently counted 3,942 complete-request commands. The recorded body contains 3,935 SQL/result items; six setup commands precede the body and COMMIT follows it. Its region source SHA is `915d5f4c6642a31fbc2bf74f114a583556cb1f4e908a3c13b27dd5e179f52310`.

All full attempts below reuse that same `record-cold-1.bin` and saved process state, with an 8 GiB heap, 300-second wall budget and 8 GiB case-output budget. Exact commands, classpaths, selected JVM hashes and process/resource receipts live under each attempt. [Original immutable-file hashes](capacity-1m/original-failure.json), [postdiagnostic unchanged-file check](cases/nonempty-idx1-region-width-20261020/replay-20261020T192604500903Z/immutable-original-check.json).

| Engine/attempt | Sampled RSS threshold | Controller wall seconds | Outcome and sampled RSS |
|---|---:|---:|---|
| Original100k, [190429](cases/nonempty-idx1-region-width-20261020/replay-20261020T190429292775Z/process-result.json) | 12 GiB | 31.400 | First RSS stop at 12,896,768,000 B. This predates the supervisor repair. |
| Original100k, [190606](cases/nonempty-idx1-region-width-20261020/replay-20261020T190606892540Z/process-result.json) | 24 GiB | 33.698 | Actual fatal `guarantee(ret < MAX_SYM_RID)` at threadContext.hpp:198; sampled peak 14,315,732,992 B (14.316 GB, 13.332 GiB). |
| Capacity1m, [191615](cases/nonempty-idx1-region-width-20261020/replay-20261020T191615824510Z/process-result.json) | 24 GiB | 49.195 | First RSS trigger 25,810,964,480 B; wrapper exited while native child continued. Later observed 61,197,287,424 B, then independently verified group kill. |
| Capacity1m plus buffer log, [192604](cases/nonempty-idx1-region-width-20261020/replay-20261020T192604500903Z/process-result.json) | 24 GiB | 70.889 | Fixed supervisor stops at sampled 25,778,556,928 B; no live owned process remains. No completed graph. |

The first capacity attempt's 24 GiB setting was a trigger, not an enforced peak. Its final stdout includes post-trigger execution, so serialization index 662 cannot locate the phase at the first trigger. The observed leak came from waiting only for `/usr/bin/time` after SIGTERM while the native JVM child survived. The corrected supervisor checks process-group members independently, kills immediately on RSS/output triggers and verifies cleanup in finally on every exit path. Three synthetic regressions cover ignored SIGTERM, a small RSS trigger and a successful parent leaving a background child: [tests](capacity-1m/supervisor-test-20261020T192102/summary.json). [Actual leak/cleanup receipt](cases/nonempty-idx1-region-width-20261020/replay-20261020T191615824510Z/cleanup-verification.json).

The native capacity guard uses unsigned-long IDs stored in maps; the complete four-use audit found no fixed 100k-sized allocation. Actual machine code verifies unsigned compare 99,999 in the original image and 999,999 in the capacity variant. The original libjvm SHA remains `34f5eabaca3f544eb80f1b4db1fb2be64b39dfb1b1b1380790f79026001edc12`; capacity-only SHA is `7bf668e4edcfcd04e0e0a312b0a05e4d5dc11d03598780ef0dc135699af6e19f`; buffer-log SHA is `3c28261c2eb45acc3d246c64fe5faef99cc20c7c71ea3775fd3c1633a7dce7c0`. [Capacity binary verification](capacity-1m/binary-verification.json), [diagnostic binary verification](capacity-1m-bufferdiag/binary-verification.json).

## Measured JSON-buffer growth

The fixed-supervisor diagnostic records 67 resource samples, including 17 samples paired with serializer progress. Each completed SQL log reports actual StringBuffer.GetSize; that is logical written JSON bytes, not reserved allocator capacity or a resident-memory partition.

| Sample | Seconds | Last serialized SQL index | JSON bytes | Process-group RSS bytes |
|---|---:|---:|---:|---:|
| First recorded buffer progress | 54.296 | 22 | 195,024,482 | 19,688,787,968 |
| Last recorded buffer progress | 70.736 | 173 | 6,220,053,459 | 25,778,556,928 |

Over this observed interval, logical JSON grows 6,025,028,977 bytes while RSS grows 6,089,768,960 bytes. Large memory use also exists before the first buffer-progress sample: the highest such RSS sample is 19,428,118,528 bytes. This separates the measured additional serialization growth from the earlier retained-memory baseline; its allocation breakdown requires additional instrumentation. Source owns one full in-memory RapidJSON buffer until statementsToJsonString returns. SQL index counts statement objects, not graph nodes.

[Analysis JSON](cases/nonempty-idx1-region-width-20261020/replay-20261020T192604500903Z/buffer-memory-analysis.json), [raw-aligned CSV](cases/nonempty-idx1-region-width-20261020/replay-20261020T192604500903Z/buffer-memory.csv), [PDF](cases/nonempty-idx1-region-width-20261020/replay-20261020T192604500903Z/buffer-memory.pdf), [PNG](cases/nonempty-idx1-region-width-20261020/replay-20261020T192604500903Z/buffer-memory.png). All original records and graph files remain unchanged.

## Pruned idx1: completed native output and Java size rejection

The corrected [Pruned recording](cases/pruned-jdbc-string-idx1-20261020/record-20261020T192352068388Z/report-0.json) passes its result oracle with 3,355 complete-request commands and 3,352 body SQL/result items. Its region source SHA is `8d49b33aed322f1f3643a2be353b10c908eca13c8b37a89dc5640b2d18f44be0`. The original 100k engine plus separately recorded frontend/width/JDBC overlays completes native graph serialization under the 12 GiB RSS budget.

The native output is 3,406,074,911 bytes, SHA256 `70564d8f7d80437d49952afd3b9b403395a569758b924cdbb3ed490d20a02805`. It is preserved as [native-graph-before-java-return.json](cases/pruned-jdbc-string-idx1-20261020/replay-20261020T192403127766Z/native-graph-before-java-return.json). Replay takes 60.364 seconds with sampled peak 7,027,486,720 B, then throws `NegativeArraySizeException` at System.weBridgeAnalysis0. The native manager saves the whole graph before jvm.cpp converts the returned string into a Java String, explaining why a file survives the Java-return failure. [Replay receipt](cases/pruned-jdbc-string-idx1-20261020/replay-20261020T192403127766Z/process-result.json), [exception](cases/pruned-jdbc-string-idx1-20261020/replay-20261020T192403127766Z/stderr.log).

A separate bounded synthesis attempt opens that retained output through the original whole-file Java reader. It fails in 0.828 seconds with `OutOfMemoryError: Required array size too large` at Files.readAllBytes, at sampled 75,952,128 B RSS. The 3.406 GB file exceeds the signed 32-bit Java array-length boundary; increasing heap does not alter that representation limit. [Synthesis receipt](cases/pruned-jdbc-string-idx1-20261020/synth-20261020T192639313398Z/process-result.json), [actual exception](cases/pruned-jdbc-string-idx1-20261020/synth-20261020T192639313398Z/stderr.log). The streaming structural check is tracked by the runtime agent against the immutable SHA, without rereading the file into a Java byte array.

These outcomes provide separate evidence for a completed native artifact, Java-return rejection, whole-file synthesis-reader rejection and interrupted full-port capture. Completed optimized IC5 inference timings require their own generated-procedure and complete-request result gates. Native Jac baseline/final measurements on the matched PostgreSQL fixture are recorded separately under [../jac-comparison/](../jac-comparison/), preserving the PostgreSQL versus MySQL execution boundary.
