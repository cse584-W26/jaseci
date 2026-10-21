# Jac and WeBridge: TPC-C and littleX

This collection extends the existing SNB comparison to the colleague's two
other workload families. Collection is complete: 648 latency cells and 168
original-schedule references. Accepted measurements pass result and database-state gates.

Start with the [English PDF slides](jac-webridge-tpcc-littlex-comparison.pdf),
[report](REPORT.md), [RTT and SQL-count matrix](results.csv), and
[original-schedule references](rtt-reference-results.csv).

The primary timing metric is **summed SQL round-trip time per request**. See
[`RTT_MEASUREMENT_PLAN.md`](RTT_MEASUREMENT_PLAN.md) for the compact proxy
boundary, sample schedules and primary output paths. The primary table combines
RTT and SQL counts from the same requests. Earlier application timings and
server-only profiles retain their own coverage and measurement definitions.
`rtt-coverage-progress.json` tracks normalized primary latency coverage;
collector status files retain the collection history.

## Workload contracts

TPC-C uses the original seed-42 warehouse fixture and seed-4242 transaction
plan in `reproduction/benchmark/scripts/tpcc_run.py`. The historical run has
100 warmup and 800 measured transactions: 487 successful NewOrder, 406
Payment and seven invalid-item rollbacks across both windows. NewOrder and
Payment-by-ID/by-last-name are retained, including median customer selection,
bad-credit updates, stock changes and atomic rollback. The seven existing
database-truth checks run outside timing.

The complete 900-request plan supplies the correctness and zero-added-delay
reference. The latency matrix separately uses seven original-plan requests:
five- and fifteen-line NewOrder, rollback, and Payment by ID/last name with
good/bad credit. Each latency cell restores the same initial fixture, then
executes ten warmup and thirty measured repetitions. Repetitions retain their
mutations; order IDs, balances and stock values advance on subsequent calls.
Per-request outputs and final state check this progression.

littleX retains the original 100 users and 5,000 follows. Its tiers contain
20/50/100/200 tweets per user. W1 reads the full feed. W2 measures like,
follow and create_tweet. W3 uses the original deterministic paged-feed/write
schedule at 0/5/15/30 percent writes. Existing target selection, result ordering,
write-success and database-delta checks define the workload semantics.

W3's zero-delay reference uses the original 110 warmup and 1,000 measured
requests. Its added-delay matrix uses 110 warmup and 100 measured requests,
retaining a complete original 100-slot schedule in every measured cell.
Per-operation sample counts accompany the mixed latency. W1/W2 added-delay
cells use ten warmup and thirty measured requests, with fresh initial state
per cell and the original deterministic target plan.

## Configurations

Each family compares native Jac original/final and direct/WeBridge pairs for
full access-equivalent Java, pruned Java and conventional relational Java.
The full form is checked against actual native SQL traces. Each pruned form
records its removed operations. Each WeBridge result retains original
record/replay/synthesis/install/activation evidence.

The native source pairs are TPC-C c12 to final32 and littleX historical ad469
CONTROL to final32. `runtime-provenance.json` records exact commits and Jac
source-tree identities. The littleX flags and fixture follow its original
recipe; the TPC-C comparison retains the runtime pair used in the SNB study.

## Collection and analysis

- Use isolated named databases and restore the same initial fixture before
  each mutating correctness or timing run. Capture/compiler activity has its
  own reset; its writes are excluded from timed initial state.
- Save individual inputs, outputs, transaction status, state checks, source
  and fixture hashes, and all executed setup/measurement commands.
- Serialize compilation, live profiling and quiet timing across this batch.
  Each collector uses `measurement_lease.py` for the shared host lease.
- Primary RTT uses compact protocol capture at 0/2/10 ms injected response
  delay. Earlier quiet application timings and detailed SQL/server profiles
  retain separate artifacts and timer definitions.
- Count complete command/response synchronization cycles separately from
  statements executed inside generated procedures. Record commits, rollbacks,
  session commands and return-result operations explicitly.
- Bound slow generated calls; retain elapsed time, connection identity and
  verified server cleanup before starting the next attempt.
- Explain performance using the collected request/SQL/protocol profiles.

`native/`, `tpcc/` and `littlex/` contain the corresponding executable collectors
and raw evidence. The report joins accepted cells and their receipts.

## Independent checks

`METHODS.md` defines the timing boundaries, state oracles and evidence scopes.
`verify_tpcc_model.py` independently evolves the seeded business state from
the request plan. `verify_tpcc_prefetch.py` checks executed PostgreSQL hydration
parameters in 24 raw request traces: both native versions load the five-line
and fifteen-line orders with one combined 10-UUID or 30-UUID batch. This
establishes that the original TPC-C implementation already batches these reads.
The receipt is `tpcc-prefetch-verification.json`.

`aggregate_results.py` checks the 648-cell latency contract.
`collect_cycle_evidence.py` joins measured synchronization evidence with the
compiler stage receipts and checks count distributions against timing rows.
`verify_rtt_results.py` independently rejoins raw compact protocol records,
checks request boundaries, and recomputes request sums, medians and counts.
`verify_result_links.py` checks the public evidence
paths after archiving. `archive_evidence.py` preserves selected raw payloads
with content-addressed gzip objects and relative symbolic links;
`verify_archive.py` verifies their compressed and uncompressed hashes.

## Completed verification

The [public-only raw audit](public-raw-rtt-verification.json) independently
recomputes 630 accepted values from 104,330 measured requests.
[Archive hashes](archive-verification.json), [ordered result streams](chunk-verification.json),
and [report evidence links](result-links-verification.json) pass independently.
[COMPLETION.json](COMPLETION.json) records the final data and PDF hashes.
