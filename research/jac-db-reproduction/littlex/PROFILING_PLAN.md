# littleX diagnostic plan after the formal matrix

Goal: measure where the current W1/W3 latency is spent, then compare only
historical measurements with matching stage definitions. Perform diagnostics
in separate output directories after the formal matrix; retain formal results
as the headline timing dataset.

## Existing instrumentation to use first

The runtime already supports `JAC_STAGE_HEADERS=1` at process startup:

| Header | Definition |
|---|---|
| dispatch | HTTP dispatch arrival to walker span entry |
| auth | token/user/root resolution, including its DB work |
| prep | request setup to first chargeable data query |
| db | sum of PgStore._run driver execute+fetch wall durations during data phase |
| build | remaining walker/run wall time after first data query, excluding db and commit |
| commit | flush and commit |
| ser | Serializer.serialize sub-timer, already contained within build |

`db` includes more than PostgreSQL execute time; it covers driver and waiting
inside the runtime call. `build` is a wall-time residual, not CPU time. `ser`
should not be added to the other stages again. The timing boundaries are reconciled per request below. Preserve all raw stage and server timing headers.

Sources: `jac-db/jac/jaclang/runtimelib/stagetimer.py`,
`runtimelib/impl/server.impl.jac`, `runtimelib/serving/app.jac`.
No request-scoped cProfile/perf hook was found. `JAC_PROFILE` and `--profile`
choose configuration profiles, not performance profiling.

## Exact server/headline reconciliation

`_run_function_with_occ` computes `_whole_ms` then emits:

```text
x-server-total-ms  = max(whole - ctx_commit - ctx_ser, 0)
x-server-commit-ms = ctx_commit
x-server-ser-ms    = ctx_ser
original driver headline = x-server-total-ms + x-server-commit-ms
                         ≈ whole - ctx_ser
```

Stage timing starts/finishes at adjacent marks, so define
`stage_sum = auth + prep + db + build + commit`. It includes serialization
inside build. The per-request check is therefore:

```text
stage_sum - x-server-ser-ms ≈ original driver headline
stage_sum - original driver headline ≈ x-server-ser-ms
```

Use x-server-ser-ms for this check; x-stg-ser-ms is a nearby diagnostic timer
around the same serializer region and can differ slightly. Dispatch is outside
the walker span. Finish/readout overhead and millisecond rounding also produce
small residuals. The profiling helper's recorded stage_sum_minus_server_ms
being close to serializer time is expected, not a missing stage.

Sources: `_finalize_call_response`, server.impl.jac:418–430;
`_run_function_with_occ`, server.impl.jac:479–488;
`stagetimer.finish`, stagetimer.py:113–136;
`harness/run.py:_jac_walker`, lines58–65.

## Diagnostic cells and fixture control

Measure W1 t20 and t200 using the active `load_feed_chain` endpoint. For W3,
use the existing mix schedule, feed_page walker, write fractions, target plan,
and oracle from mix_run.py/write_run.py. The current default W3 route is `load_feed_page`: mix_run.py uses
`FEED_WALKER` with that default, and the original wrapper leaves it unset.
`load_feed_page_chain` is a separately selectable comparison route.
Original formal W3 is t200; any t20
mix diagnostic must be labeled a diagnostic extension, not an original matrix
cell. Start with the representative existing W=15 mix, and expand to other
fractions only when the observed phase differences require it.

Restore the audited fixture before every write diagnostic; use the original
warmup-plus-timed sequence in the same driver invocation. A separate write
warmup process resets target pointers and may replay already consumed writes.
Record tier, fixture hash, token-map hash, app/source hash, request sequence,
write fraction, runtime flags, result hash/oracle delta and backend identities.
Reuse the current runner's fixture mechanism; do not invoke historical reseed
scripts against the running reproduction.

## Pass A: existing stage headers

Restart only the diagnostic app with its existing flags plus
JAC_STAGE_HEADERS=1. Keep PostgreSQL duration logging disabled for this pass.
Use original run.py/mix_run.py request helpers; a separate diagnostic wrapper
can add an httpx response event hook to capture x-stg-* and x-server-* headers
without editing existing drivers or app code. Record request index, user,
operation, warm/timed phase, client duration and raw headers.

