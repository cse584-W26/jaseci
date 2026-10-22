# LINQ: Reconciling Objects, Relations and XML in the .NET Framework

Reading progress: queued. AI screening on 2026-10-21; coverage recorded below.

## Motivation and problem

User's scope: reduce backend + SQL programming work through Jac language design.

## Main ideas and how they work

Paper mechanism: The one-page overview introduces composable standard query operators. Its DLinq section describes expression trees translated to SQL, conversion of returned tables to objects, object navigation compiled into joins, and change tracking with generated update commands (p. 706).

## Evidence and evaluation

Coverage: complete one-page overview. It explains the architecture and examples; use the follow-up papers for detailed semantics and evaluation.

## Limitations and tradeoffs

SQL translation is supplied by the relational provider. Treat query operators, provider translation, and object change tracking as distinct responsibilities (p. 706, DLinq).

## My understanding and connections

AI research framing: A concrete backend + SQL model: source-language queries and typed objects replace hand-written SQL construction and result mapping for supported operations.

User interpretation: backend + SQL is the priority; paper-specific interpretations are open.

## Open questions

- Which object/schema mappings and query operators should Jac provide, and which changes require an explicit database write?
- Which tasks are removed from application code, and which become explicit annotations?

## AI-assisted reading log

- 2026-10-21: Added local PDF, verified metadata, initial screening notes, and English slide scaffold.
  Version: Author-hosted one-page SIGMOD 2006 overview, p. 706. Title, complete authors, and 2006 venue/date checked against the PDF.

## Next reading step

Trace the query example through composition, compilation, database execution,
and result reconstruction. See the [backend + SQL guide](../../README.md#jac-backend--sql-reading-focus).
