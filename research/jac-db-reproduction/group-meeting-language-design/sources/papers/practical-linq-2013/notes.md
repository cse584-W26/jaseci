# A Practical Theory of Language-Integrated Query

Reading progress: reading. Lesson 1 covers query composition and normalisation;
formal proofs, open quotation, nested intermediates, and detailed experiments remain open.

## Motivation and problem

User's scope: reduce backend + SQL programming work through Jac language design.

## Main ideas and how they work

Paper mechanism: Quotation represents a query as code data; antiquotation composes fragments, including parameterized functions and predicates. At run, the expression is normalised before SQL generation (§2). The T-LINQ core formalizes this process (§5); Proposition 4 in §5.3 gives the normal-form result underlying the single-query guarantee.

## Evidence and evaluation

Coverage: abstract/introduction, §2 examples and restrictions, and §5.3 proposition. §9 evaluates the implementation, including query-translation failures and avalanches in the historical F# baselines. Detailed benchmark review is next.

## Limitations and tradeoffs

§2.2 requires one database, flat result rows, and SQL-translatable operations in the modeled fragment. T-LINQ excludes sorting, grouping, and aggregation; P-LINQ has broader implementation coverage (§1). Check these boundaries when designing Jac aggregation support. Historical F# results describe the evaluated versions.

## My understanding and connections

AI research framing: Direct reference for letting Jac developers factor database logic into reusable functions while the compiler combines and normalises the query expression.

User interpretation: backend + SQL is the priority; paper-specific interpretations are open.

## Open questions

- How should Jac represent reusable query fragments, prevent premature execution, and extend the formal fragment to aggregation and effects?
- Which tasks are removed from application code, and which become explicit annotations?

## AI-assisted reading log

- 2026-10-21: Added local PDF, verified metadata, initial screening notes, and English slide scaffold.
  Version: Publisher-format PDF from Edinburgh Research Explorer, with a repository cover page. Authors/title on PDF p. 2; year, ICFP venue and DOI on the cover and article first page.

- 2026-10-21: Guided Lesson 1 prepared with the paper composition example, selected
  §9 evidence, and an eight-page English PDF deck. Local SQLite check confirmed
  the adapted example result. User reading status is reading.

## Lesson 1: query functions as composable code

### Running example

The paper defines `getAge`, `range`, and `compose` as quoted functions (§§2.3–2.5,
local PDF p. 5). It evaluates `compose("Edna", "Bert")`: Edna is 21 and Bert is
55 (Fig. 2), and the predicate is **21 <= age < 55**. Result names are Cora,
Drew, and Edna. The upper bound is exclusive, following `range`'s actual code.
Teaching pseudocode in the slides uses `query` to mean a retained query body;
it is an adaptation of the paper's quoted notation.

### Mechanism and execution boundary

`<@ M @>` represents code as `Expr<A>`; `(% fragment)` splices another expression
into it. `run` normalises the composed expression, translates it to SQL, executes
it on the database, and imports the result (§2.2; Fig. 10). Helper construction
and composition preserve code until this boundary.

Normalisation substitutes function arguments (beta-reduction), flattens nested
comprehensions, and moves/combines filters (§5.3, Figs. 11–12). §5.4 works through
the exact composition until three People aliases and a combined filter remain
(local PDF pp. 9–10). One SQL query can express that normal form. The database
optimizer subsequently chooses its physical execution plan.

### Guarantee and scope

Proposition 4 (§5.3, local PDF p. 9) establishes existence of a SQL-shaped normal
form for the well-typed quoted table-result fragment. §2.2 specifies one database,
flat final rows, and supported operations; T-LINQ's formal query fragment excludes
recursion, sorting, grouping, and aggregation. Host code can recursively construct
finite quoted queries (§2.6). Nested intermediate structures are supported; nested
final collections require further treatment (§3).

P-LINQ normalises recognized constructs and carries others through to the LINQ
backend (§9). Its broader practical coverage is distinct from the formal core's
translation guarantee. SQL query count and estimated execution cost are separate
compiler-design questions.

### Evidence inspected

