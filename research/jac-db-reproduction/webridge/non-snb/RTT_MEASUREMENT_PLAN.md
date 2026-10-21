# Primary measurement: summed SQL round-trip time

The primary comparison measures the time occupied by database command/response
exchanges within an application request. The workload, input, fixture, arm and
added-delay contracts remain those in `coverage-contract.json`: 648 latency
cells, complemented by 168 original-schedule reference entries.

## Timer boundary

For each command exchange, the compact proxy records the monotonic time at
which the frontend command arrives and the time at which its complete response
is delivered to the client-facing connection. Per-request SQL RTT is the sum of
these exchange durations. The reported cell median is the median of the
per-request sums. Request-level application time is retained separately.

The measurement includes database execution, result transfer, the configured
response delay and compact proxy processing within that boundary. Client-driver
processing outside the boundary and application computation between SQL calls
are separate. Result production, buffering and backpressure can affect a
command's observed RTT. The metric is a database-call measurement, rather than
database CPU or server-only execution time.

All request-owned database connections are included, including native Jac's
auxiliary identity connection. Observer and outside-request initialization queries
are excluded; SQL initialization triggered inside a request remains included. PostgreSQL prepare-only exchanges contribute to
RTT and exchange counts while remaining separate from executed SQL counts. A
MySQL CALL contributes its outer command/complete-response duration once;
nested stored-program statements supply separate SQL-work attribution.

## Compact capture and validation

The protocol parsers retain command, response-completion, SQL identity,
connection identity and timing records. They avoid per-row and per-frame JSON
logging. Each pilot checks complete responses, ordering and counts against the
previously certified protocol behavior, plus full returned results and final
committed-state oracles. Benchmark groups hold the shared measurement lease and
verify owned-process cleanup and exact settings restoration before release.

Latency cells retain the original 0/2/10 ms added response delays. Pure littleX
operations retain ten warmup and thirty measured requests; mixed operations
retain 110 warmup and one complete 100-slot measured schedule. Original-length
reference schedules retain their original request counts. TPC-C uses the frozen
original transaction plans and state progression. Compiler failures retain
actual stage evidence and have no successful RTT value.

## Output interfaces

- `native/normalized-rtt-latency.json`: 162 native latency cells.
- `native/normalized-rtt-reference.json`: 42 native references.
- `tpcc/normalized-rtt-latency.json`: 126 Java/WeBridge TPC-C latency cells.
- `tpcc/rtt-reference-900-index.json`: six primary Java/WeBridge references.
- `littlex/normalized-rtt-results.json`: 360 latency cells and 120 references.
- Owner `rtt-cycle-evidence.json` files retain command-count distributions from
  the same RTT requests, including actual CALL and runtime-fallback evidence.

The primary figures report original Jac, optimized Jac and each Java/WeBridge
pair, with both SQL counts and RTT. Existing quiet application timings and
separate database-server phase analyses retain their own boundaries and
coverage as secondary evidence. Their values are not relabeled as SQL RTT.