For W1,20 warm requests plus100 measured requests suffice for an initial stage
profile, with the original deterministic user sequence. For W3 preserve the
original mix and warmup semantics; retain per-op stage rows and write oracle.
Report stage means and medians by cell/op plus missing-header/error counts.
Do not sum marginal stage medians as if they equal the median whole request;
check the algebra per request and compare aggregate means when additive
reconciliation is needed.

## Pass B: PostgreSQL protocol and process CPU

Use a separate restored/appropriately warmed diagnostic cell. Reuse the
profile_ic5_full.py approach, parameterized for littleX's app PID, explicit DB,
HTTP requests and original token/user/op schedule:

- Verify the dedicated postmaster.opts and backend ancestry.
- Discover existing client backends once from the postgres monitoring DB after
  warmup, then close monitoring before measured calls.
- Sample Jac process and discovered PostgreSQL backend CPU ticks separately.
- Record full SQL log windows and parse/bind/execute/simple-statement sums and
  counts. Keep identity and main data backend events, including auth before
  BEGIN. Report any new/untracked backend PID.
- W3 uses write transactions and background maintenance may run; retain PID
  attribution and label autovacuum/parallel workers separately from sampled
  client backend CPU. Preserve write-oracle checks.
- CPU tick resolution is10ms: small W1 requests require aggregate CPU across
  enough sequential calls, not a claim that a single0-tick delta means0 CPU.
- Stage DB wall time, protocol wall time, app CPU and DB CPU are different
  measurements. Their differences are not automatically network time.

Enable duration logging only for this diagnostic pass and restore the saved
settings afterwards. Record the overhead-bearing diagnostic separately from
formal timing. Avoid parallel workload activity.

## Pass C: function-level CPU only if A/B require it

Existing facilities are harness/profiling/profile_unit.sh, profile_run.py,
sample_pass.sh and buckets.py. They use py-spy speedscope or dump-loop captures.
The historical script contains old absolute paths, server kills and reseeds;
reuse the sampling/parser method, not the shell script wholesale.

A second pitfall: historical profile_run.py's feed operation selects
load_feed_leaf, whereas the active W1 selects load_feed_chain. Preserve the
active driver endpoint rather than adopting that historical default.

Prefer a separate py-spy CPU-oriented capture (GIL/active samples) alongside
an explicitly labeled waiting-stack capture; do not equate waiting stacks
with transport time. Old notes report the Zig binary could not keep up under
closed-loop py-spy record; paced sampling was usable, but pacing is itself a
separate diagnostic traffic pattern.

If deterministic cProfile is needed, a diagnostic-only launcher must profile
inside the actual walker worker thread. ExecutionManager.spawn_walker_sync
calls asyncio.to_thread(Jac.spawn, walker, target_node) at
runtimelib/impl/server.impl.jac:609. Profiling only the asyncio main thread
misses that CPU. A launcher shim can wrap that worker-side callable and dump
per-call/aggregate pstats without editing the app/runtime source. Exclude this
instrumented run from timing claims and report auth/main-thread coverage
separately. No such hook currently ships as a normal request option.

## Historical stage evidence available in this checkout

- session0901/analysis/t200_feed_stage.md contains an audited historical t200
  table: Jac db43.011ms, build64.640ms, ser11.168ms, total97.053ms; it also
  explains why summing marginal medians is not a per-request decomposition.
- That note distinguishes a genuine t200 capture from a later t50-contaminated
  bar labeled feed_t200. The contaminated bar cannot be a t200 baseline.
- Referenced raw night0823/data/census/.../marks.json,
  night0823/data/stages_r/... files and stage_split.csv are absent from this
  clone. The note supplies documented historical context, not raw evidence for
  a freshly recomputed comparison.
- No littleX per-phase capture matching the session0904 W1 t20 headline
 13/16.4ms was found. Current23.466ms versus those totals therefore needs a
  current phase measurement; historical per-phase attribution cannot be
  inferred from the available totals.

This plan changes neither the active matrix, fixture nor app while the formal
run is in progress.
