# WeBridge: Synthesizing Stored Procedures for Large-Scale Real-World Web Applications

Reading progress: read; user reported completion on 2026-10-21. Bibliography verified against the local PDF.

## Motivation and problem

Paper claim (abstract and §1, pp. 64:1–64:2): dependent SQL queries require application–database round trips that prefetching or batching alone cannot eliminate when dependency computation stays in the application.

## Main ideas and how they work

Initial overview from §1, pp. 64:2–64:3: concolic execution extracts SQL statements and their control/data dependencies along hot execution paths; WeBridge synthesizes stored procedures and integrates them through database-access interception. Unseen paths fall back to original interactive SQL execution. Assistant mechanism notes currently cover this introductory overview.

## Evidence and evaluation

Assistant evaluation notes: pending.

## Limitations and tradeoffs

Comparison questions for Jac: supported computations, path coverage, fallback, side effects and transaction semantics.

## My understanding and connections

User interpretation (2026-10-15): this paper seems closely related to the Jac database-pushdown problem discussed with the jac-db and DBHarness repositories.

AI working hypothesis: both aim to reduce application–database interaction across dependent accesses. WeBridge synthesizes stored procedures using dynamic hot-path analysis; the Jac branch discussed so far uses compiler proofs and SQL-oriented rewrites. Compare dependency analysis, transformation boundaries, and supported computations against the new Jac-to-SQL reading set.

## Open questions

- Which computations and control flow can WeBridge move into stored procedures?
- How are application state, side effects and transactions preserved?
- How does stored-procedure synthesis compare with whole-walker SQL fusion for DBHarness IC5?
- Where could Jac provide additional semantic information, and is it necessary for the optimization?

## AI-assisted reading log

2026-10-15: added at user request, downloaded the author-hosted 29-page PDF, verified bibliography, and inspected the abstract/introduction for initial framing. No full reading or evaluation review completed.

2026-10-21: user reported completing WeBridge and approved adding eight related papers, committing the library changes, and pushing them. WeBridge anchors the `jac-to-sql` reading set.

## Next reading step

Next: [Extracting Equivalent SQL from Imperative Code](../equivalent-sql-2016/notes.md), then [Froid](../froid-2017/notes.md) and [Rewriting Procedures for Batched Bindings](../batched-bindings-2008/notes.md). Compare their compilation and batching mechanisms with WeBridge and Jac pushdown.
