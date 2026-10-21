# Native database-roundtrip primary measurements

The primary timer is the **per-request sum of actual database exchanges**, measured from the compact proxy receiving the first frontend bytes of an exchange through delivering its complete PostgreSQL ReadyForQuery response to the database client. It includes all application database connections, including identity lookups. A prepare-only or protocol-control exchange contributes time and one response exchange, but zero SQL commands. Each request also retains SQL-execution RTT and preparation/control RTT separately. HTTP, Python and Java application time outside these boundaries is excluded.

`normalized-rtt-latency.json` and `normalized-rtt-reference.json` hold accepted primary rows. `normalized-rtt-coverage.json` lists pending cells explicitly. The complete contract is162 latency cells and42 original references. Every original fixture, workload, warmup count, measured count and result/full-state contract is unchanged. The accepted t20 feed0ms pilot is the first two primary cells; the persistent controller skips those keys rather than measuring them twice.

`rtt-cycle-evidence.json` derives SQL and exchange distributions from the same primary requests at each0/2/10ms condition. Actual request records retain every call's monotonic timestamps, SQL IDs, backend PID, message-type counts and byte counts. Connection initialization/calibration outside an HTTP request is retained separately, while initialization or identity SQL actually triggered within a request remains part of that request's exchanges.

The proxy retains the original response-delay transport logic. It counts DataRows in memory and writes one compact record per completed exchange. It does not write per-DataRow JSON, read a request-tag file for each DataRow, or retain bound-parameter/result payload binaries. `compact-self-test-receipt.json` records the offline metadata tests:10,000 DataRows yield one completed-flight record; independent Parse+Sync yields one prepare-only exchange and zero SQL commands. Parsing still has an observer cost; the test establishes bounded metadata output, not zero overhead.

The pilot's first three measured inputs have exactly the same SQL ID order and18→14 SQL/exchange counts as the retained full protocol certificate (`compact-pilot-alignment.json`). Across its30 measured inputs, the actual counts are18/19 and14/15 because later actors require an additional identity lookup. The complete distributions remain primary data.

`complete_primary_rtt.py` persists collection and verification commands under `primary-rtt-controller/`. Each runtime pair for one case and delay has its own live measurement lease, followed by a separately leased independent verifier. A failed gate stops the controller and preserves its attempt. Complete source responses, full final-state checks, owned-process/database-session cleanup and exact logging-setting restoration are required before acceptance.

The previous `normalized-latency.json`/`normalized-reference.json` HTTP-wall observations and `db-time-analysis/` PostgreSQL-server phase observations remain secondary collections. They are not substituted for an unmeasured primary database RTT.

## Independent raw-trace join

Each normalized row supplies `compact_trace_artifact`, `compact_trace_catalog_artifact`, `compact_trace_receipt_artifact` and `compact_trace_completeness_artifact`, relative to the WeBridge reproduction root. They identify `delay-{delay_ms}ms/trace/{flights.jsonl,sql-catalog.json,receipt.json,compact-status.json}` in that collection. `requests_artifact` contains the HTTP-request association and the accepted primary values.

For each request tag, the complete ordered list of raw `flights.jsonl` records must equal that request's `calls` list. An exchange is identified by `(request_tag, connection, frontend_received_ns, reply_delivered_ns, backend_pid, SQL_ids)`. Recompute each `roundtrip_ms` from its two endpoint timestamps, then sum the actual exchanges for that request. Resolve SQL IDs against the accompanying catalog; a prepare-only exchange has no execution SQL ID. Warmup and measured tags remain separate, and `outside-request-flights.json` retains initialization/calibration exchanges outside those tags.

The compact receipt covers every accepted proxy connection, with total bytes received/forwarded/delivered. The completeness receipt requires the raw flight count to match the JSONL record count and zero pending groups on every connection. Application launch receipts preserve the `JAC_DB_URL` shim routing all database connections through that listener. Backend process IDs come from PostgreSQL BackendKeyData messages. The compact collection does not enable an additional PostgreSQL duration-log census.

## Completion

All162 latency cells and42 original references passed. The latency matrix contains6,540 measured requests plus4,020 warmups; references contain25,600 measured requests plus4,600 warmups. `primary-rtt-completion/completion.json` consolidates per-cell shutdown/settings/proxy receipts. `primary-rtt-controller-resume1/progress.json` records the remaining-only controller completing successfully after the documented warmup-category correction.
