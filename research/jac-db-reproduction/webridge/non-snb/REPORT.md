# Jac DB and WeBridge: measured database round trips

[English PDF slides](jac-webridge-tpcc-littlex-comparison.pdf) · [Primary JSON](results.json) · [Primary CSV](results.csv) · [Measurement boundary](RTT_MEASUREMENT_PLAN.md)

The primary value is the **median per-request sum of complete SQL command/response RTTs**. The compact proxy starts each timer at frontend command arrival and stops it after complete response delivery to the client-facing connection. SQL counts use those same requests. Database execution, result transfer, communication, configured delay and compact instrumentation are included; application computation between calls is outside the boundary.

Jac uses PostgreSQL 18; Java and WeBridge use MySQL 5.7. Each baseline/optimized pair holds its database engine and program representation fixed. Cross-engine absolute timings describe these implementations. Exact source commits and settings appear in [runtime-provenance.json](runtime-provenance.json).

A CALL counts as one client SQL command. Nested procedure statements are retained in the detailed SQL-work profiles. PostgreSQL preparation-only exchanges contribute RTT and exchange counts but do not count as executed SQL commands. Observer and outside-request initialization queries are excluded; SQL initialization triggered inside a request remains included. Per-request count ranges below accompany exact histograms in JSON/CSV.

## Coverage

27 logical workloads × eight configurations × three response delays = **648 latency cells**. Pure operations use ten warmup and thirty measured requests; mixed latency uses 110 warmup and one complete 100-slot measured schedule. The **168 original-schedule references** retain their own original lengths and correctness outcomes.

| Configuration | Accepted latency cells | Compiler-stage failures | Accepted references | Other reference outcomes |
|---|---:|---:|---:|---:|
| Jac unoptimized | 81 | 0 | 21 | 0 |
| Jac optimized | 81 | 0 | 21 | 0 |
| Jac-like Java, direct | 81 | 0 | 21 | 0 |
| WeBridge, Jac-like Java | 0 | 81 | 1 | 20 |
| Original SQL Java, direct | 81 | 0 | 21 | 0 |
| WeBridge, original SQL Java | 66 | 15 | 20 | 1 |
| Pruned Java, direct | 81 | 0 | 21 | 0 |
| WeBridge, pruned Java | 24 | 57 | 9 | 12 |

## Per-workload RTT and query counts

All RTT values are milliseconds. Count cells show the per-request SQL command range. Compiler-stage failures link to their recorded stage receipts. Each case links to the complete raw/gate index in results.json.

### TPC-C: payment name GC

Median summed SQL round-trip time per request (ms); added database-response delay by column

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 3.976 | 31.993 | 135.226 | 12 | 12 | 12 |
| Jac optimized | 4.197 | 31.811 | 134.122 | 12 | 12 | 12 |
| Jac-like Java, direct | 52.438 | 65.424 | 169.971 | 12 | 12 | 12 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.838 | 24.480 | 97.421 | 9 | 9 | 9 |
| WeBridge, original SQL Java | 3.229 | 5.302 | 43.694 | 1 | 1 | 1 |
| Pruned Java, direct | 36.754 | 55.120 | 124.771 | 8 | 8 | 8 |
| WeBridge, pruned Java | replay failed | replay failed | replay failed | — | — | — |

Evidence key: `tpcc-payment_name_GC` in [results.json](results.json).

### TPC-C: new order rollback

Median summed SQL round-trip time per request (ms); added database-response delay by column

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 5.628 | 47.938 | 199.732 | 17 | 17 | 17 |
| Jac optimized | 5.757 | 51.998 | 196.886 | 17 | 17 | 17 |
| Jac-like Java, direct | 31.643 | 74.195 | 218.079 | 17 | 17 | 17 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 11.599 | 144.703 | 628.463 | 58 | 58 | 58 |
| WeBridge, original SQL Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |
| Pruned Java, direct | 32.843 | 62.079 | 156.333 | 12 | 12 | 12 |
| WeBridge, pruned Java | replay failed | replay failed | replay failed | — | — | — |

