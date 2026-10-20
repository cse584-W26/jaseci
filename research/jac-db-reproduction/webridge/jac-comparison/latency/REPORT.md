# Jac matched-fixture database-latency sweep

The same matched IC5 diagnostic runs through original and final Jac with a shared response-stream delay proxy. Both retain exact results at all three conditions. Final Jac reduces warm SQL statements from 38 to 14 and remains faster throughout the measured sweep.

| Configured response delay | SELECT1 median RTT, before / after | Original Jac server median | Final Jac server median | Same-stack ratio |
|---|---:|---:|---:|---:|
|0ms|0.119 /0.096ms|25.894ms|5.733ms|4.52×|
|2ms|2.202 /2.374ms|145.260ms|39.532ms|3.67×|
|10ms|10.656 /10.479ms|469.417ms|160.229ms|2.93×|

Each application cell has 10 warmup and 30 measured requests on a persistent HTTP connection. All 240 application responses match the declared oracle; 180 measured samples are retained. The input, matched PostgreSQL fixture, exact source revisions and primary server timing boundary are documented in [the Jac comparison](../REPORT.md). `results/summary.json` retains medians, means, p95, client times, CPU and census counts.

## Transport control

The root agent's shared `../../latency-comparison/proxy.py` listens on local TCP 18532 and forwards to the native PostgreSQL Unix socket. Client-to-server bytes forward immediately. Independently scheduled server-to-client chunks receive fixed monotonic delivery deadlines; waits overlap across chunks. The identical implementation serves the MySQL comparison.

Original and final Jac use the same proxy at zero delay as well as at 2/10 ms. Direct Unix SELECT1 median RTT is0.032ms before and0.030ms after the sweep. The explicit proxy-zero condition measures its TCP/forwarding overhead: the earlier direct Unix Jac server medians were22.298ms original and4.523ms final, compared with25.894ms and5.733ms through proxy-zero. The zero-proxy results are the baseline for this latency sweep.

SELECT1 calibration uses a persistent psycopg connection, 10 warmup and 30 measured requests, before and after each condition. Results are checked on every request. Configured delay and measured RTT are both reported because scheduling and protocol behavior affect delivery timing. The proxy implementation's byte ordering, deadline scheduling, counters, queue memory and connection lifecycle are audited in [PROXY_AUDIT.md](PROXY_AUDIT.md).

## SQL census and CPU

A separate three-request instrumented census at 10 ms preserves the original counts42/38/38 and final counts30/14/14. First-request counts include cold checks and auxiliary readiness connections. Warm original requests use backend2470557; final warm requests use backend2470883. Compressed SQL logs, every executed statement grouped by PID, and parse/bind/execute/statement duration summaries are retained under `results/delay-10ms/census/`. `results/protocol-profile.json` summarizes the two later requests. The census uses duration logging; application timing uses duration logging off.

| Configured delay | Original process CPU, mean/request | Final process CPU, mean/request |
|---|---:|---:|
|0ms|6.333ms|2.333ms|
|2ms|16.000ms|6.000ms|
|10ms|21.000ms|8.333ms|

CPU values come from whole measured-interval process counters divided by 30 requests, with 10 ms tick resolution. They include inter-request housekeeping and exclude the separate proxy process. Per-request ticks remain raw fields. The 2 ms condition has p95 server times 199.452 ms original and 67.574 ms final; the summary retains this variation alongside medians.

SQL statement counts and protocol response flights are distinct quantities. This sweep reports observed application time, actual calibrated RTT, SQL counts and CPU separately. The direct source/compiler comparison retains the same PostgreSQL database, HTTP stack, fixture and algorithm across conditions.

## Reproduction and receipts

From `/home/baichuan/jaseci`:

```text
taskset -c 9,19 reproduction/runtime/venv314/bin/python reproduction/webridge/jac-comparison/latency/sweep.py --out <fresh-output-directory>
```

The sweep serializes all Jac application runs and owns the PG proxy lifecycle. Each condition saves the exact proxy and application commands, input/source hashes, calibration samples, logs and shutdown receipts. `service.py` and `run.py` add explicit TCP-target options for this experiment. Their original direct-Unix versions are archived under `source-before-tcp/`.

`results/completed.json` confirms every condition completed. `results/cleanup.json` confirms both application services and all three proxy processes exited, recorded PostgreSQL backend processes disappeared, and all per-run logging restoration receipts passed. The matched fixture remains available. The experiment uses scoped user-space forwarding; global PostgreSQL and network configuration retain their prior settings.
