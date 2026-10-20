# Jac write function spans

Source: `littlex/w2-investigation/20261019T212611Z-spans/1-jaseci/functions`. Each operation has 100 measured requests after 100 warmups. Values below are per-request means in milliseconds. The diagnostic wrapper times functions and adds overhead; formal timing remains in the baseline/stage results.

| Operation | Dispatch wall | Main CPU | Worker CPU | Combined CPU |
|---|---:|---:|---:|---:|
| create_tweet | 4.195 | 1.075 | 0.816 | 1.891 |
| follow_user | 4.983 | 1.054 | 1.099 | 2.153 |
| like_tweet | 4.234 | 1.024 | 0.875 | 1.899 |

Dispatch spans include routing, request auth/context, argument decoding, walker execution, commit, and response construction. Main and worker CPU are measured with `time.thread_time` on their respective threads. The dispatch clock includes time awaiting the worker.

| Operation | Walker wall / CPU | Worker Session.commit wall / CPU | Worker PgStore.commit wall / CPU | Main batch_get wall / CPU |
|---|---:|---:|---:|---:|
| create_tweet | 2.880 / 0.813 | 1.991 / 0.385 | 1.458 / 0.047 | 0.514 / 0.368 |
| follow_user | 3.721 / 1.095 | 1.834 / 0.297 | 1.422 / 0.043 | 0.492 / 0.358 |
| like_tweet | 2.992 / 0.873 | 1.826 / 0.268 | 1.462 / 0.037 | 0.501 / 0.355 |

These functions are nested: Session.commit contains PgStore.commit, and the walker contains both. PgStore._run also contains the SQL COMMIT call. Their inclusive times must be compared by boundary rather than summed. Worker PgStore.commit accounts for 1.42–1.46 ms wall per request and 0.037–0.047 ms thread CPU. Main-thread PgStore.commit totals about 0.002 ms per request, while main Session.commit totals 0.042–0.045 ms.

The main thread contributes approximately 1.02–1.07 ms CPU per request, alongside 0.82–1.10 ms worker CPU. Measuring only the walker thread omits roughly half of the application CPU in this capture. Main Session.batch_get accounts for approximately 0.49–0.51 ms wall and 0.36–0.37 ms CPU per request. The function-level cProfile capture below identifies the associated initialization, routing and worker call paths.

The request CPU totals include instrumentation. CPU and wall spans are separate measurements; the wall-minus-CPU remainder includes database waits, thread scheduling, and other waiting. SQL protocol logs provide the corresponding database duration boundary.

## Function profiler receipt

The successful function capture is `littlex/w2-investigation/20261019T212828Z-function/1-jaseci/functions`: 100 measured requests per operation. Python 3.14 main/worker profilers transfer ownership of the global monitoring slot at each `to_thread` boundary. Its separate `selected-function-analysis.json` retains selected function counters and attribute-assignment caller edges.

The function profiler increases measured CPU substantially: main/worker cumulative CPU per request is 3.963/2.785 ms for create, 4.090/4.029 ms for follow, and 3.848/3.220 ms for like. These measurements identify functions and call counts; the lighter spans capture supplies the quantitative wall/CPU boundary.

Each operation executes `_toml_section` twice per request on the main thread. Source `runtime/ad469-source/jac/jaclang/runtimelib/impl/session.impl.jac:1` opens `jac.toml` and calls `tomllib.load` each time. `promotions_for` calls it during Session initialization (line 255); `retention_days_for` calls it while constructing the runtime lease (line 153). Profiled inclusive CPU is 0.594–0.626 ms per request, including profiler overhead. The separate `get_config` function is called twice but totals approximately 0.0009 ms per request in this instrumented capture. The low-overhead `_toml_section` spans reported below measure its direct cost.

