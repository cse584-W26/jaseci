# Extracting Equivalent SQL from Imperative Code in Database Applications

Reading progress: reading. Lesson 1 covers §§1–2, Figures 2–3, and introductory D-IR/F-IR concepts. Preparation also inspected §§3.2–4.2, the Appendix B initialization rule, and §7 Experiment 7. Bibliography verified.

## Motivation and problem

Paper claim: The abstract and introduction (PDF p. 1) describe deriving an algebraic representation of imperative application code mixed with SQL, then translating that representation into SQL to reduce data movement and round trips.

## Main ideas and how they work

Paper mechanism (§2, pp. 1782–1783): source program → D-IR → F-IR → relational rewrites → SQL. The compiler constructs an expression for a selected variable, replaces its computation with the generated query, and removes redundant code.

- D-IR (§3.2–3.3): an equivalent-expression DAG plus a variable-expression map. It substitutes intermediate assignments, shares common expressions, and retains explicit Loop nodes for cursor loops.
- F-IR (§4.1): extends the representation with a left fold, describing an update function, its initial accumulator, and the input collection. Subsequent transformations move computation into relational operators.
- Safety preview (§4.2, Fig. 6): loop-to-fold conversion checks dependence conditions. Detailed conditions and derivation remain the next lesson.

### Lesson 1 running example

Adapted from Fig. 2, p. 1783; Python-like pseudocode:

```python
boards = query(Board, rnd_id=1)
scoreMax = 0
for t in boards:
    score = max(t.p1, t.p2, t.p3, t.p4)
    if score > scoreMax:
        scoreMax = score
return scoreMax
```

Teaching rows for round 1: `(4, 8, 6, 3)` and `(7, 5, 9, 2)`. Row maxima are 8 and 9; the returned value is 9. A row belonging to round 2 is excluded by the original query.

An accumulator update `if score > scoreMax: scoreMax = score` computes `max(scoreMax, score)`. In simplified F-IR notation:

```text
Q = select round-1 Board rows
g(t) = max(t.p1, t.p2, t.p3, t.p4)
scoreMax = fold((acc,t) -> max(acc,g(t)), 0, Q)
```

The row-local function becomes projection; the cross-row fold becomes aggregation. PostgreSQL SQL sketch adapted from Fig. 3(d), with the original zero initialization explicit:

```sql
SELECT GREATEST(0, COALESCE(
    MAX(GREATEST(p1, p2, p3, p4)), 0
)) AS scoreMax
FROM Board
WHERE rnd_id = 1;
```

Example domain: non-NULL integer scores. `GREATEST` compares the four columns in one row; aggregate `MAX` combines rows. The outer zero floor preserves the source behavior on empty input and all-negative input. Fig. 3(d) prints the simpler aggregate; Appendix B, rule T6 discusses initial accumulator values distinct from the folding identity. Check these initial-value semantics during compiler design.

## Evidence and evaluation

Paper-reported evidence (§7, Experiment 7, Fig. 10, p. 1792 / PDF p. 12): on the Matoso maximum-score example, the optimized query transfers one scalar as table size increases, while the original transfers an increasing amount of row data. General experiment setup (§7, p. 1790 / PDF p. 10): Java/Soot, DBridge, MySQL 5.5, Intel i7-3770 3.40GHz, 8GB RAM, Ubuntu Linux.

Local teaching validation (2026-10-21): Python loop versus an in-memory SQLite 3.37.2 translation, using non-NULL integer columns. All 33 checked inputs matched: three explicit cases and 30 generated cases using random seed 42, with 0–29 rows and integer scores from -30 to 30. Matching results illustrate this adapted example's semantics.

| Explicit case | Source loop | SQL |
| --- | --- | --- |
| Normal round-1 rows, plus an excluded round-2 row | 9 | 9 |
| Empty input | 0 | 0 |
| One all-negative round-1 row | 0 | 0 |

Tested SQLite query (multi-argument `max` is scalar; single-argument `max` is aggregate):

```sql
SELECT max(0, coalesce(max(max(p1,p2,p3,p4)),0))
FROM Board WHERE rnd_id = 1;
```

Broader evaluation and its quantitative performance results: next reading tasks.

## Limitations and tradeoffs

For this example, preserve integer/NULL behavior and the initial accumulator. For general transformations, inspect collection order, duplicates, side effects, aliasing, and loop-carried dependencies (§§3.2, 4.2). The overview focuses on cursor loops and conservatively preserves exception-handling boundaries (§2).

## My understanding and connections

AI research connection: Study D-IR and F-IR as candidate designs for representing several Jac statements before generating a larger SQL expression.

Lesson 1 comparison: WeBridge synthesizes stored procedures for dependent application/database operations; this paper recovers a selected value's computation and rewrites that computation into relational SQL. For Jac, investigate an IR that exposes query lineage, accumulator state, and relevant side effects before choosing fusion rules. Source evidence: this paper §2 and WeBridge §§3–6; the Jac statement is a design question.

Follow-up comparison: WeBridge §10 (pp. 64:23–64:24) distinguishes reducing application/database round trips from optimizing procedural work inside the database. It explicitly describes its speculative execution as orthogonal to stored-procedure optimizations and says generated procedures can benefit from them. Equivalent SQL §5.2 (p. 1789) explains replacing a selected computation with relational SQL and eliminating redundant code. These are complementary mechanisms: procedure synthesis reduces communication boundaries; relational extraction can improve the computation executed across those boundaries.

Comparison correction: both papers push application computation into the database and can reduce network round trips. Equivalent SQL explicitly targets reducing both transferred data and the number of queries (§§1–2, pp. 1781–1783), including nested-loop computations translated to GROUP BY. The maximum-score example begins with one query, so it demonstrates data-transfer reduction rather than an RTT reduction. Compare the approaches by analysis method, transformation target, supported programs, and deployment; their optimization goals overlap.

Clarification on the maximum example: Fig. 2 uses three assignments, `score=max(p1,p2)`, then `score=max(score,p3)`, then `score=max(score,p4)`. D-IR substitutes earlier definitions to recover the nested expression. The lesson's four-argument pseudocode is a teaching abbreviation for those three source assignments.

Related reading: [WeBridge](../webridge-2024/notes.md), completed by the user on 2026-10-21.

## Open questions

- Which Jac constructs and query dependencies can be represented by D-IR/F-IR while preserving order and multiplicity?
- How do region construction and the variable-expression map compose assignments and branches?
- Which loop-carried dependencies permit the Fig. 6 fold transformation?
- How does the nested-loop rewrite generate GROUP BY while preserving empty groups and multiplicities?

## AI-assisted reading log

2026-10-21: added to the user-approved Jac-to-SQL reading set; downloaded and parsed the PDF, verified the bibliography, and inspected first-page material for reading preparation.

2026-10-21, Lesson 1: user selected this paper for teaching. Prepared the maximum-score example, D-IR/F-IR overview, zero-initialization analysis, SQLite validation, and a seven-page English PDF presentation. Next lesson starts with D-IR construction. User completion remains open.

2026-10-21, follow-up: clarified assignment substitution versus the abbreviated four-argument max; compared WeBridge's procedure synthesis with relational extraction using WeBridge §10 and this paper §5.2.

2026-10-21, user correction: emphasized the shared pushdown/RTT-reduction objective. The earlier explanation separated communication reduction and relational optimization too sharply; both papers can reduce round trips.

## Next reading step

Teach §3.2–3.3: build an expression DAG and variable-expression map for a short assignment/branch example. Then explain Fig. 6's dependence preconditions and progress to nested loops and GROUP BY.
