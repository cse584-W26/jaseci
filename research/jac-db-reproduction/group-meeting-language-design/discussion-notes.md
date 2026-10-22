# JacDB: Easier Queries, Efficient Execution

26 main discussion slides and 21 paper profiles.

Main flow: Research Problem → Problem Example → Solution → Solution Example → Data → Discussion.

Evidence labels distinguish existing mechanisms, historical colleague data, reproduced measurements and proposed analysis/evaluation.

## 1. JacDB: Easier Queries, Efficient Execution

Group discussion • language design + compiler/runtime support • October 2026

The project goal is to simplify SQL-database querying for application programmers. The two linked research questions are expressiveness/usability and the execution cost of that programming model.

Source: Research framing: discussion with the project collaborators and user, 2026-10-21.

## 2. Two research questions, one programming model





Source: Proposed research decomposition.

## 3. Make “comfortable to use” concrete





Source: Proposed criteria; Interdisciplinary PL Design, Fig. 1 / Table 1.

## 4. Running example: find relevant active forums

IC5: given a person and date, find friends’ recently joined forums and rank their qualifying posts.

For each forum, count posts authored by friends whose membership in that forum satisfies the date predicate. Sort by descending count then forumId and return the top 20. Friend identity and forum identity must stay correlated.

Source: Historical IC5 COMPILER_PLAN.md: query definition; benchmark/snb/jaseci-pg/app.jac.

## 5. Natural traversal leaves execution decisions open

Algorithm sketch adapted from the existing IC5 walker; illustrative pseudocode.



Source: Historical sources/session0904/ic5/COMPILER_PLAN.md, “The two plans”.

## 6. Actual Jac source: count qualifying authors

Verbatim inner-loop excerpt from the historical IC5 walker; enclosing forum loop supplies fo and foj.

The field count is local; joined maps a forum identity to its qualifying friend identities. ContainerOf and HasCreator are explicit graph operations. A compiler must retain this correlation when replacing the loop with an aggregate.

Source: sources/benchmark/snb/jaseci-pg/app.jac: ic5_new_forums, inner post loop.

## 7. What must remain predictable?





Source: IC5 semantics; proposed JacDB semantic contract.

## 8. Prior work: language design already removes work

Collected backend/query-language references; detailed paper profiles follow in the appendix.



Source: Ur/Web §§2–3; Links §§2,4; LINQ p.706; Practical LINQ §§2,5; Query Shredding §§4–5.

## 9. Prior work: several optimization paths overlap





Source: Paper-lib: QBS, EE, Froid, PL/SQL Away, Batched Bindings, Sloth, WeBridge, Pyxis, COBRA.

## 10. A language contract connects comfort to analysis





Source: Proposed JacDB design; references: Ur/Web, Links, Practical LINQ.

## 11. Build a dependency representation before SQL

Hypothesis: a shared representation can replace isolated recognizers for a defined fragment.



Source: Proposed design; related mechanisms: EE §§3–4; Froid §§3–5; WeBridge §§5–6.

## 12. Across abilities, track how here changes

A traversal result supplies the arrival node for the next supported ability.

Illustrative decomposition: A starts at Person, visits friends; B receives each friend and visits qualifying forums; C processes the correlated forum/friend value. Summary construction must account for dispatch, walker state, queue ordering and repeated arrivals.

Source: Proposed analysis; existing Jac semantics supply traversal/ability structure.

## 13. Eligibility and profitability are separate decisions





Source: EE §4.2; COBRA §§III–VI; Jac design questions.

## 14. Cost-based choices can preserve the same interface

The programmer’s query can have multiple equivalent implementations.



Source: COBRA §II, §§III–VI; proposed Jac application.

## 15. Apply the analysis to the same IC5 query

Recover the correlation and aggregate before choosing execution boundaries.



Source: Historical IC5 COMPILER_PLAN.md / REPORT.md; generalized dependency analysis is proposed.

## 16. Worked example: preserve correlation and zero counts

Teaching data, illustrating the required semantics; IDs are symbolic.



Source: Adapted IC5 example; new illustrative data, independent of measured fixtures.

## 17. Existing mechanisms and the next abstraction