Evidence key: `tpcc-new_order_rollback` in [results.json](results.json).

### TPC-C: payment id GC

Median summed SQL round-trip time per request (ms); added database-response delay by column

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 5.252 | 26.248 | 112.069 | 10 | 10 | 10 |
| Jac optimized | 3.049 | 31.627 | 110.373 | 10 | 10 | 10 |
| Jac-like Java, direct | 7.010 | 29.606 | 113.894 | 10 | 10 | 10 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.761 | 24.635 | 99.329 | 9 | 9 | 9 |
| WeBridge, original SQL Java | 3.167 | 5.238 | 14.407 | 1 | 1 | 1 |
| Pruned Java, direct | 6.076 | 23.547 | 79.183 | 7 | 7 | 7 |
| WeBridge, pruned Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |

Evidence key: `tpcc-payment_id_GC` in [results.json](results.json).

### TPC-C: new order 5

Median summed SQL round-trip time per request (ms); added database-response delay by column

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 4.548 | 45.940 | 158.337 | 14 | 14 | 14 |
| Jac optimized | 5.206 | 37.969 | 160.017 | 14 | 14 | 14 |
| Jac-like Java, direct | 19.152 | 50.430 | 169.886 | 14 | 14 | 14 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 6.866 | 75.455 | 305.820 | 28 | 28 | 28 |
| WeBridge, original SQL Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |
| Pruned Java, direct | 16.597 | 38.303 | 107.876 | 9 | 9 | 9 |
| WeBridge, pruned Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |

Evidence key: `tpcc-new_order_5` in [results.json](results.json).

### TPC-C: new order 15

Median summed SQL round-trip time per request (ms); added database-response delay by column

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 7.255 | 38.064 | 162.049 | 14 | 14 | 14 |
| Jac optimized | 6.963 | 40.034 | 157.661 | 14 | 14 | 14 |
| Jac-like Java, direct | 28.881 | 62.295 | 177.690 | 14 | 14 | 14 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 13.489 | 170.891 | 736.115 | 68 | 68 | 68 |
| WeBridge, original SQL Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |
| Pruned Java, direct | 31.315 | 50.038 | 121.210 | 9 | 9 | 9 |
| WeBridge, pruned Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |

Evidence key: `tpcc-new_order_15` in [results.json](results.json).

### TPC-C: payment name BC

Median summed SQL round-trip time per request (ms); added database-response delay by column

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 3.906 | 52.597 | 125.679 | 11 | 11 | 11 |
| Jac optimized | 3.966 | 30.095 | 122.558 | 11 | 11 | 11 |
| Jac-like Java, direct | 34.651 | 58.597 | 154.327 | 11 | 11 | 11 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 4.515 | 26.908 | 110.478 | 10 | 10 | 10 |
| WeBridge, original SQL Java | install failed | install failed | install failed | — | — | — |
| Pruned Java, direct | 33.130 | 48.391 | 108.222 | 7 | 7 | 7 |
| WeBridge, pruned Java | replay failed | replay failed | replay failed | — | — | — |

Evidence key: `tpcc-payment_name_BC` in [results.json](results.json).

### TPC-C: payment id BC

Median summed SQL round-trip time per request (ms); added database-response delay by column

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 3.602 | 27.595 | 112.899 | 10 | 10 | 10 |
| Jac optimized | 3.447 | 25.619 | 111.039 | 10 | 10 | 10 |
| Jac-like Java, direct | 6.721 | 29.503 | 112.814 | 10 | 10 | 10 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.750 | 27.143 | 109.368 | 10 | 10 | 10 |
| WeBridge, original SQL Java | install failed | install failed | install failed | — | — | — |
| Pruned Java, direct | 5.874 | 22.333 | 80.325 | 7 | 7 | 7 |
| WeBridge, pruned Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |

Evidence key: `tpcc-payment_id_BC` in [results.json](results.json).

### littleX: feed

