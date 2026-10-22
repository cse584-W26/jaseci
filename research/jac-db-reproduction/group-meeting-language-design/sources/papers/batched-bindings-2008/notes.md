# Rewriting Procedures for Batched Bindings

Reading progress: queued. Bibliography verified. Preparation coverage: abstract and first-page material.

## Motivation and problem

Paper claim: The abstract (PDF p. 1) describes rewriting repeated query or procedure invocations into batched forms and rewriting the invoked procedure to accept a batch of parameters.

## Main ideas and how they work

Detailed mechanism review: next reading task.

## Evidence and evaluation

Evaluation review: pending. Record workload, baseline, metric, and page/figure references during reading.

## Limitations and tradeoffs

Investigate the assumptions that affect the proposed Jac-to-SQL application.

## My understanding and connections

AI research connection: Study the transformation from a Jac loop issuing one parameterized query per item to a set-oriented operation over all parameter bindings.

Related reading: [WeBridge](../webridge-2024/notes.md), completed by the user on 2026-10-21.

## Open questions

- Which dependencies and side effects permit batching, and how are results matched back to their input bindings?

## AI-assisted reading log

2026-10-21: added to the user-approved Jac-to-SQL reading set; downloaded and parsed the PDF, verified the bibliography, and inspected first-page material for reading preparation.

## Next reading step

Read the motivating example and core transformation, then answer the project question above with section/page references.
