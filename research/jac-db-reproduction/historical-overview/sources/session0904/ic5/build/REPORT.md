# ic5 build session — REPORT (fable, 2026-09-05 15:38 → deadline 19:38; draft written 17:40, final numbers appended at the end)

Goal: make jac competitive on SNB IC5 with compiler/runtime changes only (walker text unchanged),
under a 4 h budget on a BUSY machine (so: statement counts + byte parity are the hard evidence,
milliseconds are indicative and always paired with the postgres arm measured in the same minute).

## Result so far (20 substitution rows, jac vs postgres, same window, `build/gates/ic5_<tag>.json`)
| binary | rungs | parity | statements (20 rows) | median stmts/row | jac p50 ms | pg p50 ms | jac/pg | row 19 (heaviest) |
|---|---|---|---|---|---|---|---|---|
| c12ba889d | start of session | 20/20 | 278,769 | 11,465 | 8942 | 84 | 107x | 25.5-33 s |
| 37ead25c5 | A | 20/20 | 656 | 30 | 193 | 86 | 2.24x | 453 ms |
| 341792cb0 | A+B | 20/20 | 657 | 30 | 122 | 68 | 1.78x | 288 |
| 07d6419dc | +C1 | 20/20 | 230 | 12 | 110 | 61 | 1.79x | 282 |
| 2b3bf171c | +C2 | 20/20 | 229 | 12 | 106 | 61 | 1.74x | 254 |
| 578c1c6c8 | +D1 | 20/20 | 229 | 12 | 128 | 86 | 1.49x | 234 |
| 7fcb93864 | +D2+D3 (full) | 20/20 | 269 | 14 | **69** | **51** | **1.35x** | **148 vs 61** |

Zero-forum rows are now faster on jac than postgres (row 18: 28 vs 41 ms). The remaining gap is the
heavy rows (Φ ≈ 2.5k candidate forums): 148 vs 61 ms on row 19 = 68 ms SQL + 95 ms Python (the
first nest still materialises every candidate Forum); Rung D4 (in flight at draft time) targets that.
Cross-query safety: on the full stack all 7 SNB queries hash-identical to postgres (140/140 keys),
is1/is2/is3/ic1/ic2/ic13 latencies unchanged.

## What was built (all fork commits on `pg/0831-effectpass`, each gated: parity 20/20 + stmt census)
| rung | commit | mechanism (compiler ⇄ runtime) | evidence |
|---|---|---|---|
| A | 37ead25c5 | T3 loop-prefetch matcher accepts EdgeRefTrailer collections and `dict.items()` tuple targets; runtime fills a two-level adjacency chain, one statement per level | 278k → 656 statements |
| B | 16d076c51 | EffectPass recognises the "nested edge-hop count with membership test" nest (pure body, jid-keyed sets) and lowers it to one `jhopcount(...)` SQL; every decline rule tested (11/11) | Python loop over 40k posts gone; p50 193 → 122 |
| C1 | 07d6419dc | prefetch accepts inbound hops with re-evaluable edge predicates (`joinDate > self.min_date`), predicate-keyed memo, hoists a FuncCall collection so the whole frontier fills in one statement | 657 → 230 statements |
| C2 | d2fd277fa | T6 field projection follows an edge-reference loop element through a dict alias (`D[jid(x)] = x` … `for (k,v) in D.items(): v.f`) → `refs(..., proj=(Forum, ('forum_id','title')))`, mirror-column hydration | Forum blob decodes → one 2-column mirror read |
| D1 | 578c1c6c8 | `jhopcount` plan drives from the distinct members' HasCreator rows (MATERIALIZED fences; typed scan) | 137 → 20 ms on the row-19 shape, identical rows |
| D2 | dff04b37f + 94a9181f8 | sort+slice folded into the aggregation: `jhopcount_topk(...)` returns the top-K by (count DESC, forum_id ASC) in SQL; tail loop runs over K=20 instead of Φ | 3.1 s (unfenced) → 4.5 ms plan; Python Φ→20 |
| D3 | d11329f2f | prefetch fill emits a literal-typed directed statement when the hop's types have no subtypes and predicates are pushable (drops 3 subtype subplans + 2.9k PK probes) | 20k → 3.7k buffers, order identical |
| D4 | 0235a09ee | ids-only first nest when the staged dict is read only in the top-K tail; typed `jobj` hydration of the K winners | target: −15 ms SQL, −60 ms Python on row 19 |

