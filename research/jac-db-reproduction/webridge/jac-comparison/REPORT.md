# Jac and WeBridge on a matched IC5 diagnostic

Jac's final compiler/runtime executes the same nonempty IC5 request in a median 4.523 ms of server time, compared with 22.2975 ms for the original Jac baseline: 4.93× faster on the same PostgreSQL fixture and HTTP stack. Warm SQL statements fall from 38 to 14. The final SQL batches membership traversal and replaces the per-forum/per-post counting loop with a member-driven aggregation.

## Measured local comparison

| Implementation | Request median | HTTP client median | Warm client-issued SQL statements |
|---|---:|---:|---:|
| Original Jac, PostgreSQL |22.298ms server|23.251ms|38|
| Final Jac SQL pushdown, PostgreSQL |4.523ms server|5.408ms|14|
| Full-behavior Java port, MySQL UTF8 |26.326ms CLI|—|38|
| Full-behavior port plus WeBridge, MySQL UTF8 |26.711ms CLI|—|4|
| Four-removal Java derivative, MySQL UTF8 |24.528ms CLI|—|31|
| Derivative plus WeBridge, MySQL UTF8 |25.007ms CLI|—|4|

Each row has 30 measured requests after 10 warmup requests; all results match the declared oracle. Java/WeBridge rows use the quiet forward-order runs from `../integration/timing/`. Reverse-order Java runs and the separately measured2.190ms database RTT experiment remain in [the WeBridge report](../integration/SMALL_IC5_REPORT.md).

The 4.93× ratio compares Jac variants within one database engine, fixture, CPU affinity, application source and HTTP entry point. The cross-system table compares complete implementations using different database engines, drivers and runtime representations. It exposes their measured behavior; the cross-database absolute differences combine those system choices.

## Matched logical data and input

The independently selected input keeps original benchmark input1's person and raises minDate to 1347527525888. It visits 10 friends, one forum, 15 posts and 15 creator traversals; its output is `[[2061584375281,"Album 7 of Jie Xie",0]]`. The original20-input collection is preserved separately.

PostgreSQL database `jac_webridge_matched_20261020` contains the same 460984 UUID anchors and 300901 edges as the exported MySQL fixture. The 13 business fields round-trip through UUID-sorted COPY with the same SHA256; every endpoint and owner-root reference resolves. `fixture/` retains the source catalog, source DDL, indexes, load script and verification manifest. The PostgreSQL fixture also copies the source identity tables needed by HTTP authentication; the Java port uses the same declared service account. The count alignment below validates the exercised request behavior.

The PostgreSQL source schema includes runtime mirror/adjacency tables. After baseline validation, `provision.py` invokes the runtime's canonical ensure methods to backfill the final runtime's mirrors, endpoints and adjacency indexes, then ANALYZE refreshes statistics. `provision/` retains all methods, results and elapsed times. These auxiliary structures belong to the final runtime's execution strategy; the shared anchor graph remains fixed.

## Actual SQL counts and correctness

| Actual request sequence | Original Jac | Final Jac |
|---|---:|---:|
| First process/request, including cold checks |42|30|
| Next request |38|14|
| Next request |38|14|

The baseline's42/38/38 exactly matches the full Java port on the same input. Its cold identity statement runs on backend2452740; the remaining41statements and both warm requests run on backend2452779. Final warm requests run on backend2456289. Its first request includes additional canonical readiness work on auxiliary connections, identified separately in `census/final/rows.json`.

Censuses are separate instrumented runs. Every request stores compressed protocol logs, executed statements grouped by backend PID, and parse/bind/execute/statement duration summaries. Database-scoped duration logging is restored afterward. Timing runs disable statement-duration logging. [Independent verification](independent-verification.json) checks all 80 timing requests, expected results, status codes, warmup separation, header formulas and restoration receipts.

## Confirmed final execution mechanism

The application remains `ic5_new_forums` from the original benchmark. Baseline source is `c12ba889d484d7fcdfb3780ac98d416d1e13ec8b`; final source is `32c5d1dbb9507571235783e78e35b1022cacc4e4`. Per-run launch/source receipts and copied JIR bundles under `compiled/` identify the executed code and caches.

