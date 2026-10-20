# IC1 measured cost breakdown

Per-command dedicated-thread ordered SQL matching verified, with explicit truncated-prefix labels

## Existing evidence

| Delay | MySQL direct median ms | Current-thread CPU ms | Paired elapsed minus thread CPU ms |
|---:|---:|---:|---:|
| 0 | 269.244 | 9.108 | 259.180 |
| 2 | 284.882 | 9.373 | 274.113 |
| 10 | 361.322 | 13.076 | 349.335 |

## Instrumented MySQL per-category medians

| Category | Commands | Server statement ms | Rows examined | Rows sent | Complete received ms | Complete delivered ms |
|---|---:|---:|---:|---:|---:|---:|
| closure.frontier_adjacency | [3] | 177.491 | 175262 | 11769 | 334.010 | 468.489 |
| person.filter_or_projection | [1] | 86.639 | 9932 | 18 | 86.460 | 89.070 |
| transaction.begin | [1] | 0.020 | 0 | 0 | 0.194 | 2.439 |
| transaction.commit | [1] | 0.036 | 0 | 0 | 0.196 | 2.392 |
| transaction.setting | [1] | 0.030 | 0 | 0 | 0.162 | 2.330 |

Statement matches use exact normalized SQL or the explicitly labeled 1024-character truncated prefix in dedicated-thread event order; warmup events are matched before selecting measured requests. Per-request raw sums and residuals are retained in JSON.

## Measurement boundaries

- Native IC1 baseline and final both execute13 commands with the same SQL sequence. Quiet request timings differ materially from logging-on profiles; the controlled quiet and instrumented windows are reported separately.
- Native execute timers come from PostgreSQL duration logs; they exclude Bind and application work.
- MySQL P_S statement timer is inclusive server statement elapsed, not CPU.
- Protocol complete_received and complete_delivered are separate boundaries; injected delay belongs only to the latter.
- Java request thread CPU is directly measured; native quiet rows provide whole-process CPU per measured request.
- Per-request paired quantities are aggregated before medians.
- Native PostgreSQL and MySQL use different engines and SQL shapes; per-category timings describe their measured execution costs.

## Native PostgreSQL instrumented request medians

| Variant | Delay ms | HTTP client ms | Application server ms | Execute sum ms | Frontend to Ready delivery sum ms |
|---|---:|---:|---:|---:|---:|
| baseline | 0 | 262.367 | 261.065 | 113.523 | 254.891 |
| baseline | 2 | 300.692 | 299.134 | 112.596 | 292.180 |
| final | 0 | 420.670 | 418.758 | 181.572 | 412.694 |
| final | 2 | 289.586 | 288.310 | 114.307 | 282.278 |

## Attribution scope

Each measured MySQL request’s seven commands are matched to dedicated-thread P_S events in execution order. The three adjacency reads and final Person projection dominate measured server elapsed. Their row metrics and completion intervals appear above. Native13-command BFS includes an early first-name endpoint filter and later projection of candidate matches; the conventional7-command reference applies its named-person projection after building the BFS frontiers. These are distinct SQL forms over the shared logical graph. Request elapsed outside measured protocol spans is recorded as an unassigned application/driver gap.

Elapsed minus thread CPU combines server execution, blocking and scheduling. Existing PostgreSQL duration logging supplies execution elapsed; native quiet receipts supply process-level CPU.

## Same-engine SQL-work comparison

All three Java forms use the same MySQL fixture and indexed adjacency. Their three frontier input cardinalities are 1, 10 and 2,740 UUIDs; observed row counts are 10, 2,750 and 9,009. Full/pruned select matching first-name IDs before their final18-ID anchor projection. The conventional reference applies its first-name condition in a final9,036-ID Person projection.

| Form | Projection input UUIDs | Rows examined | Rows returned | Projection server median ms |
|---|---:|---:|---:|---:|
| full | [18] | 18 | 18 | 0.237 |
| pruned | [18] | 18 | 18 | 0.240 |
| conventional | [9036] | 9932 | 18 | 86.639 |

The conventional final projection accounts for an observed extra server-work component relative to the candidate-first Java forms. Exact query texts, SHA256s, cardinalities and matched P_S/protocol rows are retained in `ic1-same-engine-comparison.json`. The PostgreSQL-versus-MySQL quiet gap remains a separate cross-engine comparison; native logged-profile overhead and the quiet window have separate measurement boundaries.
