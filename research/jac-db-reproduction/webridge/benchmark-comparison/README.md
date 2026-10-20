# Jac and WeBridge on the colleague's SNB benchmarks

The extension compares six existing queries—IS1, IS2, IS3, IC1, IC2 and IC13—with the completed IC5 study. The two experiments are execution latency under 0/2/10 ms added response delay and actual SQL/complete-response synchronization analysis.

The eight configurations are native Jac original/final, direct Java full/WeBridge full, direct Java pruned/WeBridge pruned, and conventional set-oriented Java/WeBridge set-oriented. Full Java reproduces the ordinary native access sequence. The pruned form removes the explicitly recorded Jac-specific overhead. Each pair retains its source, database engine and fixture.

## Evidence layout

- `../snb-extension/inputs-all20.json`: original parameters and historical canonical hashes.
- `historical-hashes.json`: frozen independent historical oracle.
- `../expansion/fixture/`: query-complete fixture export/load scripts, logical-field round-trip checks and SHA receipts.
- `../snb-extension/native/`: unchanged Jac application, both runtime gates, quiet timing, SQL catalog, protocol flights and cleanup.
- `../snb-extension/java/`: full/pruned sources, immutable snapshots, selected cases, compatibility overlays, gates and timing.
- `../expansion/set-sql/`: conventional sources, measured candidate selection, gates, selected case status and timing.
- `mysql-profile/`: instrumented actual MySQL commands, complete responses and executed stored-procedure events.
- `../roundtrip-comparison/`: completed IC5 eight-configuration study, measured operation map and companion PDF.

Canonical results use SHA256 over `json.dumps(result, sort_keys=True)` with default Python formatting. Timing uses original row zero for each query and records the result object for every request. The complete twenty-row collections are direct-program correctness gates. Generated-procedure execution gates and timing use each declared original row-zero input. Original native source comments, explicit database builtins and actual emitted SQL are catalogued separately in `../snb-extension/native/source-forms.json`.

## Measurement

Fast quiet runs use ten warmups and thirty measured requests per cell. Slow generated procedures receive three bounded attempts per delay condition with a fifteen-second request limit; each actual timeout, verified owned server connection and cleanup are retained. The instrumented IC1 diagnostic also preserves a completed correct 129.4-second CALL and its quadratic dispatch structure. Quiet runs disable stored-program control instrumentation, save its exact prior settings, and restore them after both Java windows. Measurements are serialized outside symbolic capture, compilation and profiling. A server-to-client response-delay proxy provides 0/2/10 ms conditions; `SELECT 1` receipts retain actual calibration. Native Jac timing includes the server request span plus commit; Java records its JDBC request span and thread CPU. These are complete implementations on PostgreSQL and MySQL respectively.

Protocol profiling is a separate instrumented experiment. It verifies the next command follows delivery of the preceding complete response. MySQL packet frames, result sets, wire bytes, SQL commands and stored-program control events are recorded as distinct metrics. Live Performance Schema collection unions `(THREAD_ID, EVENT_ID)` and checks completeness before interpreting nested work. Parent CALL timing includes its descendants.

The original WeBridge record/replay/synthesis/install/runtime pipeline generates each tested procedure. The configured capture region starts after the session SET and ends before COMMIT, retaining START/SET/COMMIT as three outer client commands. Stage receipts preserve concrete failures and compatibility repairs. A successful capture is distinguished from a successful generated CALL. Initialization metadata remains in warmup traces; measured activation and query counts are checked on actual requests.

## Offline reproduction

Run `python benchmark-comparison/verify_results.py --java-timing` from the collection or archived WeBridge directory to recompute canonical output hashes and timing/protocol checks. `collect_results.py` assembles measured cells and rejects unfinished timing cells. `build_pdf.py` renders the English PDF from `results.json` and the measured operation maps. Source/class/input/schema hashes identify the exact captured programs.

`archive_results.py --destination PATH` copies selected public evidence. Large graph/record binaries, fixture payloads and credential-bearing request context stay in the local collection; manifests preserve their provenance and the public metadata needed to interpret measurements. The final Git archive manifest records every included file's SHA256.

For the selected protocol captures, run `python benchmark-comparison/verify_profiles.py`. `python benchmark-comparison/mysql-profile/reanalyze_selected.py` repeats analysis for the saved explicit capture selection. `summarize.py --refresh-selection` selects a new collection attempt deliberately.
