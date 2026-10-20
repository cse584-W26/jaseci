# littleX canonical reproduction

Validated cells: 40/40; missing: 0; errors: 0.

Current Jac: final32c5d1dbb defaults (LAZY_TXN on), Python3.14 PBS. Historical littleX reference: ad469c988 CONTROL.
SQL app and HTTP driver: separate original locked dependencies on CPython3.13.16 PBS20261013.
SQL topology: PostgreSQL16 Docker/TCP; Jac: native PostgreSQL18.
Each cell checks seed counts,100-user seed-derived feed/page parity, request counts and errors.
Write rows additionally check database-truth deltas. Latencies below are server p50 milliseconds.

| Phase | Tweets/user | Fraction | Operation | Jac final defaults | SQL | Final/SQL | Historical CONTROL/SQL |
|---|---|---|---|---:|---:|---:|---:|
| W1 | t100 |  | feed | 49.667 | 26.543 | 1.87 | 1.99 |
| W1 | t20 |  | feed | 23.466 | 5.130 | 4.57 | 3.14 |
| W1 | t200 |  | feed | 107.435 | 54.130 | 1.98 | 1.98 |
| W1 | t50 |  | feed | 28.060 | 12.963 | 2.16 | 2.12 |
| W2 | t100 |  | create_tweet | 2.946 | 1.345 | 2.19 | 1.18 |
| W2 | t100 |  | follow | 3.751 | 1.373 | 2.73 | 1.28 |
| W2 | t100 |  | like | 3.096 | 1.399 | 2.21 | 1.18 |
| W2 | t20 |  | create_tweet | 3.144 | 1.337 | 2.35 | 0.87 |
| W2 | t20 |  | follow | 4.060 | 1.345 | 3.02 | 0.92 |
| W2 | t20 |  | like | 3.238 | 1.419 | 2.28 | 0.86 |
| W2 | t200 |  | create_tweet | 2.971 | 1.465 | 2.03 | 1.20 |
| W2 | t200 |  | follow | 3.905 | 1.371 | 2.85 | 1.64 |
| W2 | t200 |  | like | 3.209 | 1.384 | 2.32 | 1.53 |
| W2 | t50 |  | create_tweet | 2.934 | 1.387 | 2.12 | 1.58 |
| W2 | t50 |  | follow | 3.703 | 1.328 | 2.79 | 1.69 |
| W2 | t50 |  | like | 3.124 | 1.346 | 2.32 | 1.59 |
| W3 | t200 | 0 | feed_page | 3.763 | 4.718 | 0.80 | 0.77 |
| W3 | t200 | 15 | create_tweet | 3.096 | 1.524 | 2.03 | 1.55 |
| W3 | t200 | 15 | feed_page | 3.764 | 4.780 | 0.79 | 0.75 |
| W3 | t200 | 15 | follow | 4.048 | 1.547 | 2.62 | 1.65 |
| W3 | t200 | 15 | like | 3.219 | 1.540 | 2.09 | 1.56 |
| W3 | t200 | 30 | create_tweet | 3.020 | 1.439 | 2.10 | 1.57 |
| W3 | t200 | 30 | feed_page | 3.725 | 4.808 | 0.77 | 0.77 |
| W3 | t200 | 30 | follow | 3.908 | 1.456 | 2.68 | 1.68 |
| W3 | t200 | 30 | like | 3.128 | 1.440 | 2.17 | 1.58 |
| W3 | t200 | 5 | create_tweet | 3.234 | 1.937 | 1.67 | 1.46 |
| W3 | t200 | 5 | feed_page | 3.805 | 4.617 | 0.82 | 0.74 |
| W3 | t200 | 5 | follow | 4.161 | 1.596 | 2.61 | 1.56 |
| W3 | t200 | 5 | like | 3.369 | 1.977 | 1.70 | 1.49 |
