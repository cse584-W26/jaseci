# Ur/Web: A Simple Model for Programming the Web

Reading progress: reading. Backend-focused Lesson 1 on 2026-10-21 covers
typed persistent state and transaction/effect coordination. Detailed frontend
and implementation coverage remains open.

## Motivation and problem

User focus: simplify backend programming through language + SQL database
co-design over an existing SQL engine. Database-kernel changes are unnecessary.

## Main ideas and how they work

Paper mechanism: One statically typed functional language integrates HTML, SQL, client interaction, RPC, and channels; transactions and cooperative preemption provide the concurrency model (abstract; §§2–3).

## Evidence and evaluation

§4.1 reports Web Framework microbenchmarks. §4.2 describes deployed applications and feedback from their developers, including appreciation of client/server GUI integration and problems with sidedness diagnostics. Treat these as performance evidence and deployment/developer reports when designing a Jac study.

## Limitations and tradeoffs

Whole-program client/server sidedness analysis can produce confusing errors; compiler diagnostics and compile performance are explicit developer pain points (§4.2).

## My understanding and connections

AI research framing: compare language-level persistent state, transaction effects,
module boundaries, and runtime retry/notification management with the proposed Jac
backend model. Attribute reductions in developer work to specific mechanisms.

User interpretation: the user identified reducing cross-layer and infrastructure
work as the research direction; paper-specific interpretations are open.

## Open questions

- Which Jac cross-layer errors can be detected statically, and how understandable are the diagnostics?
- Which developer responsibilities disappear, and which become annotations or runtime constraints?
- What evidence measures programmer effort, and what evidence measures generated-code performance?

## AI-assisted reading log

- 2026-10-21: Added to the Jac full-stack/productivity collection with a local PDF,
  verified bibliography, initial screening notes, and an English slide scaffold.
  Version: Author-hosted POPL 2015 PDF; title, author, year, venue and DOI appear on PDF p. 1.

## Backend language + SQL co-design screening

Re-screened on 2026-10-21 for the user's clarified backend focus. Initial PDF
inspection identifies this as the closest existing candidate, with three concrete
language/runtime/database design links:

- §2.1, Fig. 1 (PDF pp. 2–3): SQL tables are declared in source as mutable
  multisets of typed records. SQL fragments are first-class, typed syntax trees.
- §2.1.1, Fig. 2 (PDF p. 4): ML-style modules encapsulate tables and abstract ID
  types. The compiler initializes the schema; startup checks it against source.
  Database access by external applications can bypass the language's encapsulation;
  the paper discusses separate database credentials for applications.
- §1 and §3.1 (PDF pp. 2, 9): remote calls are atomic units; server threads share
  state through the SQL database. Serialization failure triggers rollback and
  retry. The transaction monad and per-request private heaps support undoing the
  permitted effects. §3.2 delays channel sends until transaction commit.

The query interface exposes embedded SQL explicitly (§2.1); developers still
write SQL operations. The paper recommends PostgreSQL's serializable transactions
and explains the weakened semantics with engines lacking them (§3.1). The main
integration is in the language, types, and runtime over an existing SQL engine.

AI relevance assessment: inspect these backend mechanisms first. They directly
connect language abstraction/operational semantics to persistence and database
transactions. Developer-effort evidence requires the separate §4 evaluation.

Next screening step: trace one remote operation with a database update and a
channel send across a serialization failure, documenting the state/effects rolled
back and the work retained by the programmer (§§2.1.1, 3.1–3.2).

## Lesson 1: a backend operation as a typed transaction

### Running example

The chat-room example persists a message and notifies subscribers (Fig. 6, §2.3).
Teaching adaptation: expose a backend `post(room, text)` operation that inserts
the message and calls Ur/Web's channel `send`. If a serialization failure aborts
the transaction after notification work has been requested, pending notifications
must be coordinated with rollback/retry (§§3.1–3.2).

### Language/database design links

1. Source `table` declarations define typed persistent rows (§2.1, Fig. 1).
   Embedded SQL is desugared to typed AST constructors and checked with Ur's
   type system; programmers explicitly express SQL reads and writes.
2. Modules can hide tables and expose operations over abstract ID types
   (§2.1.1, Fig. 2). Schema initialization and startup checks tie these declarations
   to deployment. The paper's source-level abstraction is scoped to application
   code; separate database clients obey database permissions.
3. `transaction T` is an effectful computation returning T; `{}` is unit.
   In the example public interface, operations have transaction types. The remote
   call is the enclosing atomic execution boundary (§1; Fig. 2).
4. Runtime: server threads share state through the database; each remote call
   uses a private heap. SQL serialization failure triggers rollback and restarts
   execution, resetting managed request state (§3.1, PDF p. 9).
5. Managed channel sends accumulate in a thread-local log and are published at
   commit (§3.2, PDF p. 9). Failed-attempt send effects are held back. This example
   concerns Ur/Web-managed channels and serialization failures.

### Developer-facing effect

For the chat-room operation, the programming model handles transaction
boundaries, serialization-failure recovery, and coordinated channel delivery.
The programmer still specifies SQL statements and the application protocol.
These are language/type/runtime choices over the database's transaction semantics.

### Evidence inspected

§4.1 (PDF pp. 9–10) reports historical TechEmpower Round 9 fortunes results of
about 110,000 requests/s and 2.1 ms latency on the highest-capacity configuration
with 40 hardware/server threads. The paper explains that competing frameworks
provide different transaction semantics and reports transaction/restart overhead
on a write-heavy test. Use these as workload-specific system results.

§4.2 (PDF p. 10) reports deployed applications and developer feedback; its most
reported positive concerns client/server GUI integration, and a key pain point is
sidedness diagnostics. A proposed Jac study should directly measure backend
schema/module/transaction/effect-handling work for the target tasks.

### Connection to Jac

User clarification: an existing SQL engine is sufficient for co-design. AI
hypothesis: Jac may simplify backend work by specifying persistent-state types,
module ownership, atomic execution boundaries, and retry-safe effects together.
Next define one concrete operation, its permitted effects, and what happens to
SQL writes, local state, and notifications when serialization fails.

## AI-assisted lesson log

- 2026-10-21: User selected Ur/Web. Prepared Lesson 1 and an eight-page English
  PDF deck with editable Markdown/LaTeX, preserving backend focus. Technical
  claims cite §§2.1–2.1.1, 2.3, 3.1–3.2; evidence cites §4. User status is reading.

## Next reading step

Trace Fig. 6's subscriber table and pending-send behavior, then examine the
transaction effect model and its interaction with supported external code.
Continue the private-table/abstract-ID example in Fig. 2. See the
[lesson slides](slides.pdf) and [backend + SQL guide](../../README.md#jac-backend--sql-reading-focus).
