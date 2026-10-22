# Links: Web Programming Without Tiers

Reading progress: queued. AI screening on 2026-10-21 inspected the PDF abstract,
introduction, and selected mechanism/evaluation excerpts. The section pointers
below guide further reading. Detailed guided reading is next.

## Motivation and problem

Collection focus stated by the user: reduce cross-layer and infrastructure work
across frontend, backend, database, and deployment in Jac.

## Main ideas and how they work

Paper mechanism: A single typed language spans browser, server, and database; the implementation generates JavaScript and SQL (§1; §§3–4).

## Evidence and evaluation

The author manuscript presents worked applications (§2), client/server translation (§3), query compilation (§4), and design issues (§6). Detailed evaluation extraction is a next reading task.

## Limitations and tradeoffs

Read the placement annotations and query-fragment restrictions in §§3–4 to establish exactly which decisions remain explicit.

## My understanding and connections

AI research framing: Connect unified full-stack programming to the existing Jac-to-SQL direction: what source-level information can be shared across UI, server logic, and query generation?

User interpretation: the user identified reducing cross-layer and infrastructure
work as the research direction; paper-specific interpretations are open.

## Open questions

- Which cross-layer consistency checks and query-generation rules could Jac express in one program?
- Which developer responsibilities disappear, and which become annotations or runtime constraints?
- What evidence measures programmer effort, and what evidence measures generated-code performance?

## AI-assisted reading log

- 2026-10-21: Added to the Jac full-stack/productivity collection with a local PDF,
  verified bibliography, initial screening notes, and an English slide scaffold.
  Version: Local PDF is a 30-page author manuscript marked Submitted to FMCO 06. Catalog year 2007 follows the Springer proceedings; conference year is 2006.

## Backend language + SQL co-design screening

Re-screened on 2026-10-21. Partial match to the user's language/database integration
target, with stronger backend transaction integration currently identified in Ur/Web.

§2, Database subsection (PDF pp. 10–11): the language provides database connections
and typed table handles. A table's type is distinct from the corresponding list of
records because the table supports mutation; `asList` exposes its query view.
Comprehensions, filters, ordering, and take/drop compile into SQL; mutation
statements are modeled on SQL insert/update/delete. The implementation targets
PostgreSQL, MySQL, and SQLite dialects.

§4 (PDF pp. 20–24): restricted source/SQL grammars and rewrite rules describe query
compilation. For the current project, separate the language's table/data semantics
from this compiler mechanism. The paper's broader scope is tierless web programming.

AI relevance assessment: useful as a partial language-design reference; prioritize
Ur/Web's schema/module/transaction semantics when looking for the closest existing
backend co-design candidate.

## Next reading step

Scope update (2026-10-21): user prioritizes backend + SQL. Start with §4 query
compilation; see the [focused guide](../../README.md#jac-backend--sql-reading-focus).

Read the main programming example, then trace a cross-boundary operation from
source to generated code/runtime behavior. Extract evaluation details before
making quantitative comparisons with Jac. See [collection guide](../../README.md#jac-full-stack-and-infrastructure-reading-set).
