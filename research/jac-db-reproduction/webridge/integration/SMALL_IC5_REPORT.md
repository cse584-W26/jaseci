# Jac IC5 and original WeBridge: aligned execution and measured round-trip costs

The IC5 pipeline combines the original native engine and optimizer with the SQL-scope, numeric-width and recorded-JDBC compatibility overlays documented below.

The full Jac-behavior port and its overhead-removal derivative both run through original WeBridge recording, concolic replay, synthesis and an actual stored-procedure invocation on an independently declared, nonempty IC5 diagnostic. Results match the original Jac CPU runtime. On uniform UTF8 UUID storage, warm stored-procedure execution reduces full-baseline SQL round trips from 38 to 4 and the derivative from 31 to 4. Local execution takes about 25–27 ms in both modes. With measured database RTT increased to 2.190 ms, the full baseline takes 118.552 ms versus 35.489 ms for its stored procedure; the derivative takes 101.388 ms versus 34.287 ms.

## Input and behavioral alignment

The diagnostic keeps original input 1's person (`personId=8796093030404`, UUID `6c0eeb86-bda6-5055-b3cf-81a8bf523191`) and raises minDate from 1347062400000 to 1347527525888. Every accepted membership and dependent graph relation therefore belongs to the exact original exported fixture. `../alignment/small-diagnostic/select_input.py` enumerates later membership thresholds and selects a small, nonempty complete execution. The selected execution visits 10 friends, one forum, 15 posts and 15 creator traversals. The output is `[[2061584375281,"Album 7 of Jie Xie",0]]`.

The independently saved input, selection evidence and oracle are under `../alignment/small-diagnostic/`. The original 20-input benchmark remains the primary full-port alignment gate. This diagnostic adds a bounded nonempty engine test with its own manifest.

Actual Jac baseline requests produced 42 cold SQL statements, then 38 and 38 warm statements. The first request's identity statement ran on PostgreSQL backend 2339655; its 41 remaining statements and both warm requests ran on backend 2339678. Compressed protocol logs and the exact backend grouping are in `jac-capture/`. The full Java runtime reproduced 42/38/38 with independent MySQL session Questions counters and identical results.

| Query category per diagnostic request | Full port, cold | Full port, warm | All four overhead removals |
|---|---:|---:|---:|
| Identity/schema lifecycle |4|0|0|
| Object loads |7|7|0|
| Knows, outbound/inbound |2|2|2|
| HasMember |10|10|10|
| ContainerOf |1|1|1|
| HasCreator |15|15|15|
| Transaction/setting/commit |3|3|3|
| Total |42|38|31|

`../alignment/small-diagnostic/verification.json` checks three requests for each implementation. The derivative uses the already validated four-removal source; the same domain loops and per-post creator checks execute in all cases. Its full 20-input cumulative ablations are retained in `../alignment/ablations/20261020T190438Z/`.

## Recorded JDBC compatibility

The real recording of original input 1 contains 6376 rows and 13396 cells. All 322 projected Forum rows store column 3 as Long and column 4 as byte[]. The live MySQL JDBC driver supports decoding the title with getString; the released recorded ResultSet casts that value directly to String.

The isolated `jdbc-string/` overlay adds UTF8 byte-array decoding and numeric string conversion to recorded getString, preserving null/wasNull behavior and the original serialVersionUID. `RecordedTest.java` tests every actual recorded cell and explicit nullable, numeric and Unicode cases. The projected BIGINT identifier uses getLong plus wasNull in the typed adapters. The final 21-request adapter gate passes in `cases/pruned-region-getlong-gate-20261020/`. Request SQL, values, traversal and the original native engine remain the recorded versions.

The overlay is combined with the separately documented SQL frontend and symbolic numeric-width overlays in `jdbc-string/combined/`. `jdbc-string/provenance.json`, `overlay.diff`, and `test.log` retain the exact changes and test evidence.

## Original input1 reaches a concrete implementation size boundary