Median summed SQL round-trip time per request (ms); added database-response delay by column; 20 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 13.635 | 59.895 | 227.773 | 18–19 | 18–19 | 18–20 |
| Jac optimized | 13.167 | 46.501 | 173.629 | 14–15 | 14–15 | 14–15 |
| Jac-like Java, direct | 74.162 | 116.976 | 295.529 | 20 | 20 | 20 |
| WeBridge, Jac-like Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |
| Original SQL Java, direct | 9.516 | 18.082 | 59.959 | 5 | 5 | 5 |
| WeBridge, original SQL Java | 9.181 | 13.205 | 38.950 | 3 | 3 | 3 |
| Pruned Java, direct | 57.003 | 69.139 | 139.141 | 7 | 7 | 7 |
| WeBridge, pruned Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |

Evidence key: `littlex-feed-t20` in [results.json](results.json).

### littleX: like

Median summed SQL round-trip time per request (ms); added database-response delay by column; 20 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 3.061 | 29.912 | 133.074 | 10–12 | 10–12 | 10–12 |
| Jac optimized | 2.876 | 27.601 | 117.893 | 9–11 | 9–11 | 9–11 |
| Jac-like Java, direct | 15.404 | 43.106 | 144.672 | 11–12 | 11–12 | 11–12 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.607 | 16.952 | 66.872 | 6 | 6 | 6 |
| WeBridge, original SQL Java | 3.032 | 9.930 | 34.650 | 3 | 3 | 3 |
| Pruned Java, direct | 13.849 | 30.073 | 87.390 | 7 | 7 | 7 |
| WeBridge, pruned Java | replay failed | replay failed | replay failed | — | — | — |

Evidence key: `littlex-like-t20` in [results.json](results.json).

### littleX: follow

Median summed SQL round-trip time per request (ms); added database-response delay by column; 20 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 4.040 | 33.408 | 139.403 | 12–13 | 12–13 | 12–13 |
| Jac optimized | 3.690 | 31.617 | 129.327 | 11–12 | 11–12 | 11–12 |
| Jac-like Java, direct | 24.858 | 57.402 | 163.721 | 13 | 13 | 13 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.556 | 14.378 | 55.141 | 5 | 5 | 5 |
| WeBridge, original SQL Java | 3.038 | 10.180 | 34.477 | 3 | 3 | 3 |
| Pruned Java, direct | 23.072 | 41.182 | 110.595 | 8 | 8 | 8 |
| WeBridge, pruned Java | replay failed | replay failed | replay failed | — | — | — |

Evidence key: `littlex-follow-t20` in [results.json](results.json).

### littleX: create tweet

Median summed SQL round-trip time per request (ms); added database-response delay by column; 20 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 2.892 | 24.491 | 105.201 | 9–10 | 9–10 | 9–10 |
| Jac optimized | 2.823 | 22.830 | 96.237 | 8–9 | 8–9 | 8–9 |
| Jac-like Java, direct | 15.174 | 38.443 | 121.261 | 10 | 10 | 10 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.297 | 45.990 | 65.652 | 6 | 6 | 6 |
| WeBridge, original SQL Java | 3.714 | 9.889 | 34.447 | 3 | 3 | 3 |
| Pruned Java, direct | 13.972 | 27.236 | 77.546 | 6 | 6 | 6 |
| WeBridge, pruned Java | 16.878 | 31.166 | 83.423 | 6 | 6 | 6 |

Evidence key: `littlex-create_tweet-t20` in [results.json](results.json).

### littleX: feed

Median summed SQL round-trip time per request (ms); added database-response delay by column; 50 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 21.522 | 68.762 | 235.201 | 18–19 | 18–20 | 18–20 |
| Jac optimized | 21.471 | 56.598 | 188.104 | 14–15 | 14–16 | 14–16 |
| Jac-like Java, direct | 198.162 | 170.442 | 350.691 | 20 | 20 | 20 |
| WeBridge, Jac-like Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |
| Original SQL Java, direct | 21.506 | 29.934 | 72.400 | 5 | 5 | 5 |
| WeBridge, original SQL Java | 20.919 | 25.173 | 49.341 | 3 | 3 | 3 |
| Pruned Java, direct | 112.314 | 124.392 | 186.286 | 7 | 7 | 7 |
| WeBridge, pruned Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |

