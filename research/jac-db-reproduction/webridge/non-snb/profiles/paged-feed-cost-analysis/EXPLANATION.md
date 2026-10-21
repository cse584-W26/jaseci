# Paged feed: measured costs and scope

The primary metric is each request's **sum of database-call roundtrip durations**: command arrival at the instrumented proxy through complete response delivery. It includes database work and communication, excludes application gaps between commands, and counts a stored-procedure CALL once. Server-only timings below are a secondary attribution diagnostic.

For the **85 actual feed_page requests** in the retained W3-15 profiles at **2 ms injected response delay**, median summed call times are:

| Arm | Summed DB-call RTT ms | Median complete exchanges | Server statement/phase sum ms |
|---|---:|---:|---:|
| Original Jac / PostgreSQL | 62.9308 | 18 | 3.8300 |
| Optimized Jac / PostgreSQL | 49.6738 | 14 | 3.7160 |
| Conventional Java / MySQL | 45.9708 | 5 | 34.2933 |
| Conventional WeBridge / MySQL | 41.1059 | 3 | 33.9501 |
| Pruned graph Java / MySQL | 191.3729 | 7 | 174.3429 |
| Pruned graph WeBridge / MySQL | 182.5899 | 3 | 174.8731 |

These are legacy rich-instrumentation profiles, with per-frame logging and injected delay. They are diagnostic measurements, separate from the fresh compact-RTT matrix and the earlier zero-delay application-method timings. PostgreSQL server sums include verified parse/bind/execute/simple phases on all tagged backends; MySQL sums include outermost foreground statements and inclusive CALL duration, without adding nested children. Compare compiler/runtime changes within each engine; the SQL formulations, schemas and database engines differ across languages.

The measured MySQL bottleneck is the business SELECT already present in conventional Java: median SELECT server duration is 34.1725 ms directly and 33.7765 ms inside WeBridge. The SELECT returns a page of 20 and its ordinary statement events report a median 20,110 examined rows. WeBridge bundles transaction work into the CALL, reducing five exchanges to three, while retaining the same feed SELECT. Two session/transaction setup statements remain outside the CALL. The generated procedure's actual SELECT and its event IDs are retained in the raw P_S traces. These facts show where time is spent; they do not establish an optimizer access-plan cause without an actual EXPLAIN experiment.

The corrected Pruned graph pair retains three wrapped top-K graph SELECTs. WeBridge bundles them and the autocommit controls into one CALL, reducing seven exchanges to three; the inclusive server work remains about 174 ms. This measures request bundling, not a faster reformulation of those graph SELECTs.

Optimized Jac has lower measured PostgreSQL server time but still fourteen exchanges. At this injected delay the extra exchanges exceed that server-time advantage, so its summed-call RTT is higher than conventional WeBridge's. A zero-delay application timing cannot answer this separate roundtrip-time question.

`analyze.py` reproduces inventory, MySQL attribution, native flight/phase join and exact-case coverage under short shared measurement leases. The primary fields are `summed_db_call_rtt_ms` and `db_call_count`; `db_sum_ms` is explicitly server-only secondary. `mysql-request-rows.json`, `native-request-rows.json` and `paged-feed-w15-subset.json` retain the per-request observations and medians. SQL_TEXT truncation is accepted only with an exact ordered wire-prefix proof and recorded explicitly.

The existing independently gated profiles cover 61 of the 160 exact primary littleX case/arm combinations, plus five auxiliary standalone paged-feed profiles. Absence of a profile does not imply compiler failure. The final corrected init+charset Pruned mixed pair is independently gated and included; earlier emoji/collation failures remain excluded. Graph-anchor SELECT fallback categories are included in the secondary SELECT attribution, including wrapped top-K queries. Fresh compact capture removes per-frame/row logging and records the same complete-response boundary; see `FRESH_RTT_PLAN.md`.