Source: Historical IC5 REPORT.md / COMPILER_PLAN.md; current research proposal.

## 18. Existing evidence: database-related source lines

Each cell is total application LoC / database-related LoC under the historical classification.



Source: DBHarness 36f8b291; benchmark/burden/viewer_counts.csv; FORMAT_FAIRNESS.md.

## 19. Existing evidence: unchanged IC5, fewer SQL statements

20 parameter rows; identical walker; every rung passes result parity.



Source: September 5 gates/ic5_*.json; SQL totals recomputed by this deck builder.

## 20. New measurements: define DB call time precisely

Primary RTT = per-request sum of complete database command/response durations.



Source: webridge/non-snb/METHODS.md; RTT_MEASUREMENT_PLAN.md.

## 21. littleX feed: all compared source forms

20 tweets/user • zero added delay • 30 measured requests/cell • median summed DB RTT.

Jac original is the pinned earlier runtime, which already contains loop-prefetch batching. Jac final uses final32. Full Java ports graph-access behavior; pruned Java removes Jac-specific access work; conventional Java directly uses set-oriented business SQL. Failure rows have compiler-stage evidence and no accepted timing.

Source: webridge/non-snb/results.csv: littlex-feed-t20, delay_ms=0; METHODS.md.

## 22. Network delay makes remaining calls consequential

Same littleX feed workload; medians of summed DB-call time in milliseconds.



Source: webridge/non-snb/results.csv: littlex-feed-t20, added response delays 0 / 2 / 10 ms.

## 23. Interpret the measurements at their actual boundaries





Source: METHODS.md; COMPLETION.json; historical-overview/verification.json.

## 24. Evaluate the programming claim with real tasks

Use the same features, data and correctness oracle across Jac, SQL and an ORM/query interface.

Counterbalance task order and provide comparable training. Separate author expertise and learning cost from language effects. Record failures and debugging steps, and manually inspect what concepts participants had to understand. Start with a reproducible expert case study, then use participants if making human performance claims.

Source: Proposed study; Interdisciplinary PL Design Fig.1/Table1; ScalaLoci §8.

## 25. Evaluate the compiler claim on the same programs





Source: Proposed plan; EE / QBS / WeBridge / COBRA provide relevant baselines.

## 26. Group decisions: define the contribution to test





Source: Proposed research questions, informed by the collected prior work.

## 27. Ur/Web: Typed persistence and atomic backend operations

Ur/Web: A Simple Model for Programming the Web

Paper mechanism: Source table declarations, typed embedded SQL and modules connect persistent rows with language types. Remote calls execute atomically; managed channel sends are released at commit, and serialization failures trigger rollback/retry.

Evidence: §§2.1–2.1.1, 3.1–3.2. §4 reports framework benchmarks, deployed applications and developer feedback. Developers explicitly specify SQL reads and writes.

Connection: Jac question: which query, transaction and effect-management responsibilities should the language absorb? Ur/Web is the closest collected backend language/database co-design reference.

Full title: Ur/Web: A Simple Model for Programming the Web
Venue: POPL 2015
Local source: sources/papers/urweb-2015/notes.md

Source: POPL 2015 | https://doi.org/10.1145/2676726.2677004

## 28. Links: Tables, query values and mutation in one language

Links: Web Programming Without Tiers

Paper mechanism: A typed language spans browser, server and database. Mutable table handles are distinct from lists; a query view supports comprehensions, filters, ordering and take/drop that compile to SQL.

Evidence: §2 Database subsection; §4 query compilation. Worked applications and translation rules explain the design. Table mutation is integrated with the source language.

Connection: Jac question: distinguish a persistent graph handle, a deferred query and a materialized result. Their types and execution boundaries affect both usability and optimization.

Full title: Links: Web Programming Without Tiers
Venue: FMCO 2006, revised selected papers, LNCS 4709 (published 2007)
Local source: sources/papers/links-2007/notes.md

Source: FMCO 2006, revised selected papers, LNCS 4709 (published 2007) | https://link.springer.com/chapter/10.1007/978-3-540-74792-5_12

## 29. LINQ: Composable queries plus object/relational integration