Evidence key: `littlex-feed-t50` in [results.json](results.json).

### littleX: like

Median summed SQL round-trip time per request (ms); added database-response delay by column; 50 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 3.159 | 30.555 | 131.272 | 10–12 | 10–12 | 10–12 |
| Jac optimized | 2.958 | 27.621 | 118.156 | 9–11 | 9–11 | 9–11 |
| Jac-like Java, direct | 19.485 | 46.813 | 145.231 | 11–12 | 11–12 | 11–12 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.224 | 17.115 | 65.681 | 6 | 6 | 6 |
| WeBridge, original SQL Java | 34.273 | 9.936 | 34.277 | 3 | 3 | 3 |
| Pruned Java, direct | 18.298 | 34.314 | 100.141 | 7 | 7 | 7 |
| WeBridge, pruned Java | replay failed | replay failed | replay failed | — | — | — |

Evidence key: `littlex-like-t50` in [results.json](results.json).

### littleX: follow

Median summed SQL round-trip time per request (ms); added database-response delay by column; 50 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 3.815 | 32.908 | 142.927 | 12–13 | 12–13 | 12–13 |
| Jac optimized | 3.508 | 31.449 | 131.700 | 11–12 | 11–12 | 11–12 |
| Jac-like Java, direct | 33.664 | 61.804 | 177.436 | 13 | 13 | 13 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.189 | 14.456 | 55.352 | 5 | 5 | 5 |
| WeBridge, original SQL Java | 2.875 | 9.723 | 34.313 | 3 | 3 | 3 |
| Pruned Java, direct | 31.623 | 49.002 | 124.138 | 8 | 8 | 8 |
| WeBridge, pruned Java | replay failed | replay failed | replay failed | — | — | — |

Evidence key: `littlex-follow-t50` in [results.json](results.json).

### littleX: create tweet

Median summed SQL round-trip time per request (ms); added database-response delay by column; 50 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 2.875 | 24.910 | 108.332 | 9–10 | 9–10 | 9–10 |
| Jac optimized | 2.651 | 23.645 | 96.941 | 8–9 | 8–9 | 8–9 |
| Jac-like Java, direct | 19.204 | 43.988 | 125.045 | 10 | 10 | 10 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.623 | 17.067 | 66.360 | 6 | 6 | 6 |
| WeBridge, original SQL Java | 2.989 | 10.186 | 34.925 | 3 | 3 | 3 |
| Pruned Java, direct | 18.068 | 34.028 | 87.835 | 6 | 6 | 6 |
| WeBridge, pruned Java | 20.952 | 35.040 | 90.544 | 6 | 6 | 6 |

Evidence key: `littlex-create_tweet-t50` in [results.json](results.json).

### littleX: feed

Median summed SQL round-trip time per request (ms); added database-response delay by column; 100 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 34.757 | 77.988 | 246.856 | 18–20 | 18–20 | 18–20 |
| Jac optimized | 34.347 | 68.041 | 202.999 | 14–16 | 14–16 | 14–16 |
| Jac-like Java, direct | 212.910 | 261.643 | 429.542 | 20 | 20 | 20 |
| WeBridge, Jac-like Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |
| Original SQL Java, direct | 41.516 | 49.951 | 85.212 | 5 | 5 | 5 |
| WeBridge, original SQL Java | 40.648 | 44.770 | 62.960 | 3 | 3 | 3 |
| Pruned Java, direct | 205.008 | 226.745 | 270.647 | 7 | 7 | 7 |
| WeBridge, pruned Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |

Evidence key: `littlex-feed-t100` in [results.json](results.json).

### littleX: like