## Method notes
- Every rung: implementer (opus) with a written SPEC, compile-only harness (`check_*_shapes.sh`, all decline
  rules exercised), `jac check` counts unchanged, then the parent rebuilt+resealed and ran
  `gate_ic5.sh` (db-level log_statement armed BEFORE boot, 20 rows warm + census, byte parity vs the
  live pg arm, RESET after) and `snb_parity_smoke.sh` (7 queries × 20 rows vs the 0904 pg hashes).
- Traps found: db-level GUCs bind at connection time (arm before boot); a git worktree of the fork
  builds only after syncing `.pbs-build` payload inputs; postgres mis-estimates `unnest` CTEs badly enough
  that the fp-driven plan needs `AS MATERIALIZED` fences (24 s vs 20 ms); `ensure_adjacency_index`'s
  `_dst` partial index is keyed on `src_type` and is empty for heterogeneous edges; the store had no
  Forum mirror until the first projected read created it.

## Open after this session
- Heavy-row gap (row 19) after D4 — see the final numbers below.
- The `jhopcount*` builtins and the fusion stamp cover exactly the "count nested hop with membership
  test" family; ic2's hand-written `jtopk` and the littleX fused feed are the next candidates for the
  same pass (COMPILER_PLAN.md Rung C).
- Missing typed `(dst) WHERE dst_type` index on anchors (D1 note) would cut the count statement further
  at the price of write-side maintenance.

## Final numbers (appended 18:40; machine busy throughout — ratios, not milliseconds, are the claim)
| binary | rungs | parity | statements (20 rows) | median stmts/row | jac p50 ms | pg p50 ms | jac/pg | row 19 |
|---|---|---|---|---|---|---|---|---|
| D4 | +D4 (ids-only first nest, K winners via jobj) | 20/20 | 269 | 14 | 80 | 65 | 1.24x | 161 vs 74 |
| FINAL | +review fixes (BLOCK+3 RISK) | 20/20 | 269 | 14 | 110 | 76 | 1.45x | 177 vs 83 |
| D5 | +D5 (fill skips target hydration) = FINAL BINARY | 20/20 | 432 | 23 | 77 | 60 | 1.28x | 150 vs 70 |

Final binary: fork `pg/0831-effectpass` @ `32c5d1dbb` (= c12ba889d + A, B, C1, C2, D1, D2, D3, D4, review
fixes, D5), sealed 18:22. Cross-query: all 7 SNB queries hash-identical to postgres on every candidate
binary (140/140 keys each time); is1/is2/is3/ic1/ic2/ic13 latencies unchanged within the load swing.

**Verdict.** Not full parity, but a different problem than this morning: ic5 on jac went from 107x behind
postgres to 1.2-1.5x on the median row (the run-to-run band on this busy box), with rows that have no
qualifying forums now FASTER than postgres (row 18: 23 vs 41 ms) and the heaviest row (row 19, ≈2.5k
candidate forums) at ~2.1x (150-198 vs 70-83 ms). Statements per row 11,465 → 23. Walker text untouched.

Row 19 on the final binary (`stmt_durations.sh`): 198 ms = 90 ms SQL (fill 40, top-K count 28, ~20 of
per-friend existence re-checks introduced by the ids path) + 108 ms Python — no longer blob decodes; it
is psycopg row conversion of the ~2.9k-row fill (3 uuid columns), the walker's own dict/set loop over
2.9k pairs, and the flattening of ~3k (forum, member) pairs into uuid arrays for the top-K statement.

## Next (not built; the path to parity on heavy rows)
- **Rung E — whole-walker fusion.** The first nest (friends → HasMember[joinDate>d] → forums, pairs) is
  still executed in Python over Φ×F rows and then handed back to SQL as arrays. The compiler now proves
  every piece: the pairs are a pure set comprehension over a proven hop, the count is `jhopcount_topk`,
  the tail reads K hydrated winners. Fusing the pair construction into the same statement gives the
  postgres CTE verbatim: 1 statement, 20 rows out, ≈ pg latency + the ~3 ms jac dispatch floor.
- Consolidate the ids-path existence re-checks (D5's +9 statements/row) into the fill (the fast fill
  already proves the edge row; re-add the node EXISTS only for stub-typed rows).
- Typed `(dst) WHERE dst_type` partial index on `anchors` (D1 note) — cuts the count statement further.
- Generalise the fusion stamp to ic2's hand-written `jtopk` and the littleX fused feed (COMPILER_PLAN.md
  Rung C) and delete those hand restatements from the burden count.