With the corrected JDBC decoder, the derivative consumes 3,352 cached query results and serializes a valid3406074911-byte native graph. Streaming jq validation succeeds. SHA256 is `70564d8f7d80437d49952afd3b9b403395a569758b924cdbb3ed490d20a02805`.

The native-to-Java whole-string return throws NegativeArraySizeException after 60.364 s, with peak sampled process-group RSS7027486720bytes. Direct synthesis of the retained graph independently fails in 0.828 s with `OutOfMemoryError: Required array size too large` at Files.readAllBytes. Both whole-array interfaces exceed Java's signed32bit length boundary. These are measured implementation limits at graph transfer/loading. The native graph and both errors are retained in `cases/pruned-jdbc-string-idx1-20261020/`; the streaming validation and hash receipts are in `jdbc-string/`.

## Small-input original-engine pipeline

| Variant | Captured body queries | Complete graph bytes | Original replay | Synthesis | Actual CALL/result |
|---|---:|---:|---|---|---|
| Full Jac behavior |35|approximately72MiB|Pass|Pass|Pass|
| Four-removal derivative |28|263210|Pass|Pass|Pass|

The full variant's body includes object loads and ACL/session work; identity/schema setup and transaction commands retain their original outer region. Replay uses the released 100k symbolic-object engine. Heap 8g, sampled process-group RSS12GiB, wall300s and output8GiB bounds are recorded by the supervisor. The final supervisor tests cover timeout cleanup, RSS cleanup and a normal parent exit with a live child.

## Original ASCII UUID storage: measured slow procedure and its cause

On the original schema, actual generated procedures return the correct result while taking24.224s for the full cold request and22.452/22.188/22.159s for three derivative requests. The generated SQL and procedure definitions are retained unchanged in `cases/small-{full,pruned}-webridge-20261020/`.

The anchor UUID columns use ASCII; generated local VARCHAR variables inherit UTF8MB4. A separate same-SQL, same-values control compares literal UUIDs, UTF8 local UUID variables, and ASCII local UUID variables. EXPLAIN shows the UTF8 case applies `convert(e.src using utf8mb4)` and `convert(e.dst using utf8mb4)`, chooses the `kind_type(kind)` index and estimates214695rows per branch. Literal/ASCII-variable cases use `source_type(src)` and `target_type(dst)`, estimating7/6rows.

| Same Knows query control | Handler_read_next delta | CLI wall time, including setup/EXPLAIN |
|---|---:|---:|
| Literal UUID |13|57.7ms|
| UTF8 local UUID variables |601802|832.0ms|
| ASCII local UUID variables |13|48.1ms|

EXPLAIN, results and handler counters are retained under `../alignment/small-diagnostic/plan-{literal,utf8,ascii}/`; `plan-access-summary.json` preserves the relevant plan nodes. The actual slow procedure's Performance Schema events are in `first-sp-pfs.jsonl`. This controlled charset change establishes the index-access cause of the large scan amplification.

## Separate uniform UTF8 storage control

`utf8-clone.sql` creates `jac_alignment_utf8`, copies the original tables, and changes the four UUID columns to UTF8MB4 binary collation. Both ordinary execution and the byte-identical generated stored procedure use this database. The original ASCII database and slow measurements are retained.

Both databases contain 460,984 anchors; the copied UUID/property count-and-CRC aggregate matches990030319858526. Full behavior again matches 42/38/38 SQL statements and the same result. The derivative's timing requests repeatedly verify 31 statements and the same result. Actual stored-procedure hits are checked using both Com_call_procedure and the engine's enabled-at-end flag. The shared storage control restores indexed access: ordinary and stored-procedure execution both report 1443 Handler_read_next operations per request. Other read counters differ: full (key,next,rnd_next) changes from (222,1443,771) to (227,1443,825), and the derivative changes from (193,1443,771) to (194,1443,797).

## Warm timing and RTT intervention