Median summed SQL round-trip time per request (ms); added database-response delay by column; 100 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 3.154 | 30.088 | 130.738 | 10–12 | 10–12 | 10–12 |
| Jac optimized | 2.954 | 29.406 | 116.897 | 9–11 | 9–11 | 9–11 |
| Jac-like Java, direct | 26.278 | 53.522 | 156.497 | 11–12 | 11–12 | 11–12 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.348 | 16.781 | 65.708 | 6 | 6 | 6 |
| WeBridge, original SQL Java | 3.377 | 10.232 | 34.846 | 3 | 3 | 3 |
| Pruned Java, direct | 25.106 | 40.472 | 104.084 | 7 | 7 | 7 |
| WeBridge, pruned Java | replay failed | replay failed | replay failed | — | — | — |

Evidence key: `littlex-like-t100` in [results.json](results.json).

### littleX: follow

Median summed SQL round-trip time per request (ms); added database-response delay by column; 100 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 3.737 | 34.212 | 141.150 | 12–13 | 12–13 | 12–13 |
| Jac optimized | 3.838 | 31.269 | 128.827 | 11–12 | 11–12 | 11–12 |
| Jac-like Java, direct | 47.127 | 74.968 | 201.741 | 13 | 13 | 13 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 2.848 | 14.618 | 55.474 | 5 | 5 | 5 |
| WeBridge, original SQL Java | 3.397 | 9.805 | 35.155 | 3 | 3 | 3 |
| Pruned Java, direct | 44.796 | 62.629 | 136.918 | 8 | 8 | 8 |
| WeBridge, pruned Java | replay failed | replay failed | replay failed | — | — | — |

Evidence key: `littlex-follow-t100` in [results.json](results.json).

### littleX: create tweet

Median summed SQL round-trip time per request (ms); added database-response delay by column; 100 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 2.847 | 24.665 | 106.722 | 9–10 | 9–10 | 9–10 |
| Jac optimized | 2.734 | 24.201 | 97.037 | 8–9 | 8–9 | 8–9 |
| Jac-like Java, direct | 26.339 | 48.229 | 137.451 | 10 | 10 | 10 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.432 | 17.119 | 65.889 | 6 | 6 | 6 |
| WeBridge, original SQL Java | 3.240 | 9.812 | 34.641 | 3 | 3 | 3 |
| Pruned Java, direct | 24.964 | 38.058 | 97.026 | 6 | 6 | 6 |
| WeBridge, pruned Java | 27.831 | 41.468 | 101.787 | 6 | 6 | 6 |

Evidence key: `littlex-create_tweet-t100` in [results.json](results.json).

### littleX: feed

Median summed SQL round-trip time per request (ms); added database-response delay by column; 200 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 63.798 | 108.687 | 274.085 | 18–20 | 18–20 | 18–20 |
| Jac optimized | 62.822 | 96.185 | 237.698 | 14–16 | 14–16 | 14–16 |
| Jac-like Java, direct | 401.730 | 445.802 | 602.334 | 20 | 20 | 20 |
| WeBridge, Jac-like Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |
| Original SQL Java, direct | 81.531 | 90.311 | 125.955 | 5 | 5 | 5 |
| WeBridge, original SQL Java | 81.098 | 83.841 | 102.758 | 3 | 3 | 3 |
| Pruned Java, direct | 380.957 | 396.844 | 441.456 | 7 | 7 | 7 |
| WeBridge, pruned Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |

Evidence key: `littlex-feed-t200` in [results.json](results.json).

### littleX: like

Median summed SQL round-trip time per request (ms); added database-response delay by column; 200 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 3.174 | 30.648 | 128.324 | 10–12 | 10–12 | 10–12 |
| Jac optimized | 2.988 | 29.604 | 118.687 | 9–11 | 9–11 | 9–11 |
| Jac-like Java, direct | 40.343 | 68.348 | 171.354 | 11–12 | 11–12 | 11–12 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.408 | 17.088 | 66.306 | 6 | 6 | 6 |
| WeBridge, original SQL Java | 2.879 | 9.644 | 34.650 | 3 | 3 | 3 |
| Pruned Java, direct | 39.193 | 53.301 | 117.445 | 7 | 7 | 7 |
| WeBridge, pruned Java | replay failed | replay failed | replay failed | — | — | — |

Evidence key: `littlex-like-t200` in [results.json](results.json).

