# Database latency comparison

The experiment compares seven implementations of the fixed small nonempty IC5 input on matched logical graph data: native Jac original and SQL pushdown, full-behavior Java and its WeBridge procedure, pruned Java and its WeBridge procedure, and conventional Java executing a set-oriented SQL query.

## Input and measurements

`../alignment/small-diagnostic/input.json` fixes person 8796093030404 and minDate 1347527525888. The expected result is forum 2061584375281, title “Album 7 of Jie Xie”, postCount 0. The traversal reaches ten friends, one qualifying forum and fifteen posts. The shared logical graph contains 460,984 anchors and 300,901 edges. The conventional SQL implementation additionally passes the original 20-input result gate.

Every timing cell uses one persistent database connection after setup, ten warmup requests and thirty measured requests. Jac's service uses its existing connection management. All application measurements use CPU affinity 9,19 and run serially between implementations. Database statement logging is disabled for timing. Raw request rows contain correctness checks, timing, and SQL counts where supported. Instrumented SQL censuses run separately. Tables show medians; the machine-readable results also retain p95 and raw samples.

Jac reports server-total plus commit headers and separately records HTTP client time. Java reports the interval containing request setup, transaction, database work and result construction, excluding JSON serialization. Jac uses PostgreSQL 18.6 with runtime mirror/adjacency structures; the Java implementations use the MySQL 5.7.44 uniform UTF8 graph fixture. Cross-system absolute times combine these database and runtime choices.

## Latency transport

`proxy.py` forwards the unmodified database byte stream on loopback TCP. Client-to-database traffic is forwarded immediately. Each response chunk is scheduled for receipt time plus 0, 2 or 10 ms, in FIFO order. A dedicated receiver continues reading while the delivery task waits, so adjacent chunks' deadlines overlap. The proxy supports both the native PostgreSQL Unix socket and MySQL TCP endpoint. Its process and byte-count receipts are retained.

The three settings are **injected response-direction delay**, rather than claims of exact total RTT. Warm persistent `SELECT 1` round trips calibrate each database/condition. Every timing cell uses the same proxy path, including 0 ms. PostgreSQL additionally retains direct Unix-socket controls; MySQL retains a direct TCP control. The prior direct-transport timing experiment remains a separate measurement.

SQL statement count and protocol flight count are distinct. Prepared-statement negotiation, driver behavior, server response structure and scheduling contribute to observed latency. Interpret performance using measured request times and calibrated round trips.

## Sources and execution

- Native Jac: `../jac-comparison/latency/sweep.py` and per-cell source, command and cleanup receipts.
- Full/pruned Java and actual WeBridge: `java_sweep.py`; `prepare_java.py` makes a copy of the existing timing driver with an endpoint property. Its timer and business code remain recorded in the source hash ledger.
- Conventional Java: `../alignment/idiomatic/IdiomaticIc5.java`, `ic5.sql`, its fixture invariants, correctness gates, EXPLAIN plans and runner.
- Independent verification: `analyze.py` recomputes the first six arms from raw data; combined analysis includes the new SQL baseline.

All proxies are scoped to the experiment clients; no global network settings change. Application services, owned processes and proxy listeners stop after their runs. Fixtures and raw evidence remain available.
