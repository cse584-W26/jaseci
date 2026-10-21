# Native Jac: TPC-C and littleX

The current primary metric is per-request summed database roundtrip time; see `PRIMARY_RTT.md`, `normalized-rtt-latency.json` and `normalized-rtt-reference.json`. The earlier HTTP and server-phase collections below remain separately retained secondary evidence.

TPC-C runs the unchanged W1 application on a freshly seeded graph of 1,281,535 anchors. The original runtime is c12ba889; final uses the 32c5d1dbb Jac subtree. littleX uses historical ad469 CONTROL and the same final subtree, with the historical application and immutable tier fixtures. Launch receipts identify the checkout commit and verify the referenced Jac subtree separately.

## TPC-C correctness and initial state

Both c12 and final32 passed the original 900-transaction plan: 487 NewOrder commits, 406 Payment commits and 7 real invalid-item rollbacks. Orders increased 487, order lines 4746 and history 406; district next-order consistency and warehouse payment totals passed. Full raw responses and complete before/after logical-state snapshots are retained in `tpcc-gates/{baseline,final}`. All eight relations have identical raw normalized hashes and canonical-cents hashes across the two runtimes, both before and after the 900 transactions; `paired-state-verification.json` records the comparison.

`tpcc-initial-verified.json` independently reconstructs all eight initial logical relations from the original generator JSON and matches every canonical row hash. The Jac HTTP seeder synthesizes History from each Customer with amount 10 and data `seed`; it does not load `history.jsonl`. Carrier NULL becomes 0. Dates and generated UUIDs are retained in raw graph data and excluded from logical-key comparison. Monetary values retain raw precision and additionally have two-decimal canonical snapshots for exact cents equality.

## Actual original SQL

Each of seven original-plan classes starts from an identical initial clone and makes three real, mutating requests. Counts below describe the third request. The raw ordered SQL, bound parameters, backend PID observations and before/after state appear in `tpcc-census`.

| Class | Original plan index | SQL commands |
|---|---:|---:|
| Payment by last name, GC |0|12|
| Invalid-item NewOrder rollback |1|17|
| Payment by ID, GC |3|10|
| NewOrder,5 lines |28|14|
| NewOrder,15 lines |35|14|
| Payment by last name, BC |50|11|
| Payment by ID, BC |54|10|

The compiler already injects one heterogeneous `jobj_many` prefetch before the NewOrder loop. The source is `_prefetch_hint_stmt` in `jac/jaclang/jac0core/passes/impl/pyast_gen_pass.impl.jac`, starting at 2735 in c12. The 5- and 15-line requests each make six generic-anchor loads and two anchor-write batches. The runtime flushes pending writes before subsequent loads; the invalid request also executes two write batches before the transaction rolls back.

The rollback's seventeenth command is PostgreSQL-driver `DEALLOCATE ALL`, following `ROLLBACK`. This is recorded separately as prepared-cache cleanup. The invalid request's HTTP500 response has no server timing headers; its server span remains null, while client wall time and actual database commands are retained.

## Measurement scopes

The original 900-plan correctness/reference run and the representative-class delay sweep are separate datasets. Each representative cell restores the same immutable initial state, repeats one fixed input for 10 warm and 30 measured requests, and retains the full resulting state after 40 actual requests. Quiet transport conditions use the same persistent delay proxy at 0, 2 and 10 ms, with SELECT1 calibration. SQL and protocol tracing use separate instrumented runs.

The common host lease serializes live stages. `launch-history` retains each launch's source/command/environment receipt and server log before working files are reused. The original graph and immutable initial template remain available for reruns.

The representative sweep completed all 42 cells, comprising 420 warmup and 1260 measured requests. `tpcc-timing/independent-repeat-state-verification.json` independently verifies every output and all eight final relations against seven original-source 40-request simulations, and rehashes all retained state payloads. The quiet records retain their observed latency variations.

## Payment commit-span diagnostic