LINQ: Reconciling Objects, Relations and XML in the .NET Framework

Paper mechanism: Standard query operators express traversal and filtering inside the host language. DLinq translates expression trees and object navigation into SQL, maps rows into objects and tracks updates.

Evidence: Complete one-page system overview, p. 706, especially DLinq. It establishes an architecture; follow-up work supplies detailed semantics and evaluation.

Connection: Jac question: what work remains after query composition, mappings and change tracking are already provided? Compare specific programmer tasks against a capable ORM/query provider.

Full title: LINQ: Reconciling Objects, Relations and XML in the .NET Framework
Venue: ACM SIGMOD 2006 (one-page system overview)
Local source: sources/papers/linq-2006/notes.md

Source: ACM SIGMOD 2006 (one-page system overview) | https://gavinbierman.github.io/assets/pdf/sigmod2006.pdf

## 30. Practical LINQ: Composition needs a predictable compilation boundary

A Practical Theory of Language-Integrated Query

Paper mechanism: Quotation retains query bodies; antiquotation composes predicates/functions. Normalization removes supported abstraction before SQL generation. A restricted typed fragment has a single-query guarantee.

Evidence: §2; §5.3 Proposition 4; §9 evaluation. The formal core covers flat final results and excludes recursion, sorting, grouping and aggregation; practical coverage is broader.

Connection: Compiler background: define which Jac helpers retain query structure and which materialize results. Query-count guarantees require an explicit fragment; cost still needs separate evaluation.

Full title: A Practical Theory of Language-Integrated Query
Venue: ACM ICFP 2013, pp. 403–416
Local source: sources/papers/practical-linq-2013/notes.md

Source: ACM ICFP 2013, pp. 403–416 | https://doi.org/10.1145/2500365.2500586

## 31. Query Shredding: Nested results without a query per parent

Query Shredding: Efficient Relational Evaluation of Queries over Nested Multisets

Paper mechanism: Normalize a query returning nested multisets, shred it into flat SQL queries, retain indexing information and stitch the results back into nested values.

Evidence: Abstract, §1 and Fig. 1; mechanism in §§4–5; evaluation in §8. Query count depends on result/query structure rather than the number of parent records.

Connection: Jac question: can nested graph-shaped results retain a convenient interface while compilation handles batching and reconstruction? Preserve duplicates and specify ordering.

Full title: Query Shredding: Efficient Relational Evaluation of Queries over Nested Multisets
Venue: ACM SIGMOD 2014; local PDF is the extended author version
Local source: sources/papers/query-shredding-2014/notes.md

Source: ACM SIGMOD 2014; local PDF is the extended author version | https://doi.org/10.1145/2588555.2612186

## 32. QBS: Recover relational intent from application loops

Optimizing Database-Backed Applications with Query Synthesis

Paper mechanism: Synthesis produces loop invariants and postconditions in a theory of ordered relations; the resulting specifications translate into SQL for supported imperative fragments.

Evidence: Abstract and §1. The program-to-query problem includes joins, aggregates and output order. Existing library coverage introduces the mechanism.

Connection: Jac question: which relational facts follow directly from typed graph operations, and which still require general program reasoning or synthesis? Test equivalent tasks and semantic edge cases.

Full title: Optimizing Database-Backed Applications with Query Synthesis
Venue: ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI), 2013
Local source: sources/papers/qbs-2013/notes.md

Source: ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI), 2013 | https://homes.cs.washington.edu/~akcheung/papers/pldi13.html

## 33. Equivalent SQL: Variable lineage and folds expose relational computation

Extracting Equivalent SQL from Imperative Code in Database Applications

Paper mechanism: D-IR tracks equivalent expressions and variable definitions; F-IR represents cursor loops as folds. Relational rewrites replace a selected computation with SQL and remove redundant code.

Evidence: §§2–4, Fig. 6 and Appendix B. The maximum-score example preserves the initial accumulator on empty/all-negative input. Goals include fewer queries and less transferred data.

Connection: Jac question: use a dependency representation across supported statements/abilities, then derive aggregation. Preserve initial state, multiplicity, ordering, exceptions and effects.