### littleX: follow

Median summed SQL round-trip time per request (ms); added database-response delay by column; 200 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 4.080 | 33.479 | 143.446 | 12–13 | 12–13 | 12–13 |
| Jac optimized | 3.899 | 32.281 | 129.758 | 11–12 | 11–12 | 11–12 |
| Jac-like Java, direct | 75.287 | 103.199 | 232.986 | 13 | 13 | 13 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.681 | 14.463 | 55.419 | 5 | 5 | 5 |
| WeBridge, original SQL Java | 3.123 | 9.429 | 34.518 | 3 | 3 | 3 |
| Pruned Java, direct | 72.700 | 90.182 | 161.611 | 8 | 8 | 8 |
| WeBridge, pruned Java | replay failed | replay failed | replay failed | — | — | — |

Evidence key: `littlex-follow-t200` in [results.json](results.json).

### littleX: create tweet

Median summed SQL round-trip time per request (ms); added database-response delay by column; 200 tweets / user

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 2.924 | 26.044 | 106.582 | 9–10 | 9–10 | 9–10 |
| Jac optimized | 2.673 | 22.749 | 97.244 | 8–9 | 8–9 | 8–9 |
| Jac-like Java, direct | 40.240 | 62.555 | 152.542 | 10 | 10 | 10 |
| WeBridge, Jac-like Java | replay failed | replay failed | replay failed | — | — | — |
| Original SQL Java, direct | 3.479 | 17.282 | 65.996 | 6 | 6 | 6 |
| WeBridge, original SQL Java | 3.157 | 9.710 | 34.622 | 3 | 3 | 3 |
| Pruned Java, direct | 38.997 | 52.474 | 111.838 | 6 | 6 | 6 |
| WeBridge, pruned Java | 41.972 | 55.299 | 112.178 | 6 | 6 | 6 |

Evidence key: `littlex-create_tweet-t200` in [results.json](results.json).

### littleX: mixed

Median summed SQL round-trip time per request (ms); added database-response delay by column; 200 tweets / user; 0% writes

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 5.339 | 47.304 | 203.096 | 18 | 18–19 | 18–19 |
| Jac optimized | 4.849 | 37.212 | 158.176 | 14–15 | 14–15 | 14–15 |
| Jac-like Java, direct | 188.905 | 233.804 | 409.586 | 20 | 20 | 20 |
| WeBridge, Jac-like Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |
| Original SQL Java, direct | 34.494 | 45.816 | 101.036 | 5 | 5 | 5 |
| WeBridge, original SQL Java | 34.427 | 41.158 | 71.305 | 3 | 3 | 3 |
| Pruned Java, direct | 167.571 | 184.279 | 248.471 | 7 | 7 | 7 |
| WeBridge, pruned Java | 167.681 | 173.817 | 204.369 | 3 | 3 | 3 |

Evidence key: `littlex-mixed-t200-w0` in [results.json](results.json).

### littleX: mixed

Median summed SQL round-trip time per request (ms); added database-response delay by column; 200 tweets / user; 5% writes

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 4.874 | 47.426 | 200.206 | 9–18 | 9–19 | 9–19 |
| Jac optimized | 4.977 | 36.867 | 158.096 | 8–30 | 8–15 | 8–15 |
| Jac-like Java, direct | 189.375 | 230.576 | 413.212 | 10–20 | 10–20 | 10–20 |
| WeBridge, Jac-like Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |
| Original SQL Java, direct | 34.548 | 45.641 | 98.782 | 5–6 | 5–6 | 5–6 |
| WeBridge, original SQL Java | 34.468 | 40.805 | 69.998 | 3 | 3 | 3 |
| Pruned Java, direct | 167.858 | 184.628 | 248.927 | 6–8 | 6–8 | 6–8 |
| WeBridge, pruned Java | 166.791 | 175.194 | 203.239 | 3–8 | 3–8 | 3–8 |

Evidence key: `littlex-mixed-t200-w5` in [results.json](results.json).

### littleX: mixed