A separate four-cell, 2 ms instrumented experiment repeats Payment by ID for GC and BC customers, with 10 warmup and 30 measured requests per runtime/class. `tpcc-outlier-diagnostic/analysis.json` contains each request's SQL, protocol, header and counter components. All 120 requests have ten SQL commands and ten actual complete-response synchronization flights, certified from matching SQL/backend PIDs and delivery timestamps. Every next frontend exchange begins after the previous complete reply is delivered.

| Runtime / customer | Server median ms | Header commit-span median ms | PostgreSQL COMMIT median ms | Anchor upsert median ms |
|---|---:|---:|---:|---:|
| Original / GC |55.436|26.975|13.467|0.217|
| Original / BC |35.733|11.627|1.288|0.250|
| Final / GC |42.881|11.349|1.566|0.253|
| Final / BC |41.269|12.412|1.620|0.318|

The reproduced slow original-GC commit span includes measured PostgreSQL COMMIT execution. Across the four cells, the median per-request residual after subtracting the three observed flush/registry/COMMIT wire flights from the header commit span is 1.06–1.46 ms. Accepted proxy TCP sockets have TCP_NODELAY=1; the upstream connection uses a Unix socket. Measured median backend-receive-to-delivery hold is 2.245–2.250 ms. The proxy does not observe the libpq client's socket option.

A checkpoint completes during original-GC request29, reporting 8.969 seconds of synchronization accumulated over the checkpoint. This overlapping event identifies a measurement for further inspection; its cumulative time includes work started before the request interval. The diagnostic is separately instrumented and its medians remain distinct from the quiet matrix. Category medians are not added to reconstruct a request median.

## littleX preparation

`timing_littlex.py` consumes the frozen original schedules and TargetPlan inputs. W1 uses `load_feed_chain`; W3 uses the historical `load_feed_page` route. `littlex_oracle.py` checks every returned Tweet field and ordering, evolving likes/follows/creates, and the complete final Profile/Follow/Tweet/Post business state. Generated UUIDs are mapped through Tweet seed IDs and freshly generated timestamps are normalized only for comparisons across separate runs. Raw responses retain their actual values. `littlex-oracle-offline-verification.json` records 48 successful independent checks against captured native census responses, including the corrected historical paged route.

## Actual synchronization flights

The complete protocol collection covers all seven classes, both runtimes and0/2 ms conditions (28 arms,84 measured requests), with ten warmup and three measured requests per class. `protocol-summary.json` is the machine-readable collection index. Generic Payment has ten SQL commands and ten observed flights; name-GC has12/12, name-BC11/11, and both NewOrder sizes14/14. Invalid NewOrder has17 SQL commands and18 actual flights in all three repetitions. Its extra exchange is a Parse+Sync preparing the full-anchor SELECT, answered by ParseComplete+ReadyForQuery before the later Bind/Execute exchange begins. ROLLBACK and driver DEALLOCATEALL remain separate, later SQL exchanges. Counts distinguish actual SQL execution, prepared-statement setup, protocol messages, network chunks and complete-response barriers.

The extended Java “full” arm denotes the observed warm-access translation. Its lifecycle ledger separately identifies native schema/memo guards and JDBC transaction controls. Native memo consultation can issue a real catalog-validity query at the default five-second TTL (`store.impl.jac`, `_memo_ttl`). Tables report the actual instrumented count distributions for their measured conditions; quiet10 ms request counts retain that lifecycle context rather than inheriting a fixed count from a short census.

The earlier secondary application-latency table uses native HTTP client wall time consistently, including rollback responses. JSON also retains the secondary server total+commit span. That header is a framework timer computed from its function span and accumulated commit/serialization fields. Captured SQL exchanges can fall outside that header boundary; the primary database RTT is measured independently across every tagged request connection. Java arms time the application method call. Native original→final comparisons retain the same HTTP boundary, while cross-system rows retain their explicitly different application-entry boundaries.

## WAL timing and wait-event diagnostic