Full title: Extracting Equivalent SQL from Imperative Code in Database Applications
Venue: ACM SIGMOD International Conference on Management of Data, 2016
Local source: sources/papers/equivalent-sql-2016/notes.md

Source: ACM SIGMOD International Conference on Management of Data, 2016 | https://doi.org/10.1145/2882903.2882926

## 34. Froid: Imperative scalar functions become relational regions

Froid: Optimization of Imperative Programs in a Relational Database

Paper mechanism: UDF variables become columns; regions become relational expressions composed with APPLY. Inlining into the caller exposes the combined computation to the database optimizer.

Evidence: §§3–5. The evaluated implementation disables prototype cursor-loop support (§4.2.1). §8.3 Fig. 13 reports about 3,300 versus nearly 5 million logical reads for its total-price example.

Connection: Jac question: can ability inputs/outputs become explicit region interfaces? Compare supported control flow and traversals. Froid and Equivalent SQL share composition and branching capabilities.

Full title: Froid: Optimization of Imperative Programs in a Relational Database
Venue: Proceedings of the VLDB Endowment 11(4), 432–444, December 2017; presented at VLDB 2018
Local source: sources/papers/froid-2017/notes.md

Source: Proceedings of the VLDB Endowment 11(4), 432–444, December 2017; presented at VLDB 2018 | https://doi.org/10.1145/3164135.3164140

## 35. Compiling PL/SQL Away: Loops can target recursive SQL

Compiling PL/SQL Away

Paper mechanism: Compile procedural functions into SQL subqueries; iteration becomes SQL-level recursion so the surrounding SQL query and function can execute together.

Evidence: Abstract and §1 of the 2019 arXiv version. The motivating problem is procedural/SQL context switching inside the database.

Connection: Jac question: represent loop-carried state and termination explicitly when compiling cyclic traversal. Compare recursive SQL with retained application execution on the actual workload.

Full title: Compiling PL/SQL Away
Venue: arXiv preprint arXiv:1909.03291v1, 2019
Local source: sources/papers/compiling-plsql-away-2019/notes.md

Source: arXiv preprint arXiv:1909.03291v1, 2019 | https://arxiv.org/abs/1909.03291

## 36. Batched Bindings: Repeated calls become a batch of parameter bindings

Rewriting Procedures for Batched Bindings

Paper mechanism: Rewrite repeated query/procedure invocations into a batched call and rewrite the callee to accept a set of input parameters instead of one parameter at a time.

Evidence: Abstract and first-page example. The target includes repeated query and stored-procedure/UDF calls; dependence and side-effect conditions determine legal rewrites.

Connection: Jac question: batch a frontier of traversal inputs across ability invocations and correlate every result with its input. Repeated arrivals and duplicates require defined behavior.

Full title: Rewriting Procedures for Batched Bindings
Venue: Proceedings of the VLDB Endowment 1(1), 2008
Local source: sources/papers/batched-bindings-2008/notes.md

Source: Proceedings of the VLDB Endowment 1(1), 2008 | https://www.vldb.org/pvldb/vol1/1453975.pdf

## 37. Sloth: Delay execution to discover larger batches

Sloth: Being Lazy is a Virtue (When Issuing Database Queries)

Paper mechanism: Extended lazy evaluation exposes batching opportunities during execution, including across loops, branches and method boundaries, until a value is demanded.

Evidence: Abstract and introduction. The paper evaluates more than 100 benchmarks from two applications and reports up to 3× page-load reduction under its conditions.

Connection: Jac question: compare static fusion with runtime deferral. Identify the exact demand that forces a query and whether a dependency can instead execute in the database.

Full title: Sloth: Being Lazy is a Virtue (When Issuing Database Queries)
Venue: ACM SIGMOD International Conference on Management of Data, 2014
Local source: sources/papers/sloth-2014/notes.md

Source: ACM SIGMOD International Conference on Management of Data, 2014 | https://doi.org/10.1145/2588555.2593672

## 38. WeBridge: Dependent access paths become stored procedures

WeBridge: Synthesizing Stored Procedures for Large-Scale Real-World Web Applications

