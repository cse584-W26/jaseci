# Interdisciplinary Programming Language Design

Reading progress: queued. AI screening on 2026-10-21 inspected the PDF abstract,
introduction, and selected mechanism/evaluation excerpts. The section pointers
below guide further reading. Detailed guided reading is next.

## Motivation and problem

Collection focus stated by the user: reduce cross-layer and infrastructure work
across frontend, backend, database, and deployment in Jac.

## Main ideas and how they work

Paper mechanism: Combines formal and performance analysis with user-oriented methods across requirements, prototyping, and evaluation (§1, Fig. 1; §4).

## Evidence and evaluation

Table 1 separates formal properties, execution properties, and effects on programmers, including learnability, error-proneness, modifiability, and local reasoning. §4 discusses methods for gathering different kinds of evidence.

## Limitations and tradeoffs

Choose methods and participant populations to match a specific language-design question (§1; Table 1), then define the tasks and outcomes before running a Jac comparison.

## My understanding and connections

AI research framing: Methodological foundation for testing whether Jac reduces cross-layer development and infrastructure work through task completion, errors, and change effort.

User interpretation: the user identified reducing cross-layer and infrastructure
work as the research direction; paper-specific interpretations are open.

## Open questions

- Which task study can separate learning the Jac language from the effort saved by its cross-layer abstractions?
- Which developer responsibilities disappear, and which become annotations or runtime constraints?
- What evidence measures programmer effort, and what evidence measures generated-code performance?

## AI-assisted reading log

- 2026-10-21: Added to the Jac full-stack/productivity collection with a local PDF,
  verified bibliography, initial screening notes, and an English slide scaffold.
  Version: Final author-hosted PDF. P. 1 gives complete authors, Onward! 2018 citation and DOI; this is the published-format version rather than the PL18 placeholder draft.

## Next reading step

Read the main programming example, then trace a cross-boundary operation from
source to generated code/runtime behavior. Extract evaluation details before
making quantitative comparisons with Jac. See [collection guide](../../README.md#jac-full-stack-and-infrastructure-reading-set).