Evaluation is in **§9**, correcting the earlier screening pointer to §7.
Fig. 14 / §9 (local PDF p. 13): query (9) has a flat result and nested intermediate
structure. The evaluated F# 3.0 executes d+1 SQL queries for d departments;
reported average time per department is 12.8 ms for F# 3.0 and 0.3 ms for P-LINQ.
Departments range from 4 to 64, with 100 employees each and 0–2 random tasks.

Table 2 / §9 (local PDF pp. 13–14): all 62 concrete F# documentation database
queries translate with the P-LINQ/F# 3.0 backend. On roughly 30-record databases,
the geometric-mean P-LINQ/F# 3.0 time ratio is 1.13. Each reported time is the
median of 21 trials. Setup: .NET 4.0 and SQL Server 2012 on the same Dell machine,
i5-2400 at 3.10 GHz, 4 GB RAM. These experiments evaluate translation and execution;
a developer task study would address the Jac development-effort question.

### Local example check

SQLite evaluated the adapted three-alias SQL on Fig. 2's six People records,
using a name primary key and non-NULL ages. Compared by result contents with the
21 <= age < 55 predicate, it returned Cora, Drew, and Edna. Row order is unspecified.
This checks the SQL adaptation used for teaching.

### Connection to Jac

AI hypothesis: preserve typed query-function bodies through composition so Jac
can combine reusable business-query fragments before SQL lowering. Define which
calls construct expressions and which materialize results. Specify aggregation,
effects, duplicates, ordering, and NULL behavior for the Jac fragment, then compare
execution costs for legal translations.

### Follow-up: relationship to ORM

User observation: the teaching example resembles ORM query composition.
The overlap is direct: LINQ's relational provider includes object/table mapping,
SQL generation, identity caching, and change tracking (LINQ 2006 overview,
p. 706, DLinq section). Query composition and SQL generation should be presented
as shared capabilities of this programming model.

User correction: ORM queries can also be encapsulated in functions and composed.
Function reuse, deferred execution, and combining query expressions into SQL are
shared capabilities. The eager three-request teaching sketch illustrates one
execution choice; an ORM query-builder implementation can retain the expression
and generate combined SQL too. Assess this paper through its formal fragment,
normalisation rules, and specific historical LINQ cases rather than using function
composition as a general distinction from ORM.

P-LINQ is a query-normalisation preprocessor for the existing F# LINQ backend
(§9). This paper contributes its formal core and normalisation/translation result
(§5.3, Proposition 4), plus concrete composition examples and historical
implementation evidence (§§2–4, 9). Use the supported fragment and those results
when assessing its contribution relative to an ORM query layer.

### Follow-up example: nested view and an ALL predicate

Paper §3.1 defines a virtual nested organisation (departments -> employees ->
tasks) as a quoted expression. §3.2 query (9) uses reusable all/contains helpers
to select departments where every employee can perform a given task, returning
flat department records. The nested intermediate view remains query code.

Teaching adaptation: rename tasks to skills and ask for departments where every
employee knows Python. A has Alice/Python and Bob/SQL; B has Carol/Python.
Only B qualifies. Normalisation expresses the condition as no employee lacking
that skill, using two correlated NOT EXISTS tests over Departments, Employees,
and Skills. SQLite returned B for this adaptation. Departments without employees
satisfy ALL vacuously, as in the paper's Quality department.

The paper-specific implementation evidence is §9 / Fig. 14: for query (9), the
historical F# 3.0 backend issues d+1 SQL queries for d departments, while the
P-LINQ translation normalises the flat-result query to one SQL query. For 64
departments, d+1 is 65. The teaching Python/skills names illustrate the same
predicate shape; the measured paper query uses the task parameter abstract.
ORM query builders can also express and optimize this query. The supported
nested-composition translation and historical failure case explain the specific
contribution under discussion.

### Research selection update

User assessment (2026-10-21): Practical LINQ is outside the core related work for
language + SQL database co-design. Keep the paper and lesson as query-compiler
background. This assessment supersedes the earlier first-paper recommendation.

## Optional continuation as compiler background

Walk through `compose` in §5.4 using the individual `for-for`, `for-if`, `for-yld`,
`if-for`, and `if-if` rules. Then read §6 on abstracting in the quoted language
versus the host language; §3 covers nested intermediates. The [ten-page lesson
deck](slides.pdf) and [backend + SQL guide](../../README.md#jac-backend--sql-reading-focus)
are available.
