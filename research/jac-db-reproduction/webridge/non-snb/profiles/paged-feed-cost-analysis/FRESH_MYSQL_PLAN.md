> Historical server-only proposal; superseded by FRESH_RTT_PLAN.md. No server-only long batch was launched.

# Fresh zero-delay MySQL DB-server measurement plan

Goal: compare direct Java with its WeBridge path using MySQL server statement timers. PostgreSQL original/final uses the native owner's separately verified server-phase collector. Each engine supplies its own within-engine ratio.

## First pilot

- Exact workload: `littlex-feed-t20`, conventional `LittleXSql`, direct and accepted SP.
- Fresh identical fixture for each phase; 10 mutating warmup requests and 30 measured requests.
- Direct JDBC to local MySQL port 55337. No byte proxy, packet logger, added response delay, SQL general log or SDK DEBUG logging.
- Frozen current source/classes, charset initialization and accepted bundle from the final-init source. Record all hashes and effective session settings. Preserve the source request, its complete result consumption and output/state oracles.
- One exclusive shared host lease for reset, both request phases, capture and committed-state verification. Application affinity remains CPUs 9,19. A compiler-only preparation stage acquires its own short lease first.

## Server timer and capture

1. Snapshot exact P_S instruments/consumers, history capacity, global logging settings and the initial connection environment. Enable timed `statement/sql/%` and statement history-long collection. Disable nested `statement/sp/%` instrumentation for this primary series; the outer CALL timer already includes stored-program work and waits. Restore the exact prior settings in `finally`.
2. Start capture before the JDBC connection is created. The harness retains its existing before/after `SHOW SESSION STATUS` counter boundaries. A collector-only readiness/release handshake is inserted after the request loop and before connection close, outside every application request. This lets the collector read the live thread summary before it disappears.
3. Prefer **no observer polling during the measured request loop**. Warm+measured top-level statement counts are bounded well below the existing 10,000-event history capacity (roughly 800 for a 40-request full graph feed or 4,200 for a 210-slot mixed schedule). The post-loop readiness handshake provides a quiescent capture point. All ordinary foreground SQL names, including observer-boundary SHOW STATUS events, are checked against the live per-thread summary counts. Connection identity, raw events and all summary counters are retained.
4. Sort top-level foreground P_S events by EVENT_ID. Partition by the actual request SHOW STATUS event pairs; exclude those observer statements. Verify the number of SQL events in every request against its independent Questions delta, and CALL count against Com_call_procedure. Collect complete JDBC results and verify request completion; no early result truncation/drain shortcut is introduced.
5. Per-request **DB server time = sum(TIMER_WAIT) over outer foreground SQL events**. A CALL contributes its inclusive timer once. Nested statements are never added to this total. This contains server CPU, I/O, locking and server-side waits; it excludes client work between statements and proxy/packet timing.
6. If captured counts do not exactly match every relevant live foreground event-name counter, or any request boundary is missing, reject the capture as incomplete. History overflow never produces an accepted time. Save the failure and rerun in smaller independently reset windows if necessary. No buffer-resizing experiment is needed for the pilot.
7. A separate optional attribution pass can enable nested SQL instrumentation, with separate output/scope. Its child business SELECT and transaction-control timings explain the inclusive CALL; they are not added to it and do not replace the low-overhead primary timer.
8. Existing owned request watchdogs apply. On a bounded timeout, verify and stop only the owned connection/process group, preserve the attempt, prove absence before the next phase, and restore P_S settings.

## Correctness and result fields

- Retain the exact plan, full returned results/hash/chunks, before/after business state, actual per-request CALLs, fallback/region flags and effective charset/mode.
- Run the independent littleX model on every completed phase; direct/SP equality is additional evidence. Quarantine the newly failing Pruned mixed emoji baseline and its paired SP until the owner supplies a passing encoding/state gate.
- Report `actual_n`, median of per-request DB sums, min/max/raw samples, foreground SQL count distribution, actual CALL/fallback counts, engine, P_S source hashes and state/model receipts.
- Direct business SELECT/transaction timers are available from the primary events. SP internals are only available in the separately instrumented attribution pass; keep those columns explicitly unavailable in the low-overhead primary table rather than reuse old-profile child times.

## Proposed CLI after implementing the collector

These commands specify the intended interface; the fresh collector has not yet been implemented or run.

```sh
python profiles/paged-feed-cost-analysis/fresh_mysql_db.py pilot --case littlex-feed-t20 --implementation LittleXSql --warm 10 --measure 30 --phases baseline sp --out NEW_PILOT_DIR
python profiles/paged-feed-cost-analysis/fresh_mysql_db.py batch --case-manifest APPROVED_20_CASES --arms java_full webridge_full java_pruned webridge_pruned java_conventional webridge_conventional --out NEW_BATCH_DIR
```

The implementation should reuse `littlex/timing_command.py` and the owner's fixture/reset/model helpers, with a separately frozen measurement-harness handshake overlay. No business Java class, SQL or generated procedure changes are required.

## Staging and estimated cost

- Pilot: budget 2–5 minutes including JVM preparation, two resets, 80 requests and full result/state validation. The ordinary request phase is seconds; reset/oracle cost is retained separately. This is a planning budget, not a measured result.
- Review pilot completeness, exact state/model gates and per-query timer scope before scheduling more work.
- Full coverage: 20 cases × 6 Java/WeBridge arms = 120 terminal entries. Actual compiler-stage failures are linked, not executed as pretend SP timings. Accepted runtime paths retain real fallback. Collect one exact case/direct-SP pair per short host lease, yielding between pairs so native work can interleave.
- Budget roughly 0.5–2 minutes per runnable configuration including setup/oracles; a full batch can take 1–3 hours depending on how many generated paths are runnable and mixed result-export cost. Refine from the pilot and first mixed group; do not start the long batch before root scheduling approval.