`tpcc-wal-diagnostic/WAL-analysis.json` covers a separate original-runtime GC/BC Payment-by-ID experiment at 2 ms, with 10 warmup and 30 measured requests per class. Database-scoped `track_wal_io_timing` was enabled and restored to its exact prior setting. Both classes executed ten SQL commands and ten delivered-response flights per measured request. PostgreSQL COMMIT medians were 1.689 ms for GC and 1.626 ms for BC. Sampling the traced application backend observed 23 COMMIT samples in `IO/WalSync` in each class; GC also had one `IO/WalWrite` sample. Client-backend WAL counters increased by approximately 56 ms of fsync time across 35 fsyncs in each measured-to-shutdown interval. These samples identify the observed wait; their frequency is occupancy sampled at approximately 2 ms, rather than an exact per-request duration. The larger COMMIT latency in the earlier outlier diagnostic did not recur in this probe.

## Measured ten-millisecond lifecycle context

`tpcc-ttl-diagnostic/count-distribution.json` retains 60 measured NewOrder15 requests after ten warmups for each runtime at 10 ms injected delay. Every measured request executed 14 SQL commands and 14 actual complete-response flights, across a run lasting more than the default five-second memo TTL. This class exhibited no additional periodic query in the observed interval. Native lifecycle behavior remains an explicit source/runtime property, while count tables retain their actual measured class and condition.

## littleX pilot

`littlex-pilot-like/independent-offline-verification.json` verifies both original and final LIKE pilots against the independent result and full-state oracle. Each runtime has ten warmups and three instrumented measured requests on a fresh t20 fixture. `certified-requests.json` certifies all six measured requests using actual PostgreSQL messages, executed SQL and delivered-response barriers. The quiet tier matrices and original-reference schedules use separate collection directories.

The t20 quiet matrix has24 accepted cells, each independently rechecked against every raw response and the full final business state (`littlex-timing-t20/independent-offline-verification.json`). `littlex-like-alignment.json` identifies the actual input-dependent owner fast path: the first measured LIKE targets its own actor’s Tweet, avoiding one owner-root hydration; the following two nonowner inputs execute the larger count. Actual original counts are10,11,11 and final counts9,10,10 in that instrumented pilot.

## littleX all-connection protocol scope

`littlex-cycle-evidence.json` now covers every W1/W2 tier directly at 2 ms, with three measured requests after the frozen ten-request warmup. The t20 LIKE pilot additionally covers 0 ms. `littlex-all-connection-scope-verification.json` matches all executed SQL records across every backend PID against the tagged wire trace; all 902 current request windows pass. The earlier census reported graph-store PID counts. Its two guest-identity queries execute on a separate connection and are present in the retained raw log: original feed16 graph commands plus two guest lookups become18 actual flights in the current warmed profile; final12 plus two become14. Earlier requests also contain an initial authentication lookup before graph execution, retained separately in the scope ledger.

For the current measured source requests, W1 feed counts are original18/final14 at t20/t50; t100 has18,19,18 versus14,15,14, and t200 has18,18,18 versus14,15,14. The extra command is the runtime memo-validity guard, which checks the named Profile/Tweet projection tables with to_regclass. The exact source and derived-category correction are retained in sql-category-correction.json. FOLLOW is12→11 and CREATE9→8 at every tier. LIKE is10–11→9–10, reflecting the proven target-owner alias branch. Each reported command corresponds to a separately delivered complete PostgreSQL response. Source categories, SQL IDs, per-backend counts, protocol messages and chunk counts remain separate observations.

The common four-command read reduction removes one SERIALIZABLE BEGIN/SET/COMMIT sequence and the eager global-root hydration. The final runtime defers actor-root initialization into the read-only walker transaction. The three projected graph traversals, two ancestry queries, root-permission probes and guest-identity lookups remain separately emitted. This mechanism is runtime context deferral; the original application already uses projected graph queries.

## Earlier completed HTTP-wall matrix

