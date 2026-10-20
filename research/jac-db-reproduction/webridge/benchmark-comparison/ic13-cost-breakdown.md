# IC13 measured SQL-form and cost comparison

- Native and access-equivalent Java evaluate a frontier BFS bounded at six levels.
- Conventional SQL evaluates one CASE with ordered EXISTS tests for path lengths one through six; first success gives minimum distance, identical endpoints return zero, otherwise minus one.
- The conventional reference passes all 20 canonical inputs; different SQL plans are part of this comparison.
- Actual P_S events establish executed predicate and dispatch counts.
- Per-stage measurements distinguish protocol latency and server computation.
- Instrumented P_S and wire timing are diagnostic; quiet latency medians are from separate runs.

## Conventional quiet medians

| Delay ms | Direct ms | Generated SP ms |
|---:|---:|---:|
| 0 | 1.531 | 1.898 |
| 2 | 11.033 | 11.244 |
| 10 | 44.452 | 44.478 |

## Instrumented generated-procedure scope

| Form | Request median ms | Inclusive CALL ms | Direct instrumented children ms | Paired CALL minus children ms |
|---|---:|---:|---:|---:|
| conventional | 12.068 | 0.861 | 0.793 | 0.067 |
| full | 2644.271 | 2290.671 | 164.126 | 2126.545 |
| pruned | 2551.403 | 2265.886 | 162.593 | 2103.747 |

Business-only P_S records the executed statement and cursor-open events. The paired inclusive-CALL-minus-direct-children quantity records the remaining procedure interval, including uninstrumented control/dispatch and other unassigned procedure work. Exact source guard counts describe generated code size; observed P_S categories provide executed database-work counts.

Detailed per-category command completion intervals and native server execute timings are retained in `ic13-cost-breakdown.json`. A complete server-cost attribution additionally requires matching baseline P_S statements to request boundaries and distinguishing inclusive CALL timing from child statement timing.
