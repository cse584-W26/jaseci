# WeBridge comparison archive

TPC-C and littleX: [English DB-call RTT slides](non-snb/jac-webridge-tpcc-littlex-comparison.pdf), [measured report](non-snb/REPORT.md), [RTT / SQL-count CSV](non-snb/results.csv), and [original-schedule references](non-snb/rtt-reference-results.csv). This extension uses compact command-to-complete-response captures at 0 / +2 / +10 ms added response delay.

Start with [the seven-query comparison](benchmark-comparison/REPORT.md) and its [English PDF](benchmark-comparison/jac-webridge-snb-comparison.pdf). The PDF presents the six-query extension and appends the completed IC5 study. The machine-readable latency and synchronization matrix is [results.json](benchmark-comparison/results.json), with a CSV counterpart.

## Experiments

IC5 uses a 460,984-anchor matched fixture. The additional IS1, IS2, IS3, IC1, IC2 and IC13 experiments use a query-complete 1,475,843-anchor fixture over the colleague's original inputs. Each comparison includes Jac original/final, full Java/WeBridge, pruned Java/WeBridge, and conventional set-oriented Java/WeBridge. The report distinguishes the two cohorts and the PostgreSQL/MySQL implementation pairs.

The six-query extension has original twenty-input direct-program gates, exact selected-source gates, original row-zero generated-procedure gates, and quiet response-delay measurements. Fast cells use ten warmups and thirty measured requests. Slow IC1 generated procedures use three fresh first-request attempts per delay with a fifteen-second limit; these records identify incomplete warmup and retain verified owned-session cleanup. Instrumented timing and actual SQL/protocol profiles accompany the quiet data.

Original WeBridge capture/replay, generated SQL and runtime definitions, stage errors and compatibility changes are retained. Full IC1 and IC2 also preserve a trace-hash stack overflow after artifact emission, followed by validation and execution of the original emitted artifacts. The IC1 cursor-dispatch diagnostic has an independently verified source formula and a completed correct instrumented CALL.

## Reproducibility

Run the Python verifiers under `benchmark-comparison/` to rehash outputs, recompute timing medians, check actual SQL/protocol cycles, verify the IC1 diagnostic and validate cleanup. `README.md` in that directory describes collection scripts and exact timer boundaries. The selected MySQL protocol analyses retain command-to-complete-response ordering, response frames/bytes/result sets and observed nested stored-program operations. Selective instrumentation is identified in its receipts.

`archive-manifest.json` lists selected files and SHA256 values. Source snapshots, generated procedures, raw measured outputs, per-request timings, payload-free framing, SQL catalogs, compiler errors and environment/settings receipts are included. Six small `SnbSetSql.class` files allow the selected-source verifier to rehash the exact conventional bytecode used by the captures.

Large dataset exports, native graph/record payloads and build dependencies remain in the local collection. Their export/build/stage receipts retain hashes, sizes, commands and upstream revisions. The local collection root is `/home/baichuan/jaseci/reproduction/webridge`; the public archive sits in `research/jac-db-reproduction/webridge`.

The earlier original-paper workload reproduction remains under `paper/`. Its setup and environment receipts are a separate experiment from the Jac/SNB comparison.
