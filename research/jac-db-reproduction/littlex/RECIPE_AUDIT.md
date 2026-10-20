# Complete littleX recipe audit

Sources: `session0904/final_runner.sh`, `night0823/p1r2_runner.sh`,
`harness/scripts/91-night-run.sh`, `harness/scripts/lib.sh`,
`harness/profiling/start_pg.sh`, and the original Python drivers.

## Matched request and data definitions

-100users,50initialfollows/user; tiers20/50/100/200tweets per user.
- Original seed generator, tweet pool, epoch, IDs and deterministic random seed42.
- W1: uncapped Jac `load_feed_chain` versus SQL `/feed`,500timed+110warm.
- W2: each original write driver's500timed+110warm, same target planner.
- W3: original100-slot deterministic request schedule,1000timed+110warm,
  fractions0/5/15/30 and `/feed_page`/`load_feed_page`.
- Both arms use the original driver definitions of client latency and server
  span. Both raw request timings and summarized statistics are retained.
- Original HTTP driver loop is sequential. No driver taskset occurs in the
  final_runner→p1r2/91-night-run→hrun chain. The14-19setting in
  `65-bench-plot.sh` belongs to a different entry point.
- Jac PG_DRIVER/pool/ensure/measurement switches match the original effective
  configuration, with final runtime defaults documented in `ENV_REVIEW.md`.
- SQL Docker PostgreSQL16/TCP, cpuset0-1 and2GB memory budget follow compose.
- App and driver use their separate original frozen locks on Python3.13.

## Fresh-cell comparison configuration changes

| Dimension | Historical recipe | Current collection |
|---|---|---|
| Jac runtime | ad469c988 CONTROL |32c5d1dbb final defaults,LAZY_TXN on |
| Baseline Python | project selects3.13,exactminor not recorded | PBS3.13.16 with archive/binary hashes |
| Jac interpreter | historical sealed runtime | PBS3.14.6 source launcher |
| App source | before b94e08e | b94e08e+,only unused leaf walker removed |
| SQL app affinity | taskset6-13 | initial40-cell pass unpinned; corrected SQL rerun6-13 |
| Jac app affinity | no taskset | no taskset |
| Driver affinity | no taskset | no taskset,same for both arms |
| Seeding | original HTTP per Jac cohort | same HTTP seed once,tier-specific template restores |
| W1/W3 server setup | Jac fresh per tier/fraction;SQL can persist | fresh process per cell on both arms |
| W2 reset | one reset per(tier,arm),like→follow→create_tweet shares state | independent fresh reset and process per operation |
| W2 operation order |like→follow→create_tweet |create_tweet→follow→like |
| Untimed correctness | count/delta checks | count+100-user seed-derived feed/page check before110warm |
| Phase order |SQL W2→W3→W1;Jac wrapperW3→W1→W2 |W1→W2→W3,arms paired per tier |

W2's original code resets before its operation loop, despite comments in
`p1r2_runner.sh` describing per-op reseeds. Therefore later operations
observe earlier writes. That state-sharing difference is kept explicit.

## Primary original-recipe collection

The completed final-defaults fresh-cell40 remains a separate comparison.
`original_recipe.py` produces the primary40-cell historical reproduction:

- Actual Jac sourcead469c988 and historical CONTROL flags.
- Exact pre-retirement app89366720 and main module from DBHarness982e4f3.
- SQL: one server pinned6-13, originalW2→W3→W1 and cohort resets.
- Jac:12fresh cohort processes, originalW3→W1→W2.
- W2: one tier reset, thenlike→follow→create_tweet sharing state/process.
- Original110warm and500/1000timed requests.
- Historical100-user full/page prevalidation occurs separately; a fresh
  template restore follows it before the measured cohort begins.
- Actual server/driver affinity, source/app/binary hashes, dependency
  provenance, DB count transitions and every operation's timing are recorded.

Independent `aggregate_original.py` checks40cells,24cohorts,SQL1PID,Jac12PID,
operation/phase order, shared-state transitions, sample counts, errors,
write oracles, historical source/app identity and CONTROL flags.
Performance deviations are investigated through SQL-duration/CPU profiling
and isolated runtime/configuration controls.
