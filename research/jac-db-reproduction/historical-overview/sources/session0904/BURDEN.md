# Phase BURDEN — session0904 (2026-09-04)

Re-derived the SNB Jac burden copy from the T7 served app; checked TPC-C and
littleX copies against their served apps; regenerated the four viewers,
`viewer_counts.csv`, `burden.csv` and the `FORMAT_FAIRNESS.md` counts table.

Artifact publish (steps/BURDEN.md step 4) is NOT done here — owned by the
parent fable session.

## Counts before -> after (`viewer_counts.csv`)

LoC / dbloc / non-ws chars / non-ws chars on dbloc lines.

| bench | arm | before | after |
|---|---|---|---|
| SNB | **Jac** | **361 / 46 / 6491 / 1482** | **320 / 45 / 5761 / 1541** |
| SNB | PostgreSQL | 315 / 178 / 6868 / 4718 | unchanged |
| SNB | SQLAlchemy | 330 / 91 / 6947 / 2472 | unchanged |
| SNB | Neo4j | 202 / 71 / 4374 / 2154 | unchanged |
| TPC-C | Jac | 225 / 14 / 4146 / 401 | unchanged |
| TPC-C | PostgreSQL | 302 / 197 / 7435 / 5695 | unchanged |
| TPC-C | SQLAlchemy | 232 / 117 / 6286 / 3701 | unchanged |
| littleX | Jac | 174 / 27 / 3049 / 726 | unchanged |
| littleX | PostgreSQL | 250 / 101 / 6127 / 2888 | unchanged |
| littleX | SQLAlchemy | 281 / 68 / 7130 / 2302 | unchanged |
| littleX | Neo4j | 229 / 75 / 6429 / 2544 | unchanged |

Entity-rep counts did not move on any arm (SNB Jac stays 1 rep each for
Person / Knows / Place / Forum / ForumMember / Post / Comment).

Headline: on SNB, Jac moves from **highest** LoC of the four arms (361, above
SQLA 330) to **third**, 5 lines above PostgreSQL (320 vs 315) and below SQLA
(330); neo4j stays lowest at 202. Jac remains lowest LoC on littleX and
TPC-C, and lowest non-ws chars on every bench/arm except SNB neo4j
(SNB Jac 5761 vs PG 6868 / SQLA 6947 / neo4j 4374). SNB Jac dbloc 45 is still
~4x below PostgreSQL's 178 and 2x below SQLAlchemy's 91.

## What changed in `apps/snb/jac/app.jac` (387 -> 346 raw lines, 361 -> 320 LoC)

Re-derived from `benchmark/snb/jaseci-pg/app.jac`, verified byte-identical to
`session0901/opt_ladder/T7/app.jac.T7` (`diff -q` clean). Two T7 constructs
land in the copy:

1. **Typed lookup** — `p = jobj(self.person_jid)` + the 4-line
   `if not isinstance(p, Person) { report {...}; return; }` narrow becomes
   `p = jobj(self.person_jid, Person)`. 9 guard blocks removed
   (is1, is2, is3, ic1, ic2, ic5, ic13, add_post, add_friendship) = -36 lines.
2. **Variable-length hop syntax** — ic1's
   `jclosure(jid(start), "Knows", Person, 3, "firstName", self.first_name)` +
   its 8-line hydrate/re-filter loop becomes
   `for (f, dist) in [start<-:Knows:*3:->[?:Person, firstName==self.first_name]]`
   (-4 lines); ic13's
   `jclosure(jid(a), "Knows", Person, 6, "person_id", str(b.person_id))` plus
   the separate `length =` binding becomes
   `hits = [a<-:Knows:*6:->[?:Person, person_id==b.person_id]];` with the
   report inlined (-1 line).

36 + 4 + 1 = 41 = the LoC delta.

dbloc 46 -> 45: ic1's `f = jobj(h[0])` hydration line is gone; both `jclosure`
lines were replaced 1:1 by hop lines (both classified dbloc — the Jac rule
matches `<-:` / `:->`). dbchars rose 1482 -> 1541: fewer but denser
data-access lines.

Everything else in the copy is byte-identical to the pre-T7 copy — `jac fmt`
changed nothing outside the patched regions.

### Verification

- `diff -q benchmark/snb/jaseci-pg/app.jac session0901/opt_ladder/T7/app.jac.T7`
  → identical.
- A per-declaration comparator (strip comments/blanks/whitespace, strip
  instrumentation from the served side) reports every kept declaration OK
  against the served text. The only remaining differences are the two
  documented rules: the `if CTE_TRAVERSE {} else {}` / `if batched {}`
  collapse in **is2** and **ic2** (CLASSIFY.md step 5), and `jac fmt`
  normalisation (`lambda (e: list)` -> `lambda e: list`).
- Dropped from the copy, exactly as CLASSIFY.md step 5 requires:
  `import os`, `glob CTE_TRAVERSE`, `_neighbors_batch`, `ic1_lvl`, `ic2_lvl`,
  `ic5_lvl`, `ic1_depth`, `pymk`.
