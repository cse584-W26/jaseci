# Set-oriented Java through the original WeBridge pipeline

The single aggregate from `ic5.sql` was recorded with the original extended JDBC interceptor, replayed by the original 100k-capacity Zero JVM, and synthesized by the original WeBridge compiler with the existing SQL frontend, numeric-width and recorded-JDBC compatibility overlays. The emitted SQL was installed unchanged into `jac_alignment_utf8`. The original engine graph and generated procedure are retained in `integration/cases/idiomatic-small-20261020`.

The recording contains one prepared statement with parameters String, String and long. Its business region starts after session setup and ends before commit. The request's transaction boundary is identical in both modes:

| Step | Direct SQL | WeBridge |
|---|---|---|
| 1 | START TRANSACTION READ ONLY | same |
| 2 | SET SESSION innodb_lock_wait_timeout=10 | same |
| 3 | Prepared aggregate SELECT | generated CALL(min_date, person_uuid) |
| 4 | COMMIT | same |

`webridge-command-mapping.json` links every generated body statement to its exact source line and pins the procedure SHA. The body binds three local query parameters, assigns the result query ID, executes the aggregate, saves FOUND_ROWS(), and emits the query-ID/parameter metadata SELECT. The aggregate remains one table-access SQL operation. The extra SELECT serializes invocation metadata; assignments and control statements are additional stored-program work. Top-level command counts and internal statements use separate accounting.

The selected small input passes recording, replay and optimized execution. `webridge-gate20-final` additionally tests all 20 original input/output oracles against the same generated procedure: all outputs match, every request has one actual CALL, Questions delta four, and SP invocation remains enabled. The runtime reports that some actual results contain more rows than the one-row recording; these cases pass the explicit result equality checks. Earlier launcher failures (reflection visibility and unrelated static initialization) are preserved as `webridge-gate20` and `webridge-gate20-retry`; the query and generated procedure were unchanged by these launcher corrections.

The paired timing series is `webridge-delay-results`, with direct SQL then SP in each condition. Each arm uses 10 warm and 30 measured requests, affinity 9,19, the same Server JVM and shared response-direction delay proxy. All 240 requests pass exact output and SQL-count gates. Pre/post SELECT 1 calibration samples and stopped-proxy receipts accompany every cell.

| Response delay | Direct SQL median (ms) | Generated SP median (ms) |
|---|---:|---:|
| 0 ms | 9.5646 | 9.8058 |
| 2 ms | 18.7915 | 18.6080 |
| 10 ms | 58.8204 | 53.9624 |

The reverse-order series (SP then direct SQL) also passes all 240 requests:

| Response delay | Direct SQL median (ms) | Generated SP median (ms) |
|---|---:|---:|
| 0 ms | 9.5667 | 10.1924 |
| 2 ms | 18.5081 | 18.8336 |
| 10 ms | 55.3987 | 57.7277 |

At 10ms the ordering reverses between the two series. These measurements support reporting both phase orders, rather than a consistent SP latency improvement for an already set-oriented query. Both modes send four top-level commands. The independent verifier `verify_webridge.py` recomputes these statistics from raw rows, checks CALL activation and exact output, and verifies process cleanup. The reverse-order series uses `webridge_reverse_sweep.py` and its separate `webridge-delay-reverse-results` directory. The root protocol/P_S census supplies actual transport and internal-statement traces separately from these uninstrumented timings.

Reproduction entry points:

```sh
python reproduction/webridge/alignment/idiomatic/webridge.py record
python reproduction/webridge/alignment/idiomatic/webridge.py replay
python reproduction/webridge/alignment/idiomatic/webridge.py synth /absolute/path/to/retained/graph.json
python reproduction/webridge/integration/install_utf8.py --case reproduction/webridge/integration/cases/idiomatic-small-20261020
python reproduction/webridge/alignment/idiomatic/webridge.py optimized
python reproduction/webridge/alignment/idiomatic/webridge_gate.py
python reproduction/webridge/alignment/idiomatic/webridge_sweep.py
python reproduction/webridge/alignment/idiomatic/verify_webridge.py
```

Existing recordings and output directories are retained. Fresh reproduction requires a new case/output directory rather than overwriting these artifacts. The wrapper uses the original graph lock and bounded replay supervisor (8g heap, 12GiB sampled RSS, 300s wall, 8GiB output).
