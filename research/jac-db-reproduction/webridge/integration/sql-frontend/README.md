# Isolated SELECT frontend extension

This overlay adds SQL metadata support for the IC5 graph-hop queries while preserving their original SQL text and bindings. It retains the original visitor's public ABI and lives ahead of `basic-components.jar` on the classpath. The original artifact source and dependency jars remain the comparison baseline.

The original visitor registers every nested SELECT's projection as a JDBC result column, and rejects IN-subquery predicates. Its parameter list follows visitor scope completion rather than the statement's positional binding indices. The overlay resolves three separate concerns:

1. Schema traversal still visits every nested SELECT/UNION scope; result metadata comes from the outer SELECT projection only. Derived columns resolve through their own query/table scope.
2. IN-subqueries remain intact and their nested parameters participate in the same metadata pass. SQL predicates and type-ancestor semantics are retained.
3. Positional `?` parameters are registered by Druid's original `SQLVariantRefExpr.index`, with types inferred from their actual comparison/IN/cast/limit context. Missing, duplicated, or unresolved positional metadata raises an error.

`select_extension.java.fragment` contains the independent SELECT metadata pass. `prepare_overlay.py` copies the original visitor and substitutes its SELECT handlers, producing `overlay.diff` and SHA-256 provenance. The original INSERT/UPDATE/DELETE handler bodies remain intact.

Run the offline tests with:

```bash
reproduction/webridge/integration/sql-frontend/test.sh
```

The 13 cases include the four retained original regressions, mixed parameter types across nested SELECT/JOIN/LIMIT scopes, literal limits, literal IN lists, JSON-date casts, the four-column scalar Forum projection, nested IN-subqueries, and original aggregate/UPDATE/INSERT controls. Each case checks result-column scope and expected positional type/column order where specified, and asserts that visiting leaves the SQL AST text unchanged. `test-results.json` retains the outcomes. `basic-report.json` also retains the original AstAudit output with the overlay prioritized.

Classpath entry:

```text
/home/baichuan/jaseci/reproduction/webridge/integration/sql-frontend/classes
```

Place it before the original dependency jars. The integration agent's `control.py --frontend-overlay` records the selected overlay for each attempt. Original tiny-region synthesis with this overlay succeeded in `integration/cases/tiny-region-cold-20261020/synth-20261020T185541349162Z`; its subsequent stored-procedure invocation validates the generated procedure's runtime behavior separately.

The implementation infers types for the declared query forms. A UNION whose corresponding derived columns require distinct type coercions requires explicit additional metadata and currently raises an error. This keeps unknown type decisions observable in the experiment.
