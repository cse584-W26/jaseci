# Optional littleX CPU sampling after stage diagnostics

Use sampling only if stage headers and application/backend CPU leave a
function-level question. The formal matrix completes first; sampling runs use
separate restored diagnostic fixtures and separate output tags.

## Tool and process ownership

Static inspection on2026-10-19: ptrace_scope is0 and py-spy is absent from the
current PATH. Install/verify the tool in the later diagnostic window. Capture
its version and `record --help` with the resulting artifacts.

Launch the Jac child under the profiler so profiler ownership also works on
hosts with parent/child tracing restrictions:

```bash
py-spy record --rate 100 --gil --format speedscope \
  --output OUTPUT/cpu.speedscope.json \
  -- /home/baichuan/jaseci/reproduction/runtime/bin/jac314 \
       start main.jac -p 18120 --no-client
```

Run from the audited diagnostic app directory with the exact runtime flags
and fixture selection already used for that cell. A supervisor records the
profiler PID and child Jac PID, waits for readiness, performs untimed warmup,
runs the original request driver, then stops only its own child and waits for
the profiler to flush its capture. Keep raw output and stderr even on failure.
The Jac wrapper execs its interpreter, retaining the child process identity.

## Preserve the real workload

- W1 t20/t200: `harness/run.py --workloads feed_chain`, which invokes
  `load_feed_chain`.
- W3 default read path: `load_feed_page` (`mix_run.FEED_WALKER` default;
  original wrapper leaves FEED_WALKER unset). Keep BASELINE_FEED and the
  actual recorded environment. `load_feed_page_chain` is an explicit alternate
  route, selected only when that comparison is intended.
- Full W3 CPU capture uses the original mix_run.py schedule, write fraction,
  token/target selection and write oracle. Restore the fixture before each
  capture and keep its write warmup and timed sequence in one invocation.
- The old profile_run.py defaults feed to load_feed_leaf. Use the current
  harness driver instead of inheriting that historical default.

An initial target is10–20 seconds of sustained requests.500 or1000 calls are
reasonable starting budgets for small cells, but actual request duration
sets the window; a t200 batch can be much longer than t20. Retain executed
request counts, timing and operation mix rather than assuming a fixed batch
has a fixed duration.

## Separate request samples from startup and warmup

The parent-launch capture begins before Jac initialization, so its raw profile
also contains startup and warmup. Record sampler start, server-ready,
warmup-start/end and measured-driver-start/end timestamps. Save request-level
wall/monotonic timestamps from the diagnostic driver. When comparing hot
functions, restrict analysis to the conservative interior of the request
window using the speedscope sampled timeline; report the chosen boundaries
and duration. Retain the raw untrimmed profile.

Confirm the profiler's timeline origin from its captured start event before
trimming. Whole-process totals that include compiler initialization are not
request CPU attribution. If reliable time alignment is unavailable, label
that capture as process-lifetime exploration and use function stacks only to
form a follow-up hypothesis.

## Interpretation

`--gil` focuses on Python threads holding the GIL, useful for ranking Python
CPU functions. It is not a complete CPU census: native work releasing the GIL
can be absent. Correlate with measured app process CPU and use a separate
active-thread/native-stack pass only if the missing CPU requires it. Request
worker threads matter: Jac's synchronous walker executes through
asyncio.to_thread(Jac.spawn,...), so inspecting only the event-loop thread
would miss walker execution.

Report top functions by sampled weight and call-stack context for application
serialization, hydration, field coercion, query construction, walker sorting,
ACL checks and driver work as actually observed. Treat these as categories to
measure, not predicted causes. A waiting-stack capture is a different
instrument and does not establish network time.

Keep stage/protocol logging and sampler configurations with each capture.
Measured timings with sampling are diagnostic, separate from formal matrix
latencies. Reuse existing harness/profiling/buckets.py only after verifying
its categories match the current source paths and retained sample format.
