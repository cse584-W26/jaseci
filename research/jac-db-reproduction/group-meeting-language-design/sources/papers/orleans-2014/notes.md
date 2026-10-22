# Orleans: Distributed Virtual Actors for Programmability and Scalability

Reading progress: queued. AI screening on 2026-10-21 inspected the PDF abstract,
introduction, and selected mechanism/evaluation excerpts. The section pointers
below guide further reading. Detailed guided reading is next.

## Motivation and problem

Collection focus stated by the user: reduce cross-layer and infrastructure work
across frontend, backend, database, and deployment in Jac.

## Main ideas and how they work

Paper mechanism: Virtual actors provide stable logical identities while the runtime manages physical activation and placement. Interfaces and asynchronous calls expose application behavior (§2); runtime mechanisms are detailed in §3.

## Evidence and evaluation

The report presents production applications (§4) and performance experiments (§5). Use these as deployment experience and system-performance evidence.

## Limitations and tradeoffs

Actor interfaces, asynchronous interaction, persistence, and messaging guarantees remain part of the programming model (§§2–3). Trace their semantics before comparing application effort.

## My understanding and connections

AI research framing: Reference for moving object location, activation lifecycle, and distributed resource management from Jac application code into a runtime.

User interpretation: the user identified reducing cross-layer and infrastructure
work as the research direction; paper-specific interpretations are open.

## Open questions

- Which distributed-state and lifecycle decisions would a Jac developer still need to specify?
- Which developer responsibilities disappear, and which become annotations or runtime constraints?
- What evidence measures programmer effort, and what evidence measures generated-code performance?

## AI-assisted reading log

- 2026-10-21: Added to the Jac full-stack/productivity collection with a local PDF,
  verified bibliography, initial screening notes, and an English slide scaffold.
  Version: Title and authors checked against PDF p. 1; report identifier and March 2014 date checked against Microsoft Research publication page.

## Next reading step

Read the main programming example, then trace a cross-boundary operation from
source to generated code/runtime behavior. Extract evaluation details before
making quantitative comparisons with Jac. See [collection guide](../../README.md#jac-full-stack-and-infrastructure-reading-set).
