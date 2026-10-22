# JacDB group meeting: language design and efficient queries

[English PDF slides](jacdb-language-design-discussion.pdf) ·
[Discussion notes](discussion-notes.md) · [Prior-work synthesis](prior-work.json)

The main discussion follows Research Problem → Problem Example → Solution →
Solution Example → Data → Discussion. It connects two research questions:
how the language simplifies database queries for programmers, and which compiler
optimizations make that programming model efficient. IC5 is the running example.

The appendix covers all 21 papers in paper-lib's `jac-backend-sql`, `jac-to-sql`
and `jac-fullstack-productivity` sets as inventoried on October 22, 2026.
The broader distributed-language papers supply design/evaluation lessons;
the database-language and transformation papers supply direct technical comparisons.
Each profile records the mechanism, inspected evidence and a concrete Jac question.
Paper notes and metadata are frozen under `sources/papers/`; full PDFs remain in
paper-lib, with verified hashes and source URLs in `paper-inventory.json`.
The source snapshots preserve reading-coverage distinctions and detailed caveats.

Measured evidence is read from adjacent checked-in artifacts:

- Historical source-burden classifications and the ten-rung IC5 SQL-count ladder.
- Reproduced littleX feed DB round-trip times and command counts from the same requests.
- Failed WeBridge compilation configurations retain their measured failure status.

The main deck labels historical evidence, reproduced measurements and proposed
analysis/evaluation separately. DB call time is the summed complete command/response
duration, including communication and server work. Jac runs on PostgreSQL;
Java/WeBridge runs on MySQL. Within-engine pairs support the controlled optimization
comparisons. Detailed metric definitions remain in `../webridge/non-snb/METHODS.md`.

## Build

Requires Python and matplotlib. From the jac-db repository root:

```sh
/home/baichuan/jaseci/jac-on-gpu/env/bin/python \
  research/jac-db-reproduction/group-meeting-language-design/build_slides.py
```

The builder checks historical input hashes, output parity gates, complete paper
coverage and measurement identities; emits a PDF, discussion notes and source
manifest; and checks page bounds in `verification.json`. Generation is CPU-only.

Suggested presentation: use the 26 main slides as a discussion pool and select
the relevant paper profiles during questions. The appendix supplies a complete
reference for the related-work collection.
