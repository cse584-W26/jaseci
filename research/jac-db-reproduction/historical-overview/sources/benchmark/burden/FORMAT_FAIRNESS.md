# Formatting fairness + Jac style pass (2026-09-03)

Why the burden counts moved on 2026-09-03 and what the rule is now.

## Problem found

The line viewer's Jac panels had been machine-formatted (`format_jac`, later
`jac fmt`: one keyword argument per line once a call exceeds 88 columns), but
the Python baseline panels had never been formatted - black was not installed
in the 0814 environment, so the hand-packed source (several kwargs per line,
dict literals on 2-4 lines) was counted as-is. Same statement, two wrapping
policies. Effect: baseline LoC under-counted by 40-90 lines per arm on SNB and
TPC-C (littleX baselines were already close to black style, -2..-10 lines).

## Rule now

Both sides go through their canonical formatter at the same width before
counting:

| side   | tool                        | width |
|--------|-----------------------------|-------|
| Python | `uvx black -l 88` (25.x)    | 88    |
| Jac    | `jac fmt`                   | 88    |

Both wrap a too-long call to one argument per line and add a trailing comma,
so a constructor with N fields costs N+2 lines on either side. SQL/Cypher
string literals are untouched by black; their layout stays the authors'.
Blank lines are stripped by `gen_viewer.py` after formatting, as before.

Also removed this day, unrelated to formatting: four TPC-C Jac walkers
(`get_district/get_customer/get_stock/get_item`) that exist only for the
bulk-load oracle (`scripts/pg_bulk_load.py`, Gate 3-A) and have no baseline
counterpart. They stay in the served source; the viewer copy ends after
`payment`.

## Jac style pass

Mechanical rewrites, applied IDENTICALLY to the served sources
(`benchmark/tpcc/jaseci-pg/app.jac`, `benchmark/snb/jaseci-pg/app.jac`) and
the viewer copies, so the copies never show code that is not benchmarked:

- `x = x + y;` -> `x += y;` (TPC-C 10 sites, SNB 2 sites; ints/floats only)
- `num = 0; for l in lines { num = num + 1; ... }` -> `for (num, l) in enumerate(lines, 1)`
- 6-line `all_local` loop -> `int(all(l["supply_w_id"] == wh.w_id for l in self.lines))`
- 4-line `if new_q < 10 { new_q = new_q + 91; }` -> ternary

Not rewritten:
- littleX `here.likes = here.likes + [self.actor];` - list `+=` mutates in
  place and may not mark the node dirty; the rebind is load-bearing.
- Not-found guards. Baselines guard too (`if x is None: raise HTTPException`,
  2 lines). Jac's 4-line `if not isinstance(x, T) { report {...}; return; }`
  was real burden the language imposed (untyped `jobj` forced a manual
  narrow), not a viewer asymmetry. LANDED 2026-09-04 as T7's typed lookup
  `jobj(id, T)`: the SNB app's 9 narrows are gone (the guard is now the
  builtin's own contract). TPC-C/littleX still guard by hand (`if not
  wh_list`, `isinstance(target, Profile)`) - those are emptiness/branch
  tests, not type narrows, and stay.

Verification: `jac check` on the served files - TPC-C 7 -> 4 errors, SNB
16 -> 16; every remaining error is pre-existing `list[dict]` typing noise the
apps already serve with. No statement shapes change (Python-level operators
only), so timings were not re-run; re-run TPC-C/SNB parity before citing a
post-0903 timing next to these sources.

## Counts after (LoC / dbloc / non-ws chars / non-ws chars on dbloc lines)

| bench   | Jac               | PostgreSQL        | SQLAlchemy        | Neo4j            |
|---------|-------------------|-------------------|-------------------|------------------|
| littleX | 174 / 27 / 3049 / 726  | 250 / 101 / 6127 / 2888 | 281 / 68 / 7130 / 2302 | 229 / 75 / 6429 / 2544 |
| TPC-C   | 225 / 14 / 4146 / 401  | 302 / 197 / 7435 / 5695 | 232 / 117 / 6286 / 3701 | -                |
| SNB     | 320 / 45 / 5761 / 1541 | 315 / 178 / 6868 / 4718 | 330 / 91 / 6947 / 2472  | 202 / 71 / 4374 / 2154 |

Before this fix (same day, oracle walkers already stripped): TPC-C PG 260,
SQLA 191; SNB PG 255, SQLA 237, Neo4j 131.

**SNB Jac re-derived 2026-09-04 (T7)**: was 361 / 46 / 6491 / 1482 on the
pre-T7 served app; the copy is now re-derived from the T7 `app.jac`
(variable-length hop `[start <-:Knows:*3:-> [?:Person, f == v]]` in
ic1/ic13, typed lookup `jobj(id, Person)` replacing the 4-line
`if not isinstance {report; return}` narrow in all 9 walkers). -41 LoC,
-1 dbloc (ic1's `f = jobj(h[0])` hydration line is gone; the two `jclosure`
calls became hop lines 1:1), -730 chars, +59 dbchars (fewer but denser
data-access lines). No other arm and no other bench moved.

**0904 flag retirement — no count moved.** The served SNB app lost `import os`,
`glob CTE_TRAVERSE` and the naive is2/ic2 arms; the served littleX app lost
`walker load_feed_leaf`. Every number in the table above is unchanged, because
the burden copies had already dropped exactly that text: CLASSIFY.md step 5
collapses the `if CTE_TRAVERSE {} else {}` wrapper to its taken branch, and the
littleX section drops `load_feed_leaf`. Re-derived and re-verified per
declaration against the new served text (`session0904/flags/BURDEN2.md`); all
four viewer HTMLs regenerated byte-identical.

**Why the `jtopk(...)` lines stay in the count.** is2 and ic2 hand the top-K
builtin the edge type, both message archetypes with their tie-break field
names, the sort field, a bound and the limit — the ORDER BY / LIMIT the walker
already spells out as a `sort` + slice, restated for the engine because the
compiler cannot yet prove mirror-top-K sufficiency (that the runtime-grown
`(endpoint, creationDate DESC)` mirror index alone answers the query). Until it
infers that, those lines are developer text the developer had to write, so they
are **COUNTED** in Jac's LoC and dbloc — as is the `jroot_many`/`author_of`
batching around them. What was removed on 0904 is a different thing: the
`JAC_CTE_TRAVERSE` env switch and its naive arm existed only to select a
*benchmark arm* at boot, so they were never developer text for the shipped
application and were never counted (the copies dropped them from the start).
Retiring the switch therefore changes what is served, not what is measured.

Source of truth for the numbers: `viewer_counts.csv`, regenerated by
`python gen_viewer.py`. The `auth lines removed` column was dropped the same
day (baseline auth is stripped per the advisor ruling; the tally was noise).
