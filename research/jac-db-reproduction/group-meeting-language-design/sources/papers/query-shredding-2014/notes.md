# Query Shredding: Efficient Relational Evaluation of Queries over Nested Multisets

Reading progress: queued. AI screening on 2026-10-21; coverage recorded below.

## Motivation and problem

User's scope: reduce backend + SQL programming work through Jac language design.

## Main ideas and how they work

Paper mechanism: A query with nested multiset results is normalised and shredded into flat SQL queries. The resulting packages retain indexing information so results can be stitched back into nested values (§1, Fig. 1; §§4–5). The query count is fixed by the query structure rather than the number of parent records (abstract; §1).

## Evidence and evaluation

Coverage: PDF abstract/introduction and Figure 1; these describe the pipeline and motivation. §3 provides a running example and §8 evaluates against a loop-lifting implementation. Detailed translation/evaluation review is next.

## Limitations and tradeoffs

The core result targets nested multiset semantics. Trace ordering, duplicates, grouping, and aggregation requirements separately when applying the model to Jac (abstract; §9).

## My understanding and connections

AI research framing: A backend developer can request customers with nested order lists while compilation and stitching handle flat database results. This removes manual batching and nested-result reconstruction for the supported query fragment.

User interpretation: backend + SQL is the priority; paper-specific interpretations are open.

## Open questions

- Which nested Jac result types can be shredded, and what query-count and data-volume bounds follow from their shape?
- Which tasks are removed from application code, and which become explicit annotations?

## AI-assisted reading log

- 2026-10-21: Added local PDF, verified metadata, initial screening notes, and English slide scaffold.
  Version: Local PDF is arXiv:1404.7078v2, 2 May 2014, titled with the suffix (extended version); p. 1 identifies its SIGMOD 2014 relationship. Complete authors checked there. Canonical title/year/DOI also checked against the author-hosted conference PDF.

## Next reading step

Trace the query example through composition, compilation, database execution,
and result reconstruction. See the [backend + SQL guide](../../README.md#jac-backend--sql-reading-focus).
