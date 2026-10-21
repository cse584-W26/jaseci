# PostgreSQL server-only durations for native littleX

The retained PostgreSQL logs provide **parse, bind, execute and simple-statement server durations**. This analysis sums those disjoint phases within each tagged request across every certified database connection, then takes the median of the per-request sums. HTTP, Python, Java, application headers and proxy-flight durations do not enter these values. Prepared statements reused in a warm request have no new parse event; their bind and execute events remain included.

There are40 original/final arms covering all20 littleX cases and896 measured requests. W1/W2 use three instrumented measured requests after10 warmups; W3 uses the complete100-slot measured schedule after110 warmups. All profiles used the separately instrumented2ms transport condition. These server-phase observations remain separate from the quiet latency matrix and retain their actual sample sizes. PostgreSQL logs round durations to0.001ms. The observed database phase includes the server's planning/binding, execution, result production and transaction work inside its logged boundaries; it is not a CPU-only or storage-only timer.

The verification matches each executed SQL identifier, backend PID, order and execute duration against the existing all-connection protocol certificates. It also checks every parse/bind/execute/simple-statement record count against frontend P/B/E/Q message counts. The source logs contain13,232 bind,13,232 execute,26 simple-statement and9 parse records. Every phase is counted once; a SQL command with bind and execute is still one command.

`summary.json` contains per-arm medians and actual SQL-count distributions. `requests.json` retains each request's complete phase totals, transaction/read/write/identity subtotals, fine SQL categories and per-command phase durations. The read bucket includes hydration, traversals, ACL reads, type/catalog and schema-guard reads. Transaction includes BEGIN, local settings, COMMIT and ROLLBACK. Write includes anchor and type-registry mutations. Identity contains identity-table lookups on their actual separate backend. Component medians are computed independently and need not add to the median total. W3 totals include the actual mixture of read/write operations, which remains identified per request.

## Measured request DB-time medians

|Case|Original ms|Final ms|n per arm|
|---|---:|---:|---:|
|littlex-create_tweet-t100|5.8250|2.5830|3|
|littlex-create_tweet-t20|5.9310|1.9330|3|
|littlex-create_tweet-t200|2.0220|2.6290|3|
|littlex-create_tweet-t50|2.4150|5.8060|3|
|littlex-feed-t100|100.0980|104.1560|3|
|littlex-feed-t20|19.8110|22.9840|3|
|littlex-feed-t200|218.0220|226.6820|3|
|littlex-feed-t50|48.1640|86.1730|3|
|littlex-follow-t100|2.8820|3.3530|3|
|littlex-follow-t20|3.0930|9.3140|3|
|littlex-follow-t200|3.0360|10.3230|3|
|littlex-follow-t50|9.5620|5.3240|3|
|littlex-like-t100|2.9030|4.5140|3|
|littlex-like-t20|3.1650|5.5480|3|
|littlex-like-t200|2.3160|5.9690|3|
|littlex-like-t50|2.3940|3.3160|3|
|littlex-mixed-t200-w0|3.7285|4.2680|100|
|littlex-mixed-t200-w15|3.7130|3.5540|100|
|littlex-mixed-t200-w30|4.0900|3.4720|100|
|littlex-mixed-t200-w5|3.9230|3.9940|100|

## Reproduce from retained evidence

Run from the reproduction `webridge` directory:

```sh
python non-snb/measurement_lease.py --label 'Native DB phase verification' \
  --receipt /tmp/native-db-phases-lease.json -- \
  python non-snb/native/db-time-analysis/analyze.py --check
```

The parser accepts `--root` for an alternate native evidence directory and `--out` for alternate outputs. Without `--check`, it writes fresh derived JSON; with that flag it verifies equality with the saved summary, per-request records and input hashes. `inputs.json` pins every compressed raw SQL log by SHA256. The phase logs, protocol certificates, SQL catalogs and classifier are included in the existing public evidence selection; the new script and derived outputs are added to that selection.
