# Eliom: A Core ML Language for Tierless Web Programming

Reading progress: queued. AI screening on 2026-10-21 inspected the PDF abstract,
introduction, and selected mechanism/evaluation excerpts. The section pointers
below guide further reading. Detailed guided reading is next.

## Motivation and problem

Collection focus stated by the user: reduce cross-layer and infrastructure work
across frontend, backend, database, and deployment in Jac.

## Main ideas and how they work

Paper mechanism: OCaml extensions interleave server, client, and shared declarations; typed client fragments support reusable widgets with both server and client behavior (§§1–2). The paper formalizes the core language, execution and compilation (§§3–5).

## Evidence and evaluation

The principal inspected evidence is the language example, type system, operational account, and compilation scheme (§§2–5). §1.2 identifies industrial users of the surrounding Ocsigen ecosystem.

## Limitations and tradeoffs

Programmers explicitly annotate execution locations and communication to control data placement and remote interactions (§1.3; §2).

## My understanding and connections

AI research framing: A direct reference for keeping all parts of one feature together while retaining explicit placement and typed communication in Jac.

User interpretation: the user identified reducing cross-layer and infrastructure
work as the research direction; paper-specific interpretations are open.

## Open questions

- Can a Jac component package frontend behavior, server behavior, and shared data types as a reusable unit?
- Which developer responsibilities disappear, and which become annotations or runtime constraints?
- What evidence measures programmer effort, and what evidence measures generated-code performance?

## AI-assisted reading log

- 2026-10-21: Added to the Jac full-stack/productivity collection with a local PDF,
  verified bibliography, initial screening notes, and an English slide scaffold.
  Version: 20-page author version. Title and authors checked on p. 1; 2016 publication and APLAS venue checked against Springer and the author publication list.

## Next reading step

Read the main programming example, then trace a cross-boundary operation from
source to generated code/runtime behavior. Extract evaluation details before
making quantitative comparisons with Jac. See [collection guide](../../README.md#jac-full-stack-and-infrastructure-reading-set).
