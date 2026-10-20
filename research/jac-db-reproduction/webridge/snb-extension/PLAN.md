# Extension to the colleague's other SNB benchmarks

The research question is whether Jac's graph/walker semantics enable database-operation combinations that differ from WeBridge's stored-procedure synthesis, and how close automatic execution comes to conventional SQL.

## Fixed workloads

Extend IC5 with IS1 (profile), IS2 (recent messages), IS3 (friends), IC1 (name-filtered three-hop search), IC2 (friends' messages), and IC13 (bounded shortest path). Original parameter row zero is the declared nonempty performance input for each query. The complete twenty-row parameter collection per query remains a separate correctness gate. Source applications, parameter hashes and historical canonical-result hashes are pinned in `inputs-all20.json` and `inputs-representative.json`.

## Eight configurations per query

- Native Jac original and final runtime/compiler revisions.
- Full-behavior Java and its actual WeBridge pipeline.
- Java with the declared Jac-specific overhead removed, and its actual WeBridge pipeline.
- Conventional set-oriented Java SQL and its actual WeBridge pipeline.

Java's full behavior follows actual native SQL/access traces. Existing explicit builtins and runtime fast paths count as part of the baseline. Source comments and hypothetical SQL lowerings are checked against emitted SQL. Dialect adaptations, applicability limits and actual failed stages receive separate measured receipts.

## Evidence

1. Verify all twenty original canonical results against matched query-complete graph data.
2. Run quiet timing at 0/2/10 ms added response delay, ten warmup plus thirty measured requests per supported configuration, recording actual SELECT 1 calibration and exact outputs.
3. In separate instrumented requests, reconstruct serialized protocol command/complete-response cycles and actual SQL categories. For WeBridge, inspect both outer CALL boundaries and executed nested table operations.
4. Map source graph stages to emitted SQL, identify retained standalone operations, distinguish query rewriting from procedure packaging, and preserve generated procedure hashes and actual activation/fallback state.
5. Publish raw evidence, reproducibility scripts, an integrated English PDF and results report.

The additional fixture is a complete query-specific closure over all six twenty-input workloads: all Person/Knows records, complete relevant authored messages, complete ReplyOf ancestor chains, profile location edges, endpoints and owner roots. Original graph UUIDs, sequence and business properties are preserved. The original full graph and IC5 fixture remain available separately.

Quiet measurements run serially after loading/indexing/provisioning and outside native symbolic captures. Diagnostic instrumentation has its own timing scope. All owned services/proxies stop and logging settings restore after runs. Raw measurement evidence is retained; report versions fully superseded by the integrated analysis can be replaced in Git.