Main-thread `archetype.__setattr__` executes 208–209 times per request, taking 0.201–0.209 ms exclusive CPU in the function capture. For create, 96 of those calls arise from generated dataclass `__init__` methods. The retained call edges also identify Session/Store/context initialization and response-header object assignments. This is general object initialization/attribute machinery across the request, alongside dirty-tracking uses; assigning all of it to graph mutation would overstate mutation overhead.

Worker database-driver calls scale with operation: create has five `PgStore._run` calls per request, follow eight, and like averages 6.96. The main thread has four per request across all three operations. The SQL-category spans classify these calls by their actual SQL text to separate COMMIT from reads, writes, and setup.

## SQL-category and configuration spans

Capture: `littlex/w2-investigation/20261019T213018Z-spans/1-jaseci/functions`. Metadata confirms all configuration hooks. SQL labels partition calls to PgStore._run; each label derives from the SQL text, with `type-registry` matching graph_types references. Values are per-request means over 100 requests.

| Operation | TOML parses/request | TOML wall / CPU ms | Main SQL wall / CPU ms | Worker SQL excluding COMMIT wall / CPU ms | COMMIT wall / CPU ms |
|---|---:|---:|---:|---:|---:|
| create_tweet | 2 | 0.181 / 0.182 | 0.488 / 0.295 | 1.098 / 0.351 | 1.461 / 0.047 |
| follow_user | 2 | 0.156 / 0.157 | 0.382 / 0.245 | 1.778 / 0.510 | 1.395 / 0.042 |
| like_tweet | 2 | 0.154 / 0.155 | 0.378 / 0.248 | 1.202 / 0.449 | 1.424 / 0.039 |

Direct configuration parsing accounts for 0.154–0.181 ms wall and 0.155–0.182 ms thread CPU per request in this lighter capture. This confirms two synchronous parse operations on the request path and bounds their measured cost. The function-profiler value of roughly 0.6 ms includes its heavier instrumentation.

Main SQL consists of two anchor loads, one BEGIN, and one SET per request. Worker queries include one anchor INSERT and one COMMIT per request. The initial graph_types-reference category combines registry writes with graph traversals containing graph_types subqueries; the corrected capture below separates these operations. The original category JSON remains alongside its capture.

The COMMIT _run span measures application-side driver wall/CPU around that SQL call. Database protocol duration and backend CPU remain distinct boundaries; the large wall-minus-thread-CPU component represents waiting, whose database portion is available in retained protocol logs.

## Corrected SQL-category capture

The authoritative categories use `littlex/w2-investigation/20261019T213148Z-spans/1-jaseci/functions`. Its retained launcher source/provenance records the corrected classifier: explicit graph_types DML and standalone registry SELECT are distinct from traversal SQL containing registry subqueries. Each operation has 100 measured requests.

| Worker category | Create calls / wall ms / CPU ms | Follow calls / wall ms / CPU ms | Like calls / wall ms / CPU ms |
|---|---:|---:|---:|
| Anchor traversal | 1 / 0.451 / 0.082 | 2 / 1.004 / 0.150 | 1 / 0.456 / 0.083 |
| Anchor load | 1 / 0.157 / 0.077 | 3 / 0.373 / 0.189 | 2.96 / 0.439 / 0.222 |
| Anchor INSERT | 1 / 0.241 / 0.092 | 1 / 0.186 / 0.079 | 1 / 0.197 / 0.089 |
| Type registry INSERT | 1 / 0.094 / 0.051 | 1 / 0.074 / 0.046 | 1 / 0.087 / 0.052 |
| COMMIT | 1 / 1.428 / 0.039 | 1 / 1.384 / 0.034 | 1 / 1.470 / 0.038 |

Main-thread query counts remain two anchor loads, one BEGIN, and one SET per request. Follow performs two traversals instead of one and three worker anchor loads instead of create's one; these are directly measured query counts. Follow's traversal wall total exceeds create's by 0.553 ms, while its traversal thread CPU exceeds create's by 0.068 ms. Full SQL-shape and backend-duration evidence is retained by `write-investigation/sql_work.py`; this table measures the application's driver boundary.