Paper mechanism: Record and replay hot paths using concolic execution, recover SQL control/data dependencies, synthesize procedures and intercept application database calls. Unseen paths use interactive execution.

Evidence: §§1, 3–6. §10 explains complementary optimizations within generated database work. Procedure synthesis and relational rewriting can both reduce communication.

Connection: Jac question: can language semantics make cross-ability regions easier to identify and support? Compare matched workloads, generated work, fallback coverage and command counts.

Full title: WeBridge: Synthesizing Stored Procedures for Large-Scale Real-World Web Applications
Venue: Proceedings of the ACM on Management of Data 2(1), Article 64 (SIGMOD), February 2024
Local source: sources/papers/webridge-2024/notes.md

Source: Proceedings of the ACM on Management of Data 2(1), Article 64 (SIGMOD), February 2024 | https://doi.org/10.1145/3639319

## 39. Pyxis: Choose where application code executes

Automatic Partitioning of Database Applications

Paper mechanism: Profile the application/server loads and analyze dependencies to partition code between application and database servers, reducing control transfers and transferred data.

Evidence: Abstract and §1; evaluation uses TPC-C and TPC-W. The application/database placement decision incorporates resource load.

Connection: Jac question: after proving a region movable, choose its placement. Deployment support and database load are part of the execution decision.

Full title: Automatic Partitioning of Database Applications
Venue: Proceedings of the VLDB Endowment 5(11), 1471–1482, 2012
Local source: sources/papers/pyxis-2012/notes.md

Source: Proceedings of the VLDB Endowment 5(11), 1471–1482, 2012 | https://www.vldb.org/pvldb/vol5/p1471_alvincheung_vldb2012.pdf

## 40. COBRA: Choose among equivalent whole-program strategies

COBRA: A Framework for Cost-Based Rewriting of Database Applications

Paper mechanism: A Region DAG retains equivalent imperative/relational alternatives. A cost-based search compares SQL joins, prefetch/local lookup and retained application computation.

Evidence: §§II–VI. Fig. 12: at one million orders/73,000 customers, join vs prefetch is 6,047 vs 3,467 seconds on the slow network; 16 vs 12 seconds on the fast network.

Connection: Jac question: separate eligibility from profitability. Model round trips, row duplication/transfer, database execution, application work and available memory.

Full title: COBRA: A Framework for Cost-Based Rewriting of Database Applications
Venue: IEEE International Conference on Data Engineering (ICDE), 2018
Local source: sources/papers/cobra-2018/notes.md

Source: IEEE International Conference on Data Engineering (ICDE), 2018 | https://www.microsoft.com/en-us/research/publication/cobra-a-framework-for-cost-based-rewriting-of-database-applications/

## 41. Eliom: Reusable behavior across explicit execution locations

Eliom: A Core ML Language for Tierless Web Programming

Paper mechanism: OCaml annotations interleave client/server/shared code. Typed client fragments and cross-tier communication support components with behavior on both sides.

Evidence: §2 examples; §§3–5 type system, execution and compilation. Placement and communication are explicit language choices.

Connection: Broader design lesson: modular source boundaries can span execution boundaries. For JacDB, test whether reusable query helpers/abilities remain analyzable when composed.

Full title: Eliom: A Core ML Language for Tierless Web Programming
Venue: APLAS 2016, LNCS 10017
Local source: sources/papers/eliom-2016/notes.md

Source: APLAS 2016, LNCS 10017 | https://doi.org/10.1007/978-3-319-47958-3_20

## 42. Hop: Package related logic while exposing execution levels

Hop, a Language for Programming the Web 2.0

Paper mechanism: A two-level language packages application logic and GUI behavior together; function calls and event loops connect execution levels.

Evidence: Abstract; §§2–4 constructs and execution; §6 implementation. Database access is supplied through libraries.

Connection: Broader design lesson: make execution boundaries understandable to programmers. A Jac query API should explain when construction becomes database interaction.

Full title: Hop, a Language for Programming the Web 2.0
Venue: Dynamic Languages Symposium (DLS), co-located with OOPSLA 2006; OOPSLA Companion
Local source: sources/papers/hop-2006/notes.md