Median summed SQL round-trip time per request (ms); added database-response delay by column; 200 tweets / user; 15% writes

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 4.850 | 45.853 | 200.382 | 9–18 | 9–19 | 9–19 |
| Jac optimized | 4.542 | 36.232 | 154.887 | 8–14 | 8–15 | 8–15 |
| Jac-like Java, direct | 188.449 | 233.392 | 407.199 | 10–20 | 10–20 | 10–20 |
| WeBridge, Jac-like Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |
| Original SQL Java, direct | 34.489 | 45.312 | 89.106 | 5–6 | 5–6 | 5–6 |
| WeBridge, original SQL Java | 34.239 | 40.722 | 68.957 | 3 | 3 | 3 |
| Pruned Java, direct | 167.970 | 183.560 | 250.123 | 6–8 | 6–8 | 6–8 |
| WeBridge, pruned Java | 166.739 | 176.605 | 203.823 | 3–8 | 3–8 | 3–8 |

Evidence key: `littlex-mixed-t200-w15` in [results.json](results.json).

### littleX: mixed

Median summed SQL round-trip time per request (ms); added database-response delay by column; 200 tweets / user; 30% writes

| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Jac unoptimized | 4.594 | 45.061 | 194.285 | 9–18 | 9–19 | 9–19 |
| Jac optimized | 4.320 | 35.367 | 155.276 | 8–14 | 8–15 | 8–15 |
| Jac-like Java, direct | 188.732 | 230.498 | 404.032 | 10–20 | 10–20 | 10–20 |
| WeBridge, Jac-like Java | synthesis failed | synthesis failed | synthesis failed | — | — | — |
| Original SQL Java, direct | 34.305 | 45.330 | 87.375 | 5–6 | 5–6 | 5–6 |
| WeBridge, original SQL Java | 34.384 | 40.601 | 67.162 | 3 | 3 | 3 |
| Pruned Java, direct | 167.806 | 184.974 | 244.933 | 6–8 | 6–8 | 6–8 |
| WeBridge, pruned Java | 165.570 | 175.482 | 204.713 | 3–8 | 3–8 | 3–8 |

Evidence key: `littlex-mixed-t200-w30` in [results.json](results.json).

## Evidence and independent verification

- [Original reference schedules and actual procedure routing](rtt-reference-results.json), with [CSV timings and counts](rtt-reference-results.csv).
- [Same-request command/exchange evidence](rtt-cycle-evidence.json).
- [Fresh compact-RTT SQL attribution](profiles/primary-rtt-attribution/final/MEASURED_FINDINGS.md): source-aware categories, additive mean costs, exact SQL hashes and per-request reconciliation.
- [Independent raw RTT verifier](verify_rtt_results.py): recomputes timestamps, request sums, medians and counts; checks all connections at request boundaries.
- [Detailed SQL-work attribution](profiles/paged-feed-cost-analysis/EXPLANATION.md): earlier rich-trace diagnostic with explicit sample and transport scope.
- [Archive verifier](verify_archive.py), [indexed-stream verifier](verify_chunks.py) and [result-link verifier](verify_result_links.py).
- [Methods](METHODS.md), [workload contracts](workload-contracts.json) and [seed inputs](seed-inputs).

Earlier application timings and server-only profiles retain separate timer definitions and coverage in their original artifacts. The primary tables above are generated from compact RTT measurements.

## Rebuild the report from collected evidence

```bash
python collect_cycle_evidence.py
python collect_references.py --native native/normalized-rtt-reference.json --littlex littlex/normalized-rtt-results.json
python aggregate_results.py
python verify_rtt_results.py . --out final-rtt-verification.json
python profiles/primary-rtt-attribution/analyze.py --results results.json --out profiles/primary-rtt-attribution/rebuilt
python build_report.py
python build_pdf.py --attribution profiles/primary-rtt-attribution/rebuilt/attribution.json
```

Run live collectors and heavy analyses under the shared measurement lease when any experiments are active.

Primary results SHA-256: `a9f769b43ab6e862c07cd63c93870331d080655c0251763a1faaca9991787870`.