Each run uses one JVM, one connection, a fixed complete input,10warmup requests per phase and 30 measured requests per phase. Status observers execute outside the request timer; their final SHOW is subtracted from Questions. Byte counters include observer traffic and are retained as raw diagnostic fields. Cold activation/setup is separate from measured warm requests. General logging is off; informational runtime logging is disabled for the authoritative quiet runs. Performance Schema configuration stays unchanged. Thread CPU time support/enabled state is saved explicitly in reverse-order and subsequent runs.

| Storage control, database RTT | Full ordinary median | Full SP median | Derivative ordinary median | Derivative SP median |
|---|---:|---:|---:|---:|
| Local, quiet forward order |26.326ms|26.711ms|24.528ms|25.007ms|
| Local, quiet reverse order |25.318ms|28.922ms|24.338ms|26.284ms|
| Added2100us DB egress |118.552ms|35.489ms|101.388ms|34.287ms|

Each cell has 30 measured requests. Full warm Questions is38→4; derivative is31→4. Each optimized request has one actual CALL and correct output. The local results show no acceleration. The RTT intervention makes the saved client/server exchanges visible: incremental median time is approximately92ms versus9ms for the full variant and77ms versus9ms for the derivative.

The delay applies only to the dedicated database network namespace egress. Measured ping mean RTT is0.040ms before,2.190ms during, and0.049ms after restoration. Exact commands, qdisc states, pings, samples and summaries are in `timing/delay2100us/`.

## Independent profiling explains the local result

Instrumented censuses run separately from quiet timing. They retain thread-filtered general logs, nested Performance Schema statements, CPU timers and independent statement counts. `analyze_small_census.py` verifies every request's counted wire queries against its status delta.

| Instrumented warm requests | Ordinary server statement time | SP server statement time | App-thread CPU, quiet forward median |
|---|---:|---:|---:|
| Full behavior |22.090/22.151ms|24.034/24.110ms|3.328ms ordinary /3.563ms SP|
| Derivative |22.136/21.412ms|21.939/21.745ms|2.466ms ordinary /3.334ms SP|

A derivative SP CALL takes 21.610–21.814ms in the census. Its direct children include 988 assignments, 420 conditional jumps, cursor work and 29 statement/sp/stmt events; those events take17.414–17.569ms and have a summed direct-child rows_examined counter of 44281. Full SP CALLs take23.881–23.960ms; their 36 statement/sp/stmt events take17.442–17.530ms and have a summed direct-child rows_examined counter of 44831. Nested times are reported separately from their inclusive parent CALL. Parent CALL rows_examined is zero; the child-counter sums describe recorded statement instrumentation rather than unique physical row accesses.

The final warm derivative CALL separates into24direct table-SELECT events (17.145ms), four cursor-open events including materialization (2.083ms), four returned-result SELECT events (0.099ms), and one final binding SELECT (0.170ms). The full CALL has25direct table-SELECT events (16.980ms), ten cursor opens (2.847ms), ten returned-result SELECTs (0.305ms), and one binding SELECT (0.157ms). These event roles are retained in `sql-role-last-call.json` under each census. They distinguish business-query execution from result transport/control without equating query counts to physical access counts.

The local workload retains substantial SQL execution and stored-procedure interpreter work while saving low-cost local exchanges. The quiet client CPU measurements also show added result-buffer/engine work in SP mode. The independent server measurements and RTT intervention support the observed local parity and delayed-network benefit. Classified events and raw evidence are in `census/small-{full,pruned}-utf8/`.

## Reproduction and final state

`SMALL_IC5_COMMANDS.json` lists the scripts, source/overlay inputs, exact lifecycle commands and evidence directories. Every supervisor attempt retains command, process result and cleanup receipts. `small-final-cleanup/receipt.json` verifies all owned diagnostic database sessions are gone, owned application groups have exited, and the Jac baseline service is stopped. General logging is restored off, Performance Schema settings were read only, and the database network qdisc is restored to noqueue. Both dedicated databases and fixtures remain available for reproduction.
