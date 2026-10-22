# Froid: Optimization of Imperative Programs in a Relational Database

Reading progress: reading. Lesson 1: problem, motivating function, state-as-columns representation, APPLY, and inlining. Preparation inspected §§2–5, §8.3 resource evidence, and the comparison in §9. Bibliography verified.

## Motivation and problem

Paper claim: The abstract (PDF p. 1) describes transforming imperative UDFs into relational algebra expressions embedded in the calling SQL query, enabling cost-based optimization of the combined expression.

## Main ideas and how they work

Paper mechanism (§§3–5, pp. 435–438): divide a scalar T-SQL UDF into regions, convert each region to a relational expression, combine expressions using APPLY, and substitute the resulting expression at the calling query's UDF operator before normal query optimization.

- Variables become projected columns (§4.2.1, Table 1, p. 436): `SET @x = expr` becomes a relation equivalent to `SELECT expr AS x`.
- Region write-sets determine the output columns of derived tables (§4.2.2, p. 437). These derived tables represent intermediate program state.
- A simple IF/ELSE assigning constant labels becomes CASE (§4.2.1). More complex predicates and returns need the paper's additional machinery to preserve evaluation behavior.
- APPLY connects an earlier relation with a parameterized later relation that can reference its columns (§3.2, §4.3). Froid uses outer APPLY between sequential regions; Fig. 4 shows the currency example.
- After substitution into the caller, existing optimizer rules can decorrelate subqueries, simplify expressions, select joins, and enable parallel plans (§§3.2–3.3, 5).

### Lesson 1 teaching example

Adapted pseudocode combines the SUM lookup from Fig. 1 with the high/low branch in §4.2.1. Amounts are non-NULL integers; `Customers.id` is unique. Empty-order totals are explicitly zero.

```text
spending_label(customer):
    total = SELECT COALESCE(SUM(amount),0)
            FROM Orders WHERE customer_id = customer
    if total > 1000: label = 'high'
    else: label = 'low'
    return label
```

Calling-query sketch: `SELECT id, spending_label(id) FROM Customers`.
The historical execution problem described in §2 is inside the database: the query invokes a scalar function per customer, and that function can execute further SQL. The outer call can already be a single client request.

Algebrization represents the total as a column, the label as a CASE expression over that column, and the return as a `returnVal` column. APPLY composes the dependent regions. The combined expression is substituted into the caller; a subsequent optimizer can consider a decorrelated query shape such as:

```sql
SELECT c.id,
       CASE WHEN COALESCE(t.total,0) > 1000
            THEN 'high' ELSE 'low' END AS label
FROM Customers c
LEFT JOIN (SELECT customer_id, SUM(amount) AS total
           FROM Orders GROUP BY customer_id) t
  ON t.customer_id = c.id;
```

This teaching SQL illustrates a possible relational rewrite, rather than specifying a mandatory emitted Froid plan. The compiler's direct transformation acts on the relational query tree (§4.3, p. 437). LEFT JOIN and COALESCE preserve customers with no orders under the example's stated semantics.

## Evidence and evaluation

Paper-reported resource example (§8.3, Fig. 13, p. 443 / PDF p. 12): the total-price query uses about 3300 logical reads with Froid versus close to 5 million without, on a 1GB TPC-H dataset with cold cache. This is the paper's simpler total-price function in Fig. 13; its output formatting differs from the teaching classification function.

Local validation (2026-10-21): an in-memory SQLite 3.37.2 database compared four per-customer SUM/branch calculations against the joined SQL above. All output rows matched. This validates the teaching rewrite on these inputs.

| Customer case | Per-customer calculation | Joined SQL |
| --- | --- | --- |
| Total 300 | low | low |
| Total 1500 | high | high |
| No orders | low | low |
| Total exactly 1000 | low | low |

Broader runtime, compilation, and workload-coverage evaluation: future reading.

## Limitations and tradeoffs

The evaluated implementation disables cursor-loop support after prototyping it (§4.2.1, p. 437). This affects applying Froid directly to Jac traversal and loop-heavy code. Scalar UDF support and its precise language constructs are listed in §3.4. For branch and return lowering, preserve predicate evaluation and early-return behavior (§4.2.1).

## My understanding and connections

AI research connection: Study how to lower supported Jac control flow and variable state into relational expressions that compose with surrounding queries.

Lesson 1 design question: can Jac region outputs become relation schemas, with APPLY expressing dependencies between regions? Additional representations are needed to cover the project's traversal/loop semantics. Compare mechanisms and supported program classes with Equivalent SQL and WeBridge; both earlier discussions retain their shared pushdown/RTT-reduction goals.