`normalized-latency.json` contains all162 accepted native cells:42 TPC-C and120 littleX cells across0/2/10 ms injected-response-delay conditions. There are6,540 measured HTTP requests after4,020 warmup requests. Each TPC-C representative cell has10 warmups and30 measured requests; each littleX W1/W2 cell has10 and30, and each W3 cell has110 and100. Every cell uses a fresh source fixture, retains every raw response, and passes the corresponding complete final-state oracle. Main medians consistently use native HTTP client wall time, with server total+commit spans retained separately.

The original schedules are collected independently in `normalized-reference.json`: native TPC-C has100 warmups plus800 measured requests per runtime; littleX references use110 warmups plus500 measured requests for W1/W2 and110 plus1,000 for W3. Their artifacts and request/state gates remain separate from the RTT matrix.

## Complete W3 schedule protocol evidence

`littlex-profiles-mixes/certified-requests.json` certifies all 800 measured requests: the complete original 100-slot W3 cycle for each of four mixes and both runtimes, after110 warmups at2 ms. The all-read mix executes18–19 original flights versus14–15 final flights; the mixed schedules span9–19 versus8–15 according to the executed operation and memo guard. Every request retains its logical operation, SQL category/ID sequence, per-backend counts and complete delivered-response barriers in `littlex-cycle-evidence.json`. These distributions are measured full schedules, rather than extrapolations from three read samples.

## Original references and final evidence inventory

`normalized-reference.json` contains all42 accepted native references: the two original900-request TPC-C schedules and40 littleX source-reference cells. They retain30,200 requests:4,600 warmups and25,600 measured requests. Each littleX W1/W2 reference has110 warmups plus500 measured requests; each W3 reference has110 plus1,000. Every response passes the source oracle, and every cell passes the complete final business-state check. The corresponding source request plans and state hashes remain separate from the162 earlier HTTP-wall matrix cells.

The initial t200 reference attempt reached a launcher shutdown timeout after collecting its first feed. It remains excluded, with all610 raw responses retained as lossless chunks and the cleanup receipt in `littlex-reference-t200/`. The fresh `littlex-reference-t200-retry/` group passed all eight cells. The shutdown launcher now verifies the owned process and exact database-session absence inside the measurement lease; its cleanup-only change and actual source SHA are preserved in the retry source receipts. `cleanup/littlex-service-stops.json` consolidates retained stop proofs.

`littlex-completion-controller-resume-t200/progress.json` records the successful remaining-stage controller. `PUBLIC_FILES.json` selects the portable evidence, including bounded response chunks, payload-free compressed protocol events, source snapshots, state oracles and exact restoration receipts. The strict inventory contains no selected file larger than90 MiB. Private authentication material and raw anchor exports remain outside the public selection.

## Completed primary database-roundtrip collection

`normalized-rtt-latency.json` contains all162 accepted primary cells:42 TPC-C and120 littleX, with6,540 measured requests after4,020 warmups. `normalized-rtt-reference.json` contains all42 original references, with25,600 measured requests after4,600 warmups. Each median is computed from the per-request sum of actual complete database exchanges across all application connections. Prepare-only/control exchanges contribute RTT and exchange counts, separately from executed SQL counts. Every distribution and median uses the same recorded requests.

`PRIMARY_RTT.md` defines the exact clock boundaries and raw join. Each normalized row links its request records, compact flights, SQL catalog, connection-byte receipt and completeness receipt. Response/full-state gates, original plans, source snapshots and restoration records are retained per collection. `primary-rtt-completion/completion.json` indexes the actual owned-process/database-session shutdown proofs. Large full-feed responses use verified lossless chunks.

The first W3 finalizer encountered previously uncategorized warmup schema-setup statements after its response and state gates passed. `classifier-history/w3-warmup-classification.json` preserves the classifier snapshots and hashes; the failed derived-verification receipt remains beside the collection. The remaining-only controller verified the existing raw pair and skipped all already accepted keys. Collection timestamps, SQL counts, roundtrip values and workload inputs were preserved.