The actual warm final request emits a SQL expression with:

- `pr(k,m)`: qualifying forum/friend pairs;
- `fp`: HasCreator edges restricted to the qualifying members;
- `fc`: ContainerOf edges joined to those posts;
- `cnt`: grouped per-forum counts;
- a forum mirror join, ordering and LIMIT.

`final-aggregation.sql.log` retains the complete actual statement and its 0.221 ms execute duration in the warm census. The compiler batches the HasMember frontier and hydrates the winning forums. The original Java port and WeBridge preserve the business traversal loops; WeBridge moves their query sequence into one CALL. These mechanisms change different parts of execution: actual business SQL work versus client/server exchanges. SQL round-trip count alone therefore does not determine elapsed time.

## Timing boundary and CPU

The primary Jac metric is:

`server_ms = x-server-total-ms + x-server-commit-ms`

The request timer starts after JWT validation and before identity/root request-context initialization. The total header excludes commit and serializer time; adding commit yields approximately the whole application request minus result serialization. Argument deserialization, worker dispatch, walker execution and transaction completion remain inside that boundary. Raw headers are saved on every sample. HTTP client time is reported separately.

Java CLI timing wraps `request(connection,input)`, including identity/root setup when required, traversal and commit; result JSON serialization happens afterward. Its boundary is similar to Jac server+commit time, while their runtime stacks and database engines differ. Source anchors are `jaclang/runtimelib/impl/server.impl.jac` (`_run_function_with_occ` and `_server_total_ms`) and the original `benchmark/scripts/bench_timed.py` (`issue_snb`).

Measured Jac process CPU across the complete 30-request measured interval is 180 ms for baseline and 80 ms for final: 6.000 ms and 2.667 ms per request. `/proc` counters have 10 ms tick resolution; interval totals provide the CPU summary. Per-request CPU ticks remain raw diagnostic fields, and the interval includes inter-request application housekeeping. Java's retained CPU samples use ThreadMXBean, a different scope.

## Configuration and reproducibility

`service.py` creates isolated copies of the same application files, selects the exact source variant, binds the explicit matched database and uses affinity 9,19. Existing runtime flags, CPython 3.14 runtime and LLVM shim match the reproduction. Each variant has its own copied application/cache directory.

The released `conninfo_from_url` ignores URL query parameters and defaults to a TCP host. The native PostgreSQL instance listens on a Unix socket. `connection_shim.py` supplies only the declared `?host=/tmp/jacpg-d6275e76eb` as `ConnInfo.unix_socket_dir`, identically for both variants. Connection routing is adapted at launch; SQL, application code and compiler/runtime source files retain their recorded versions. The initial configuration failure and restoration are preserved in `census/baseline-configuration-attempt/`.

Commands, from `/home/baichuan/jaseci`:

```text
reproduction/runtime/venv314/bin/python reproduction/webridge/jac-comparison/run.py --variant baseline --mode census --out <fresh-output>
reproduction/runtime/venv314/bin/python reproduction/webridge/jac-comparison/run.py --variant baseline --mode timing --out <fresh-output>
reproduction/runtime/venv314/bin/python reproduction/webridge/jac-comparison/provision.py --database jac_webridge_matched_20261020 --variant final --execute
# ANALYZE is recorded in provision/analyze.json.
reproduction/runtime/venv314/bin/python reproduction/webridge/jac-comparison/run.py --variant final --mode census --out <fresh-output>
reproduction/runtime/venv314/bin/python reproduction/webridge/jac-comparison/run.py --variant final --mode timing --out <fresh-output>
```

`summary.json` records medians, counts and CPU. `cleanup.json` verifies both application services have stopped, all request-owned PostgreSQL backend PIDs have exited and database logging settings are restored. The matched fixture remains available for reproduction. Native Unix-socket transport uses the original network configuration.

The subsequent matched transport sweep is documented in [latency/REPORT.md](latency/REPORT.md). Its explicit TCP-target options extend the launcher; original direct-run source snapshots are retained in `latency/source-before-tcp/`.
