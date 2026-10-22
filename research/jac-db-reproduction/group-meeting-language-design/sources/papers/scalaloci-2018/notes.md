# Distributed System Development with ScalaLoci

Reading progress: queued. AI screening on 2026-10-21 inspected the PDF abstract,
introduction, and selected mechanism/evaluation excerpts. The section pointers
below guide further reading. Detailed guided reading is next.

## Motivation and problem

Collection focus stated by the user: reduce cross-layer and infrastructure work
across frontend, backend, database, and deployment in Jac.

## Main ideas and how they work

Paper mechanism: Placement types associate values with peers; language-level architecture definitions and distributed reactive data flows support multi-peer applications while generating communication and data conversions (§§1–2; §7).

## Evidence and evaluation

§8 uses case studies, implementation variants, code metrics, and runtime benchmarks. Table 1 (p. 129:22) counts LOC, callbacks, imperative state updates, cross-host composition, and remote accesses. §8.1 reports 63% communication-boilerplate reduction for its Play/Scala.js port, with a Todo behavior difference explicitly described in that comparison.

## Limitations and tradeoffs

Placement and topology remain language-level design choices (§2). Check the exact baseline and feature differences before reusing the case-study code-reduction result (§8.1).

## My understanding and connections

AI research framing: Provides both a concrete distributed language design and useful code-burden metrics for evaluating Jac across multiple execution locations.

User interpretation: the user identified reducing cross-layer and infrastructure
work as the research direction; paper-specific interpretations are open.

## Open questions

- Which responsibilities move into Jac types, generated communication, and runtime connection management, and what remains in application code?
- Which developer responsibilities disappear, and which become annotations or runtime constraints?
- What evidence measures programmer effort, and what evidence measures generated-code performance?

## AI-assisted reading log

- 2026-10-21: Added to the Jac full-stack/productivity collection with a local PDF,
  verified bibliography, initial screening notes, and an English slide scaffold.
  Version: Author PDF; p. 1 gives complete authors, 2018 PACMPL/OOPSLA citation and DOI.

## Next reading step

Read the main programming example, then trace a cross-boundary operation from
source to generated code/runtime behavior. Extract evaluation details before
making quantitative comparisons with Jac. See [collection guide](../../README.md#jac-full-stack-and-infrastructure-reading-set).
