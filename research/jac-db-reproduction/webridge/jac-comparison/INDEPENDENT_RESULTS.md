# Matched-fixture native Jac independent check

Both arms pass direct expected-result checks for all ten warm and thirty measured HTTP requests. The input is the explicitly selected small diagnostic: original person index1, UUID `6c0eeb86-bda6-5055-b3cf-81a8bf523191`, with min_date raised to `1347527525888`. It returns one forum and traverses fifteen posts. [Input](../alignment/small-diagnostic/input.json), [selection](../alignment/small-diagnostic/selection.json). This is separate from the original twenty-parameter sweep and the large original-idx1 native capture.

| PostgreSQL native Jac arm | Warm / measured | Server median ms | HTTP client median ms | App CPU ms/request | Cold / warm SQL census |
|---|---:|---:|---:|---:|---|
| Baseline c12ba889d | 10 / 30 | 22.2975 | 23.251369 | 6.000 | 42 / 38,38 |
| Final 85b1efc07 | 10 / 30 | 4.5230 | 5.407603 | 2.667 | 30 / 14,14 |

Within the same Jac HTTP/PostgreSQL stack, median server speedup is 4.9298×; median client speedup is 4.2998×. Server values reproduce header total plus commit. Conventional medians are recomputed from all thirty measured samples. CPU values use the whole thirty-request application-process interval, including inter-request housekeeping; the original 10 ms CPU tick resolution makes single-request CPU medians unsuitable for these short requests.

The independent checker reopens the logged census gzip files, verifies their SHA, recomputes top-level execution counts by backend PID and excludes Parse/Bind phases. Cold windows include initialization and setup PIDs. Stable warm counts are 38 and 14. Timing is collected separately with duration logging disabled. Restored receipts record service stop and logging restoration.

[Independent verification and input hash](independent-results.json), [reproduction script](verify_results.py), [fixture verification](fixture/independent-verification.json). Baseline/final share the same three application-file hashes; their exact runtime revisions and process configurations are preserved under timing/*/source.json and launch.json.

The selected small diagnostic's earlier Jac/Full Java gate independently aligns cold/warm counts at 42/38/38, with Pruned counts 31: [gate](../alignment/small-diagnostic/verification.json). Java/WeBridge runs use MySQL and their declared CLI timing boundary; this native Jac table uses PostgreSQL and HTTP/server-header boundaries. The common anchor closure, input and result oracle support a controlled workload comparison while preserving those engine and boundary labels.
