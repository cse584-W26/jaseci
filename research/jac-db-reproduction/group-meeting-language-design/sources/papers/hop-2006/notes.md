# Hop, a Language for Programming the Web 2.0

Reading progress: queued. AI screening on 2026-10-21 inspected the PDF abstract,
introduction, and selected mechanism/evaluation excerpts. The section pointers
below guide further reading. Detailed guided reading is next.

## Motivation and problem

Collection focus stated by the user: reduce cross-layer and infrastructure work
across frontend, backend, database, and deployment in Jac.

## Main ideas and how they work

Paper mechanism: Packages application logic and GUI code together while distinguishing their execution levels. Cross-level function calls, data exchange, and event loops connect the two sides (abstract; §§2–4).

## Evidence and evaluation

Language constructs and examples (§§2–5), implementation sketch (§6), and design discussion (§7) provide the initial evidence for screening.

## Limitations and tradeoffs

Hop primarily targets interactive GUI applications; database access is provided by libraries (§1.1). Use its staging and communication model for the client/server comparison.

## My understanding and connections

AI research framing: Study how a unified syntax exposes execution boundaries and asynchronous communication without requiring hand-written inter-language glue.

User interpretation: the user identified reducing cross-layer and infrastructure
work as the research direction; paper-specific interpretations are open.

## Open questions

- What should a Jac programmer explicitly write to distinguish local UI behavior from remote application logic?
- Which developer responsibilities disappear, and which become annotations or runtime constraints?
- What evidence measures programmer effort, and what evidence measures generated-code performance?

## AI-assisted reading log

- 2026-10-21: Added to the Jac full-stack/productivity collection with a local PDF,
  verified bibliography, initial screening notes, and an English slide scaffold.
  Version: Author-hosted PDF; p. 1 confirms authors and 2006 OOPSLA notice. DLS 2006 conference program confirms the presentation venue.

## Next reading step

Read the main programming example, then trace a cross-boundary operation from
source to generated code/runtime behavior. Extract evaluation details before
making quantitative comparisons with Jac. See [collection guide](../../README.md#jac-full-stack-and-infrastructure-reading-set).
