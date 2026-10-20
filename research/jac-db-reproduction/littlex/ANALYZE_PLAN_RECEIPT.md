# Anchors statistics and W1 query plans

The retained before/after plans explain the observed fixture-dependent W1 latency change. The same captured query and parameters, against the same fixture, select a cheaper traversal plan after `ANALYZE anchors`.

Sources:

- Before: `littlex/explain/20261019T200019Z/t20-final-fresh`
- After: `littlex/explain/20261019T200127Z/t20-final-fresh-analyzed`

Both `captured.json` files are exactly equal, including database, SQL, and parameters. SQL SHA-256: `f2c5cb3431ee8dc3c2b7e8aef35760b4abca981ae5830ffa25c3dc44efcf6916`. The index definitions in `layout.json` are exactly equal. Anchors relation statistics change from `reltuples=-1, relpages=0` to `reltuples=9303, relpages=795`.

| Boundary | Before | After |
|---|---:|---:|
| Custom plan execution median, 3 captures | 13.393 ms | 5.465 ms |
| Generic plan execution median, 3 captures | 16.637 ms | 9.844 ms |
| Custom capture 1 output rows | 1000 | 1000 |
| Custom capture 1 shared-hit blocks | 6860 | 6452 |

The key difference lies in the second-hop `Bitmap Heap Scan` over anchors, executed 50 times. Before ANALYZE its child is a `BitmapAnd` combining src/dst bitmaps with `idx_anchors_kind_type`. That kind/type index produces 7100 entries on every loop, taking 0.155 ms per loop in custom capture 1. After ANALYZE the plan uses only the src/dst `BitmapOr`, dropping the repeated kind/type bitmap. Second-hop total time falls from 0.210 to 0.056 ms per loop: approximately 7.7 ms across 50 loops. Its estimated rows improve from 1 to 13 against 20 actual rows per loop.

The first hop also drops the kind/type BitmapAnd and uses typed src/dst indexes. Its heap-scan time falls from 0.261 to 0.074 ms in the same capture. The final tweet-mirror primary-key lookup remains 1000 loops with 3000 shared-hit blocks in both plans.

Audit's separately retained same-fixture intervention reports original continuous 110-warmup/100-request headline median 23.527 → 15.312 ms after ANALYZE, close to the older fixture's 15.296 ms. The EXPLAIN measurements locate the corresponding removed database work. These are plan-level timings; the end-to-end headline additionally includes application execution and result handling.
