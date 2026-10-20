# Typed-symbol numeric width repair

The unmodified graph explicitly labels the request timestamp as JVM descriptor
`J`. The released parser creates an untyped `SymbolicInteger` for descriptors
B/C/I/J/S, after which SQL type collection infers INT from its default bounds.
Actual invocation of the original generated INT parameter with1348704000000
failed with `MysqlDataTruncation: Out of range value`, then the original driver
fell back to ordinary execution.

This isolated compiler overlay preserves J's `Types.T_LONG` during parsing and
preserves integer typecode/bounds when alpha-renaming creates a new symbol.
The original optimizer, graph, SQL statements, bound values and returned columns
are retained. The overlay also carries the separately tested SQL frontend
coverage extension. `prepare.py`, `overlay.diff`, `rename-overlay.diff` and
`provenance.json` record the complete changes.

`WidthAudit.java` checks parser→type collection preserves I→INT and J→BIGINT.
`type-boundaries.json` lists each declared domain's boundaries, including the
actual timestamp beyond INT_MAX; these are static declaration checks. Actual
repaired stored-procedure invocation is recorded separately.

Use a fresh API/case when changing compiler types. Re-synthesis into an existing
case can import previously serialized INT metadata during version merging; the
retained same-case attempts demonstrate this behavior. Clean-case synthesis in
`cases/tiny-region-width-cold-20261020` produces a BIGINT timestamp parameter.
