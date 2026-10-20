# Six-query Java / WeBridge protocol profiles

`summary.json` is an incremental set of measured arms. Each cell contains three post-warmup requests, actual command/response cycles, frames, bytes, result sets, request duration and verified historical output hashes. The original and generated-SP phases each use ten warmups. Profiles use a 2 ms response-delivery proxy and are collected separately from quiet timing.

`run.py` calls the frozen-case timer, captures protocol frame metadata and collects owned-thread Performance Schema records continuously. It retains unique `(THREAD_ID, EVENT_ID)` records, including parent CALL records that complete after their children. A second decoded THREAD_ID check detects concurrent history-ring overwrite. Each run acquires `integration/.mysql-sp-profile.lock`. A 15-second outstanding-command watchdog verifies the owned server connection and database before killing that connection, preserving a server-side cleanup receipt.

`analyze.py` matches request boundaries to the two session-status observations, checks actual Questions, recomputes result hashes, and proves that the next frontend command follows delivery of the complete previous response. It separates command cycles, protocol frames, rows and result sets. Measured CALL event ranges must be complete for analysis to pass.

Actual cursor-open events are associated with the next executed `SELECT cursor_cnt_N` result-materialization statement. This counter identifies `DECLARE cursor_N CURSOR FOR ...` in the generated procedure. The analyzer requires the result statement to precede another cursor open. Each association retains event IDs, declared SQL and its hash; source literal assignments resolve logical graph-edge categories. Open-event counts reflect executed cursors.

Performance Schema output separates direct business statements and cursor opens, materialized-row result SELECTs, replay-metadata SELECTs, and procedure control events. Parent CALL time is inclusive. Child timers are instrumented server elapsed time. Quiet latency remains in the separate timing experiment.

The initial IS1 timer attempt retained an actual cold callable-metadata count of eight commands and stopped at its strict warmup assertion. The timing-only overlay preserves cold metadata counts and enforces successful CALL activation and four commands after warmup. Later invalid P_S captures occurred while another finite, expensive IC1 procedure saturated the shared history ring; these attempts remain saved and excluded from certified cells. The shared lock serializes subsequent diagnostic calls.

IC1 pruned SP execution has an independently observed finite but expensive dispatch path. Its existing completed-call evidence and bounded diagnostic censoring are reported separately when available.

Run a ready pair with `run.py --query is1 --kind full --case CASE --out NEW_DIRECTORY`; analyze it with `analyze.py NEW_DIRECTORY`. `batch.py` processes currently ready case manifests, and `summarize.py` refreshes the partial summary. Pending or genuinely failed generated-SP stages retain their stage receipts; direct baseline profiles can use `--phases baseline`.