### Comparison with Extracting Equivalent SQL (EE)

Both approaches can express the simple SUM/branch teaching example. Froid's specific comparison (§9, p. 443) says Emani et al.'s approach has similar goals and can be adapted to UDFs; the authors report that their prototype adaptation generated larger, more complex SQL than Froid. This is a qualitative prototype observation. The large performance gains in §8 compare Froid ON with Froid OFF.

EE constructs D-IR/F-IR and applies specialized rules to extract relational SQL. Froid directly algebrizes UDF regions, composes them with APPLY, and substitutes the combined expression into the caller before ordinary query optimization (§§3–5). Both ultimately use relational optimization. Query-tree compactness matters because larger trees increase optimizer search complexity (§7.2).

Scope relevant to Jac: EE explicitly handles cursor loops and nested-loop aggregations; the evaluated Froid implementation disables cursor-loop support (§4.2.1). Investigate combining EE's loop reasoning with Froid's region/state representation. Compare semantic coverage, generated query complexity, planning time, and execution cost on the same Jac examples.

Correction after the user's challenge: EE already handles assignments, conditionals, sequential/conditional region composition, and function/procedure composition (§3.3 and Appendix D); Appendix B, rule T7 also uses outer APPLY to combine nested scalar queries. These capabilities cannot be presented as unique Froid advantages. Froid's state-as-columns and region/APPLY design is a representation choice with different integration. Its specific §9 comparison with EE concerns generated SQL size/complexity in a prototype adaptation. The later §9 remarks about multiple returns and predicate evaluation compare with Simhadri et al., rather than establishing missing EE support.

### Fallback and suitability

When source code compiles normally but lacks an eligible relational translation, the optimization can retain original execution. EE works on selected variables/regions: if transformation or SQL generation fails for a variable, its original computation remains intact; other computations may still be optimized (EE §4.2, Fig. 6, and §5.2). Partial replacement must satisfy dependence and effect checks.

Froid substitutes a relational expression for an eligible scalar UDF invocation (§§3.3–3.4). An ineligible invocation retains ordinary UDF execution in SQL Server. This boundary is a function invocation inside the database, rather than arbitrary application code migrating into the database. Tree-size and inlining-depth constraints also bound transformation (§7.2).

Expressibility and profitability are separate. For a translatable but expensive pushdown, EE's implementation assumes its rewrites are beneficial; §5.3 gives a counterexample involving an aggregate plus formatting that still needs all original rows, and proposes cost-based selection as future work. Froid chooses substitution during binding rather than cost-based inlining, while bounding query-tree growth (§§7.1–7.2). Thus SQL compilability alone does not provide a general profitability decision in either paper implementation.

Related reading: [WeBridge](../webridge-2024/notes.md), completed by the user on 2026-10-21.

## Open questions

- How are branches, assignments, and dependencies encoded, and which Jac operations would require additional lowering rules?
- What does outer APPLY preserve when a later region produces no row?
- How do implicit predicate and return variables preserve evaluation order?
- Which decorrelation rule turns repeated per-customer work into a grouped join?

## AI-assisted reading log

2026-10-21: added to the user-approved Jac-to-SQL reading set; downloaded and parsed the PDF, verified the bibliography, and inspected first-page material for reading preparation.

2026-10-21, Lesson 1: user requested moving to the next paper after Equivalent SQL. Selected Froid according to the established order, prepared the state-as-columns/APPLY explanation, checked a four-customer SQLite example, and created a seven-page English PDF lesson deck.

2026-10-21, follow-up: user asked why Froid improves on EE. Inspected Froid §§7.2 and 9; recorded the authors' qualitative SQL-complexity comparison, the ON/OFF evaluation baseline, and the loop-support difference relevant to Jac.

2026-10-21, comparison correction: user correctly identified that EE already translates substantial imperative semantics. Rechecked EE §3.3, Appendix D, and Appendix B T7. Revised the comparison to distinguish shared capabilities, representation differences, and the narrower direct evidence about generated SQL complexity.

2026-10-21, fallback discussion: user asked about normally compilable code unsuitable for SQL pushdown. Distinguished host-language compilability, eligible relational translation, and cost; recorded variable/region fallback in EE versus UDF-invocation fallback in Froid.

## Next reading step

Walk through Fig. 4's exact APPLY expression. Then examine branch/return semantics, optimizer simplification, and the paper's comparison with Emani et al. in §9.
