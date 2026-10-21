# Native server-only zero-delay follow-up

## Why the existing numbers remain diagnostic

The t200 final full-feed instrumented collection has a226.682ms median PostgreSQL phase sum,416.342ms HTTP median and352.710ms application-server header median. Its separate quiet zero-delay cell has168.538ms HTTP and110.2215ms header medians. These are different collections; the first result is not a replacement for the quiet result.

PostgreSQL18 processes Execute by running the portal with a remote result receiver before measuring the duration. Its tuple receiver converts fields and emits DataRow messages during that portal run. Consequently the execute timer covers server-side result conversion/output and any waiting encountered there; it is not execution-engine CPU alone. See the official source: [postgres.c, exec_execute_message and check_log_duration](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/backend/tcop/postgres.c), and [printtup.c](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/backend/access/common/printtup.c). These source boundaries explain the timer's scope, rather than proving the cause of a particular observed delay.

The retained trace proxy synchronously parses and logs every frame before its receive coroutine queues the bytes for delivery (`trace_proxy.py`, Parser.feed/emit/receive). That establishes a receiver-overhead path. The old collection lacks wait-event sampling that would demonstrate how much PostgreSQL ClientWrite time, if any, came from that path. No backpressure attribution is established.

## Proposed collection

Use the same40 native arms, original source plans and fresh fixture per cell, but connect the Jac runtime directly to the existing Unix socket. Omit the byte proxy, payload capture and per-DataRow event logging. Retain PostgreSQL duration logs, raw source responses and full final-state verification. Enable database-scoped log_min_duration_statement=0 and preserve/restore all prior settings. Set log_parameter_max_length=0 during this diagnostic to avoid logging entire parameter arrays, recording the exact setting change. This preserves SQL and bindings, while retaining statement text and every logged phase duration.

W1/W2: four tiers × four workloads × two runtimes;10 warmups plus30 measured requests per cell. W3: four mixes × two runtimes;110 warmups plus100 measured requests per cell. Total:40cells,2960requests,1200warmups and1760measured. The original ad469CONTROL/final32 source pair remains unchanged.

Capture each request's SQL log window after its complete response and collector flush, outside the database timer. Verify every execute/simple-statement event, its PID and SQL ID; associate parse/bind with their actual command. Preserve actual extra identity/schema/TTL queries rather than imposing a fixed expected count. Read/write/identity/transaction subtotals are sums within each request; only then compute medians. Retain per-request SQL counts, phase counts and full result/state gates.

The implemented collector is `profile_server_only_littlex.py`. The pilot command is:

```sh
python non-snb/native/profile_server_only_littlex.py \
  --output littlex-db-only-zero-pilot --tiers t20 --only W1-feed \
  --profile-measured 30
python non-snb/native/finalize_db_only.py littlex-db-only-zero-pilot
```

The persistent `complete_db_only.py` waits for the pilot's successful cleanup, independently verifies it, then executes the remaining19 case pairs with a separate live lease and verification lease for each. Its recorded commands are under `db-time-analysis/direct-zero-controller/`. W1/W2 retain the source plan's10 warmups and30 measured requests. W3 commands select each original W3 mix with `--profile-measured 100`, retaining110 warmups and100 measured requests. No byte proxy or packet logger is started.

The collector retains the existing50ms post-response log-flush pause outside every server-phase sum. This is an explicitly paced diagnostic; lifecycle/cache SQL counts are recorded as actually observed. Every measured command is summed from raw server records, rather than assigned the quiet matrix's command count. The phase and timer boundary remain identical for both runtimes.

Estimate8–12minutes of lease-held work including40 fixture resets, startup, collection, shutdown and state checks; estimated retained data0.2–0.5GiB, with1GiB reserved. These are planning estimates, not measured completion times; interleaved queues add wall-clock waiting. Actual collection time and file sizes are recorded.

Even this direct-transport experiment measures PostgreSQL elapsed server phases, including output conversion and server-side waits. A compute-only timer would be a distinct measurement with a different output boundary.
