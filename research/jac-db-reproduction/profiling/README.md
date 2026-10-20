# Request-scoped Jac CPU and wall profiling

`launch_jac.py` is a diagnostic launcher. It patches in-memory dispatch and
worker callables before starting the normal Jac CLI, leaving source/app files
unchanged. The coordinator supplies the restored fixture, existing measurement
flags, taskset affinity and logging configuration.

Example from the audited app directory:

```bash
env PYTHONPATH=/home/baichuan/jaseci/reproduction/runtime/ad469-source/jac \
    JAC_NO_DEV_SOURCE=1 JAC_NO_PRECOMPILE=1 \
    XDG_CACHE_HOME=/home/baichuan/jaseci/reproduction/runtime/cache314-ad469 \
    JAC_LLVM_SHIM=/home/baichuan/jaseci/reproduction/runtime/lib/libjacllvm.so \
    taskset -c 6-13 \
    /home/baichuan/jaseci/reproduction/runtime/venv314/bin/python \
    /home/baichuan/jaseci/reproduction/profiling/launch_jac.py \
      --output-dir /home/baichuan/jaseci/reproduction/results/NEW_TAG \
      --mode spans --operations create_tweet,follow_user,like_tweet \
      --warmups 100 --limit 100 \
      -- start main.jac -p 18120 --no-client
```

Supply the same CONTROL environment/JAC_CACHE_HOME already selected for the
cell; the example lists the source/bootstrap selection, not a replacement flag
recipe. Start a fresh fixture/server per operation when using the existing
write profile helper. Exactly100 warm calls to that route are excluded and the
next100 calls are profiled. Health requests and other routes are excluded.
Avoid an extra write smoke call before the counted warmup. Outputs refuse an
existing directory. SIGTERM/SIGINT flushes accumulated profiles and JSON after
the client finishes. Startup/compilation is outside all request profiles.

## Modes and outputs

- `spans`: selected function wall and thread CPU spans, outer dispatch totals,
  worker totals and request records. Use this first with SQL duration logging
  off to reduce observer overhead.
- `cprofile`: separate cProfile CPU profiles for main dispatch, walker worker
  and auxiliary worker calls. Each worker invocation has its own Profile.
- `both`: selected spans and cProfile in one diagnostic capture.

Per operation/lane: `.pstats`, text top exclusive/cumulative functions, and JSON
with complete function nodes, caller/callee edges and top100 lists. Per request:
operation ordinal, dispatch wall time, main/worker CPU totals and thread IDs
in the recorded worker spans. `main_plus_worker_cpu_ms` adds only disjoint
thread-lane outer CPU measurements, not nested selected-function spans.

## Source boundaries verified at ad469

- `ServingApp.dispatch` (serving/app.jac:218) encloses routing, request binding,
  token/identity/root work, execution and response construction. The wire write
  follows this method.
- `ExecutionManager.spawn_walker_sync` (server.impl.jac:586) deserializes input,
  then `_run_function_with_occ` begins user context before executing the walker.
- Its `asyncio.to_thread(Jac.spawn,...)` (line609) runs walker CPU on a worker.
  A ContextVar links that worker profile and auxiliary auth workers to the
  outer request.
- `_finalize_call_response` commits and serializes; Session.acommit directly
  calls Session.commit, so that work executes on the awaiting main thread.

Selected spans cover `_run_function_with_occ`, `_abegin_user_request_context`,
`_begin_request_context`, `_deserialize_wire_args`, Session.flush/commit/dirty
tracking/batch_get/read_barrier, PgStore._run/begin/commit/upsert/load_full,
Serializer.serialize/deserialize, graph connect/build_edge/disconnect and final
response construction. Metadata records hooks present in the selected runtime.
PgStore._run includes driver round-trip/fetch wall time; inspecting its CPU
profile separately distinguishes active CPU from waiting.

## Timing interpretation

cProfile uses `time.thread_time`, so thread waiting is excluded from its CPU
clock. Selected spans also report wall time. Main profiles remain enabled
across awaits; a sequential client ensures one diagnostic request at a time,
while unrelated main-loop background CPU may still be included. Nested async
and sync spans are inclusive: cumulative times cannot be summed as independent
phases. Deterministic profiling adds overhead; compare its hot functions, not
its instrumented latency, with formal metrics.

Preserve client wall time and both arms' original server headers. Jac's
headline includes identity/root setup and excludes reported serialization;
the SQL route starts its handler timing after FastAPI Depends auth. Outer
request scope and handler headline are distinct quantities. Stage reconciliation
is documented in littlex/PROFILING_PLAN.md.

For lower-overhead sampling, the optional parent-launched py-spy recipe is in
littlex/SAMPLING_PLAN.md. Use the real write routes and worker threads, record
CPU-oriented and waiting samples separately, and restrict analysis to the
request window. Stage/spans may resolve the question without a sampling pass.

Python 3.14 uses a process-wide cProfile monitoring slot. The launcher pauses
the main profiler before awaiting each to_thread call, profiles its worker,
and resumes main profiling after the worker finishes. Wall and thread CPU
spans retain the complete request boundary. A Python 3.14 threaded handoff
smoke test validates monitoring-slot transfer.