Source: Dynamic Languages Symposium (DLS), co-located with OOPSLA 2006; OOPSLA Companion | https://doi.org/10.1145/1176617.1176756

## 43. ScalaLoci: Placement types and generated communication

Distributed System Development with ScalaLoci

Paper mechanism: Values are associated with peers using placement types. Architecture definitions and distributed reactive flows drive communication and data conversion.

Evidence: §2 mechanisms; §8 case studies and runtime measurements. Table 1 counts LOC, callbacks, imperative state updates and remote accesses.

Connection: Evaluation lesson: measure specific responsibilities removed from source alongside runtime costs. Query execution and programmer effort need distinct evidence.

Full title: Distributed System Development with ScalaLoci
Venue: PACMPL 2, OOPSLA, Article 129 (2018)
Local source: sources/papers/scalaloci-2018/notes.md

Source: PACMPL 2, OOPSLA, Article 129 (2018) | https://doi.org/10.1145/3276499

## 44. Multitier Modules: Separate modularity from deployment topology

Multitier Modules

Paper mechanism: Modules encapsulate cross-peer functionality over abstract peer types, allowing composition and distribution to vary independently.

Evidence: Abstract and §1; §5 case studies include algorithms, distributed data structures and Flink task distribution.

Connection: Broader design lesson: changing query placement should preserve a useful module interface. Study which Jac ability summaries allow analysis across reusable modules.

Full title: Multitier Modules
Venue: ECOOP 2019, LIPIcs 134, Article 3
Local source: sources/papers/multitier-modules-2019/notes.md

Source: ECOOP 2019, LIPIcs 134, Article 3 | https://doi.org/10.4230/LIPIcs.ECOOP.2019.3

## 45. Orleans: Runtime responsibilities support a simpler object model

Orleans: Distributed Virtual Actors for Programmability and Scalability

Paper mechanism: Virtual actors let the runtime handle activation, location and distributed resource management while application code uses logical actor identities.

Evidence: §§2–3 programming/runtime model; §§4–5 applications and performance. This is the 2014 MSR technical report.

Connection: Broader design lesson: identify each responsibility moved into the runtime and its consistency contract. Apply that accounting to Jac object loading, identity and query execution.

Full title: Orleans: Distributed Virtual Actors for Programmability and Scalability
Venue: Microsoft Research technical report MSR-TR-2014-41 (March 2014)
Local source: sources/papers/orleans-2014/notes.md

Source: Microsoft Research technical report MSR-TR-2014-41 (March 2014) | https://www.microsoft.com/en-us/research/publication/orleans-distributed-virtual-actors-for-programmability-and-scalability/

## 46. Kappa: Compiler/runtime support absorbs infrastructure work

Kappa: A Programming Framework for Serverless Computing

Paper mechanism: Checkpointing handles serverless timeouts, while concurrency mechanisms support parallel computation and coordination from a programming framework.

Evidence: Abstract; §3 mechanisms; §5 evaluation; §6 programmer requirements. The abstraction comes with checkpoint/runtime constraints.

Connection: Broader design lesson: simplicity has a runtime cost and an effect boundary. Evaluate programmer obligations and execution overhead together.

Full title: Kappa: A Programming Framework for Serverless Computing
Venue: ACM Symposium on Cloud Computing (SoCC) 2020
Local source: sources/papers/kappa-2020/notes.md

Source: ACM Symposium on Cloud Computing (SoCC) 2020 | https://doi.org/10.1145/3419111.3421277

## 47. PL design methods: Evaluate the programmer-facing claim directly

Interdisciplinary Programming Language Design

Paper mechanism: Combine formal/performance methods with interviews, user experiments, case studies and iterative prototyping throughout language design.

Evidence: Fig. 1, Table 1 and §4. The paper describes complementary design/evaluation methods, including human-centered approaches.

Connection: Jac evaluation: use representative query/modification tasks, comparable training and correctness tests. Measure completion, time, errors and required concepts alongside source metrics.

Full title: Interdisciplinary Programming Language Design
Venue: Onward! 2018
Local source: sources/papers/interdisciplinary-pl-design-2018/notes.md

Source: Onward! 2018 | https://doi.org/10.1145/3276954.3276965
