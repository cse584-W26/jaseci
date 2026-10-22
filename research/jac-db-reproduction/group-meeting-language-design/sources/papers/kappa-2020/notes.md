# Kappa: A Programming Framework for Serverless Computing

Reading progress: queued. AI screening on 2026-10-21 inspected the PDF abstract,
introduction, and selected mechanism/evaluation excerpts. The section pointers
below guide further reading. Detailed guided reading is next.

## Motivation and problem

Collection focus stated by the user: reduce cross-layer and infrastructure work
across frontend, backend, database, and deployment in Jac.

## Main ideas and how they work

Paper mechanism: Transforms Python code to support checkpointing across bounded serverless invocations and supplies task, future, and queue primitives through a coordinator (§3).

## Evidence and evaluation

§5 measures checkpointing and concurrency costs and evaluates five applications (§5.3). §6 discusses application changes required by the model and implementation restrictions.

## Limitations and tradeoffs

Programmers use Kappa concurrency primitives, annotate externally visible side effects, and sometimes insert checkpoints before long library calls. The evaluated compiler supports a subset of Python (§6).

## My understanding and connections

AI research framing: Study how a compiler/runtime absorbs serverless time limits and coordination work, and which annotations Jac would need to retain.

User interpretation: the user identified reducing cross-layer and infrastructure
work as the research direction; paper-specific interpretations are open.

## Open questions

- What source semantics let Jac safely manage deployment boundaries, retries, checkpoints, and external effects?
- Which developer responsibilities disappear, and which become annotations or runtime constraints?
- What evidence measures programmer effort, and what evidence measures generated-code performance?

## AI-assisted reading log

- 2026-10-21: Added to the Jac full-stack/productivity collection with a local PDF,
  verified bibliography, initial screening notes, and an English slide scaffold.
  Version: Author-hosted SoCC 2020 PDF; p. 1 confirms complete authors, title, year and DOI.

## Next reading step

Read the main programming example, then trace a cross-boundary operation from
source to generated code/runtime behavior. Extract evaluation details before
making quantitative comparisons with Jac. See [collection guide](../../README.md#jac-full-stack-and-infrastructure-reading-set).
