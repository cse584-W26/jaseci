# COBRA: A Framework for Cost-Based Rewriting of Database Applications

Reading progress: reading. Lesson 1 covers the motivating example (§II), equivalent program alternatives, the Region DAG idea, and cost-model intuition. Preparation inspected selected parts of §§III–VI and §VIII Experiments 1–2 / Fig. 12. Bibliography verified.

## Motivation and problem

Paper claim: The abstract (PDF p. 1) describes representing program regions algebraically, generating equivalent alternatives through transformations, and extending Volcano/Cascades to select a low-cost program.

## Main ideas and how they work

COBRA retains equivalent program alternatives in a Region DAG and chooses the alternative with the lowest estimated program cost (§§III–VI). The alternatives come from a supplied set of semantics-preserving transformations. EE's F-IR and existing rewrite rules are used as candidate generators (§V, Fig. 10); the search includes imperative regions as well as relational/F-IR expressions.

### Lesson 1: the same program, three execution strategies

Adapted from §II and Fig. 3. Original program P0 iterates over orders, obtains the related customer through the ORM, computes `myFunc(order.id, customer.birth_year, ...)`, and adds the value to the result. Lazy customer access can issue lookup queries; ORM caching affects actual lookup counts.

- P1: issue an order/customer SQL join, fetch its result, then run the same `myFunc` in the application.
- P2: prefetch customers, cache them by customer key, fetch orders, then look up each customer locally before running the same `myFunc`.

Both P1 and P2 are valid rewrites. Their costs differ because the join repeats customer attributes for each order, while prefetch transfers the customer table once and pays local lookup/memory costs. Few relevant orders favor fetching only matching customers; many orders sharing customers can favor avoiding repeated transfer. The motivating example assumes the prefetched tables fit application memory.

### Search representation

An OR node represents equivalent ways to compute a region's result. Its AND-node alternatives specify the operators/subregions required to compute it (§§III–IV). New rewrites add alternatives while retaining the original. Region operators such as `seq`, `cond`, and `loop` allow the representation to include application work that stays outside SQL.

### Cost model

§VI and Fig. 11 estimate query execution, network transfer, local computation, branch costs, and loop iterations. The query-cost equation, with shortened names, is:

```text
C_query = RTT + t_first + max(result_bytes / bandwidth, t_last - t_first)
result_bytes = estimated_result_rows * estimated_row_width
```

The maximum accounts for overlap between continued database result production and network transfer. Sequential-region costs add; conditional costs use branch probabilities plus predicate evaluation; loop costs depend on iteration count and body/folding-function cost. Prefetch has an amortization factor for expected reuse. Experiments estimate parameters using database information and profiling, supplied via a cost catalog (§VIII).

Further mechanism to inspect: §V extends F-IR with tuple-valued folds and projections to represent dependent aggregations together, allowing costing to account for computations that remain in a loop when only one aggregate is pushed down.

## Evidence and evaluation

Paper-reported measurements (§VIII Experiments 1–2, PDF p. 10; Fig. 12(a)–(b), PDF p. 11): at 1 million orders and 73,000 customers, the join alternative P1 takes 6047 seconds versus 3467 seconds for prefetch P2 in the slow-network experiment. In the fast-network experiment, P1 takes 16 seconds and P2 12 seconds. COBRA selects P1 at lower order cardinalities and switches to P2 as duplication grows.

Setup: simulated slow remote network, 500 kbps and latency parameter 250 ms; fast local network, 6 Gbps and RTT 0.5 ms. MySQL 5.7 server: Intel i7-3770 3.40GHz, 16GB RAM. Hibernate application client: Intel i5-6300 2.4GHz, 8GB RAM, about 4GB available to the application. Windows 10; reported times average five runs. Order/Customer row sizes follow the paper's TPC-DS-based setup.

These measurements compare two equivalent programs under the stated conditions. Further workload experiments, estimation errors, and optimization overhead remain future reading topics.

## Limitations and tradeoffs

The selected alternative depends on generated candidates and cost estimates. Application memory matters for prefetch (§II). Cache reuse is modeled using an amortization factor; the paper identifies more general cache/materialization interactions as future work (§VI). F-IR focuses on read queries; update queries can remain as imperative code in the Region DAG (§V-C).

## My understanding and connections

AI research connection: Study a cost model and search strategy for choosing Jac-to-SQL fusion boundaries, including data-transfer and application-computation costs.

User's specific question: a region may compile correctly to SQL yet be slower after pushdown. This is profitability, distinct from translation eligibility. COBRA directly considers retaining application execution alongside SQL/prefetch alternatives. For Jac, propose candidates first, preserve their semantics, estimate whole-program costs, then validate predicted ranking against measurements.

Related reading: [WeBridge](../webridge-2024/notes.md), completed by the user on 2026-10-21.

## Open questions

- Which cost terms decide whether to fuse queries, prefetch data, or retain computation in Jac?
- How are Region DAG alternatives generated without repeatedly exploring cyclic rewrites?
- How does tuple-valued F-IR represent dependent aggregates and expose the cost of partial pushdown?
- How sensitive is selection to cardinality, row-width, network, and cache-reuse estimation errors?

## AI-assisted reading log

2026-10-21: added to the user-approved Jac-to-SQL reading set; downloaded and parsed the PDF, verified the bibliography, and inspected first-page material for reading preparation.

2026-10-21, Lesson 1: user selected COBRA after clarifying that the question is SQL-compilable code whose pushdown may be unprofitable. Reviewed the order/customer alternatives, search representation, cost model, and Fig. 12. Prepared a seven-page English lesson PDF.

2026-10-21, stopping point: user requested committing and pushing the current lessons and plans to resume COBRA on 2026-10-22. Resume with a brief join-versus-prefetch recap, then work through the Region DAG and cost model.

## Next reading step

Work through the Region DAG construction in §IV, then §V's dependent-aggregation example and the precise cost-model inputs in §VI.
