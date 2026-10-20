# Native Jac: six additional SNB queries

The unchanged SNB application runs on both the c12 baseline runtime and final runtime. Each variant passed all 120 original-input historical output hashes on the matched 1,475,843-anchor fixture. Per-input outputs are retained in `gates/baseline-canonical` and `gates/final-canonical`. The final checkout includes later experiment-report commits; its `jac` subtree is identical to commit 32c5d1dbb. `source-forms.json` records both tree hashes.

## Workload and fixture

`inputs-all20.json` and `inputs-representative.json` preserve original benchmark parameters. Every timing/profile uses original index0, whose historical output is nonempty for all six queries. The matched graph includes all Person/Knows records, query-author message closure, ReplyOf root/creator closure, and required locations. The fixture receipts independently verify all 13 copied anchor fields. Conventional MySQL query gates also reproduce all 120 hashes.

The baseline already uses several database operators. IS2 explicitly calls `jtopk` and `jroot_many`; IC2 explicitly calls `jtopk`. IC1 and IC13 express bounded variable-length traversal plus endpoint predicates. Actual c12 SQL uses adjacency-frontier expansion, lateral topK, promoted reply roots, and selected-field projections. The operation map distinguishes these existing mechanisms from differences introduced by the final runtime.

## Bootstrap

Source census preserves the original full graph: anchor count and xmin aggregate are identical before and after. Its initial canonical work is separated from request profiles. Source warm SQL counts are IS1 7, IS3 12, IC1 13, IC13 14, IS2 24, and IC2 33, each repeated three times with exact historical outputs.

The matched fixture initially contains empty derived tables. The first baseline gate passed 80 queries, then IS2 returned an empty result. This preserved attempt is a fixture bootstrap failure. Canonical runtime ensure methods filled mirrors, HasCreator endpoints, ReplyOf roots, and adjacency structures; the subsequent complete baseline and final gates passed all 120 outputs. Provisioning receipts retain transient autovacuum lock refusals and successful bounded repairs. Table autovacuum options were restored and the fixture analyzed before timing.

## Measurement boundary

Quiet timing uses ten warmups and thirty measured requests per query, variant, and delay condition. A shared protocol-transparent proxy delays server-to-client byte delivery by 0/2/10 ms. Persistent `SELECT 1` controls measure actual roundtrip latency before and after each condition; direct Unix controls measure proxy overhead separately. Quiet requests disable SQL-duration logging. Each row preserves HTTP headers, actual result, canonical hash, and HTTP client latency.

`server_ms` adds `x-server-total-ms` and `x-server-commit-ms`: the Jac request span begins after JWT verification and before identity/root initialization; it includes argument decoding, worker dispatch, walker execution and commit, and excludes result serialization. HTTP client latency is reported separately. Process CPU is measured over the full thirty-request interval with 10 ms kernel ticks, then divided by 30.

Separate protocol profiles preserve the actual PG Parse/Bind/Describe/Execute/Sync and ReadyForQuery framing. The analysis matches SQL to request-owned backend PIDs and proves whether each subsequent command was sent after the preceding Ready delivery. SQL statements, protocol frames, TCP chunks, and synchronization cycles remain distinct metrics.

## Reproduction

Run `native/gate.py --variant baseline`, canonical `native/provision.py --database jac_webridge_matched_six_20261020 --variant final --execute`, then `native/gate.py --variant final`. Each output directory is exclusive; preserve existing attempts and choose a new attempt label for gates.

Run `native/sweep.py --out native/latency` in an exclusive quiet window, then `native/summarize.py`. Run `native/profile.py` separately and `native/analyze_profiles.py` for instrumented SQL/protocol receipts. All drivers use the existing PBSCPython3.14 environment and unchanged Jac service launcher.

## Results

All 1,440 requests passed the historical result hash: 360 warmups and 1,080 measured requests. The table reports median Jac server time in milliseconds, adding the commit span.

| Query | Baseline0ms | Final0ms | Baseline2ms | Final2ms | Baseline10ms | Final10ms |
|---|---:|---:|---:|---:|---:|---:|
|is1|2.011|2.053|18.078|17.574|79.838|79.594|
|is2|6.441|6.405|68.232|66.826|272.709|270.710|
|is3|3.330|3.266|33.403|35.419|136.969|137.074|
|ic1|37.598|37.442|68.814|68.512|184.089|189.191|
|ic2|10.528|10.595|97.359|100.314|379.500|385.696|
|ic13|35.142|34.987|69.981|70.251|216.228|210.078|

The actual ordinary SQL sequence is identical between the two Jac variants for all six representative inputs. Consequently, these cases exercise capabilities already present in c12. The final runtime shows similar latency across the conditions.

| Query | Ordinary synchronization cycles | Actual retained database work |
|---|---:|---|
| IS1 |7| BEGIN/SET/COMMIT; root, Person and Place hydration; IsLocatedIn hop |
| IS2 |24| Transaction 3; full-anchor hydration 15; Person field projection 1; guest resolution 2; lateral topK 1; promoted reply roots 1; HasCreator hop 1 |
| IS3 |12| Transaction 3; full-anchor hydration 2; descendant-type probe 1; root-permission probes 2; guest resolution 2; Knows field-projection hops 2 |
| IC1 |13| Transaction 3; full-anchor hydration 3; Person endpoint filter 1; adjacency frontier 3; selected Person field projection 1; guest resolution 2 |
| IC2 |33| Transaction 3; full-anchor hydration 25; descendant-type probe 1; Knows hops 2; lateral topK 1; author HasCreator hop 1 |
| IC13 |14| Transaction 3; full-anchor hydration 4; target Person projection 1; guest resolution 2; endpoint filter 1; adjacency frontier 3 |

All 72 instrumented requests match their request-owned backend SQL logs. Normal cycles contain Bind/Describe/Execute/Sync followed by ReadyForQuery. Each subsequent frontend command arrives after the prior Ready delivery, including commands on the separate identity connection. IC13 has one extra schema-guard SimpleQuery in one 2 ms request per variant: actual triples are 14/15/14 and 15/14/14. The schema guard is retained in the public operation map.

Payload-free frame/chunk metadata are archived as `profiles/delay-*/{variant}/trace/events.jsonl.gz`; `analyze_profiles.py` can rerun from these files and saved SQL logs. Raw binary protocol captures remain private. `profiles/operation-map.json` provides category ranges and ordinary SQL equality; `profiles/sql-catalog.json` contains stable hashes and exact SQL.

## Cleanup and reproducibility receipts

`latency/completed.json` confirms every condition completed and all proxy processes stopped. Every variant/condition retains launch/source provenance and `cleanup.json` confirming application shutdown and database logging restoration. Each proxy has a successful termination receipt. The canonical provisioning autovacuum options were restored before timing.

The short external compile window overlaps only baseline 0 ms IS2 warmup iteration 0. `latency/compile-overlap-audit.json` verifies that no measured request overlaps this window.

CPU totals and 10 ms tick resolution are retained per query in every measured-cell directory. Full raw timing rows, calibration samples, SHA provenance, and protocol classifications accompany the summaries.
