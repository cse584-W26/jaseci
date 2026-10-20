# Measured native-to-Java access alignment

The frozen 240-request Java gate is `gates-20261020T215324439277Z/summary.json`. It covers all twenty original inputs for each full/pruned program. The later IS3 full alias-only compatibility gate is `gates-20261020T215519883648Z`. Each request checks the canonical Jac result and an independent MySQL Questions delta. The native statement sequence comes from `../native/source-census/<query>/sql-census.json` and its raw protocol/log records.

| Query | Native warm commands | Full Java warm commands | Pruned Java warm commands | Full Java body commands | Pruned Java body commands |
|---|---:|---:|---:|---:|---:|
| IS1 | 7 | 7 | 5 | 4 | 2 |
| IS2 | 24 | 24 | 7 | 21 | 4 |
| IS3 | 12 | 12 | 5 | 9 | 2 |
| IC1 | 13 | 13 | 8 | 10 | 5 |
| IC2 | 33 | 33 | 7 | 30 | 4 |
| IC13 | 14 | 14 | 8 | 11 | 5 |

These are original input index 0. Transaction begin, transaction setting, and commit are the three outer commands. Native PostgreSQL connector housekeeping is recorded separately in the native sweep. Other inputs can change frontier depth or message count.

## Actual native operations

- IS1 loads root, input person, and city separately, with one location traversal.
- IS2 projects the input person's ID, performs guest identity resolution and a second root load, selects ten message IDs in one top-K command, hydrates messages individually, reads the promoted ReplyOf root column, batch-loads root posts, and fetches creator edges and authors in batches.
- IS3 projects friend fields directly in two directional Knows statements. Its additional operations include input/root loads, type metadata, root ACL metadata, and guest identity lookup.
- IC1 queries the first-name candidate IDs, executes three adjacency-frontier statements for this input, projects matching people, and performs guest/root bookkeeping.
- IC2 executes two friend-reference traversals and one friend hydration batch, one top-K statement, twenty individual message loads, and one creator-pair query followed by edge/author hydration batches.
- IC13 projects the target person's ID, queries the target-ID predicate, executes three adjacency-frontier statements for this input, and hydrates the surviving target. It also performs root/source loading and guest/root bookkeeping.

Native IC1 and IC13 use frontier queries against `adj_knows` in these actual executions. The observed access sequence determines the port.

## Cross-engine representations

The Java ports map UUID arrays to positional JDBC placeholders and UUID values to hyphenated character columns. A finite top-K LATERAL scan over the supplied authors becomes one UNION ALL of per-author/type ordered, bounded selects followed by the same global ranking. Its business-command count remains one. The matched fixtures provide the same logical Person, message endpoint/root, and Knows adjacency relations. Creator and ReplyOf cardinality checks return zero violations.

Native Person projections read promoted scalar columns; the Java projection paths reconstruct equivalent fields from stored archetype JSON. PostgreSQL and MySQL therefore have different physical representations and wire payloads. Actual wire bytes and execution profiles accompany the system comparison.

## Original WeBridge artifact behavior

`case-status.json` links every selected immutable source/class/input/schema snapshot and every measured failure. The full IC1/IC2 recorder can fail after emitting SQL and serialized runtime definitions: upstream `SQLGraphRecorder.process` writes SP SQL and definitions before computing the trace hash. Both affected cases have a zero-byte `generated/trace/ver-0`. The emitted definitions deserialize, identify the matching SQL procedure, and run through the original invocation manager; the emitted SQL is installed unchanged.

`cursor-dispatch-analysis.json` extracts actual generated cursor control. IC1 emits independent equality dispatch branches for 10, 2,750, and 9,009 cursor rows. Each loop increments its counter and has a finite exit. For the captured row counts, these loops execute 88,736,450 row-index equality tests. The completed instrumented IC1 pruned request reports a correct result at approximately 129.9 seconds; the separate quiet control exceeds its measured 15-second budget with SP instruction instrumentation disabled. The source bounds and measured counters establish the emitted control cost.