- `jac check` (sealed T7 binary `session0904/T7b/jac-t7-832374734`, lambdas
  converted to that fork's `lambda (x: T)` spelling): copy **6 errors**, served
  app **14 errors** — same pre-existing class on both
  (`E1030 Type "HasCreator" has no attribute "__jac__"` ×4 from the
  `edge ... __jac__.source.archetype` idiom in is2/ic2, `E1054` jtopk overload
  ×2). No new error class; the copy has fewer only because the dropped
  `_lvl`/`pymk` walkers carried the rest.

### Formatter note (real, worth knowing)

The two forks' `jac fmt` disagree. `PATH jac` (symlink →
`JaseciFork/jac/zig-out/bin/jac`) emits `lambda e: list {` and cannot parse
the T7 hop; the sealed pg-fork binary emits `lambda (e: list) {` and cannot
parse `lambda e: list`. The copies have been PATH-`jac fmt` style since 0903,
so that style was kept (the difference is 0 lines and 0 dbloc — it only
changes spellings inside single lines, so no count is affected). Mechanics:
the two hop expressions were swapped for equal-length string placeholders,
`jac fmt app.jac` was run, and the hops were swapped back — so the formatting
of every other line is genuine `jac fmt` output.

## TPC-C and littleX: NOT re-derived (verified unchanged)

Same per-declaration comparator, served vs copy:

- **TPC-C** (`benchmark/tpcc/jaseci-pg/app.jac`, incl. the idiom-pass commit
  `06915ac`: `+=`, `all(...)`, `enumerate`): every node/edge and both burden
  walkers (`new_order`, `payment`) match the served text exactly. The only
  deltas are the documented instrumentation strip (`t0: float = 0.0`,
  `self.t0 = time.perf_counter()`, which turns the previous `has` field's
  trailing `,` into `;`) and the `lambda ( )` spelling. **The copy already
  carried the 06915ac idioms** — no regen needed.
- **littleX** (`littleXs/jaseci-pg/app.jac`, unchanged since `14520df`): all
  kept walkers match; deltas are the instrumentation strip (including
  `"server_total_ms"` keys removed from `report {}` dicts) and `jac fmt`
  spellings (`def _now()`, `dict[(str, str)]`). Dropped set unchanged:
  `import time`, `_now`, `load_feed_leaf`, `load_feed_chain`,
  `load_feed_page_chain`. No regen needed.

## `burden.csv`

Regenerated with `collect.py` — it had **not** been re-harvested since the
`jaseci-pg` app dirs were added, so it carried only `jac-lti` rows: 67 rows →
**108 rows**, now including every `snb/jaseci-pg` and `tpcc/jaseci-pg`
annotation (`arm=jaseci-pg`, `jaseci-pg-cte`, `jaseci-pg-lvl`). The `arm`
column never carried the `(JAC_CTE_TRAVERSE=1)` suffix — `collect.py`'s
`arm=(\S+)` capture stops at the space — so nothing to strip there. The T7
walker annotations in the served app were already updated by the T7 session
(`ic1 jaseci-pg-cte dbloc=17`, `ic13 jaseci-pg-cte dbloc=4`,
`pymk jaseci-pg-cte dbloc=15`).

**Left for the parent (out of this phase's commit scope):** two annotation
lines in `benchmark/snb/jaseci-pg/app.jac` are now stale, and editing that
file would break the `app.jac == app.jac.T7` pin the T7b bracket control
swaps against, so they were NOT touched:

- line 300 `# burden: bench=snb feature=ic1 arm=jac-lti dbloc=24` and line 627
  `# burden: bench=snb feature=ic13 arm=jac-lti dbloc=20` describe naive-BFS
  arms that no longer exist **in this file** (T7 deleted them). They remain
  correct for `snb/jac-lti/app.jac`, which still has that code with the same
  numbers, so `burden.csv` is not wrong — the headers are just in the wrong
  file now.
- `is2` (line 108) and `ic2` (line 336) keep the `(JAC_CTE_TRAVERSE=1)`
  suffix, which is still **accurate**: both walkers still branch on the flag.

## Commands run

```
cd /home/aaron/Dev/Research/DatabaseResearch/DBHarness
diff -q benchmark/snb/jaseci-pg/app.jac session0901/opt_ladder/T7/app.jac.T7
# patch the copy with the T7 deltas (text taken verbatim from the served app)
python3 <scratchpad>/patch_snb.py
cd benchmark/burden/apps/snb/jac
#   hops -> equal-length placeholders, format, hops back
jac fmt app.jac
# verify against the served app
python3 <scratchpad>/cmp2.py benchmark/snb/jaseci-pg/app.jac  benchmark/burden/apps/snb/jac/app.jac
python3 <scratchpad>/cmp2.py benchmark/tpcc/jaseci-pg/app.jac benchmark/burden/apps/tpcc/jac/app.jac
python3 <scratchpad>/cmp2.py littleXs/jaseci-pg/app.jac       benchmark/burden/apps/littlex/jac/app.jac
session0904/T7b/jac-t7-832374734 check app.jac    # copy 6 errors / served 14
cd benchmark/burden
../.venv/bin/python gen_viewer.py
../.venv/bin/python collect.py
```

## Files changed

- `benchmark/burden/apps/snb/jac/app.jac` (re-derived, 387 → 346 lines)
- `benchmark/burden/viewer_counts.csv` (SNB jac row only)
- `benchmark/burden/burden.csv` (67 → 108 rows)
- `benchmark/burden/burden_viewer.html` (unified, 11 panels)
- `benchmark/burden/snb_burden_viewer.html`

`tpcc_burden_viewer.html` and `littlex_burden_viewer.html` were regenerated
and came out **byte-identical** to the committed versions — independent
confirmation that nothing outside SNB Jac moved.
- `benchmark/burden/FORMAT_FAIRNESS.md` (counts table + guard note)
- `benchmark/burden/CLASSIFY.md` (step 5: which walkers still carry the
  `CTE_TRAVERSE` wrapper after T7)
