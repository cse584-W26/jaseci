# Transaction and SQL frontend compatibility audit

The original whole-request typed-JDBC capture contains28SQL nodes. Its START TRANSACTION READ ONLY, SET SESSION innodb_lock_wait_timeout=10 and COMMIT nodes all have `isTxnControl=false`. The application submits these through Statement.execute; the original extended driver's SP interception targets PreparedStatement and Connection transaction APIs.

The original synthesizer's transaction-specific parser accepts `isTxnControl=true` records for Connection.setAutoCommit(false/true) and Connection.commit. Its regular SQL visitor assigns statement types only to SELECT, INSERT, UPDATE and DELETE. Therefore upgrading Druid's parser alone would not establish correct transaction compilation.

| Candidate | Preserved behavior and remaining boundary |
|---|---|
|Keep original Statement.execute|Exact28-query baseline preserved; captured transaction SQL is not consumed by the online SP interceptor. An SP containing those commands would risk duplicate transaction execution.|
|PreparedStatement.execute|The upstream SP manager's doExecute is a stub returning true; this API is unsuitable for generic command adaptation.|
|PreparedStatement.executeUpdate|Retains SQL text/order and reaches the online interceptor, but START READ ONLY/SET/COMMIT still lack regular visitor statement types and control markers.|
|Connection transaction APIs|Original engine supports setAutoCommit and commit; preserving read-only characteristics and restoring the original connection state introduces different SQL/state transitions. It is a separate transaction adapter requiring a new ledger and gate.|
|Explicit body API region|Preserves every original statement and full request timing. START READ ONLY/SET execute before the region; COMMIT executes once afterward. Only the body is submitted to the original engine. This is an explicit frontend boundary, not automatic whole-request coverage.|

The coordinator approved the body-region experiment. `prepare_region.py` generates its derivative and a no-op baseline hook. `region-ledger.json` and `region-compatibility.diff` document its exact source changes. Original WeBridge graph-analysis/synthesis/invocation code remains unchanged, and captured graphs are passed through without pruning.

## Executed findings

The original exact Java helper first fails replay at MultipleRowResultSetImpl.getMetaData; getObject(int) is also unimplemented. The separate declared-arity/getString helper adapter retains SQL/counts/runtime behavior and is documented in compatibility-ledger.json.

The typed whole-request synthesizer then fails on START TRANSACTION READ ONLY in Druid1.1.21. Its unmodified graph and exception are retained under cases/tiny-typed-cold-20261020.

The body-region record preserves28source calls and28independent server Questions, captures21body SELECTs, and replays all21results with oracle success. Replay independently submits7statements:4cold prefix queries plus the three retained transaction/session commands. Its unmodified graph is under cases/tiny-region-cold-20261020/replay-20261020T183952616652Z/graph.json.

Original synthesis of that body graph fails at SQLAstVisitor.handleWhere on the inheritance `IN (SELECT type_name FROM graph_types WHERE ancestor=?)` predicates. No generated procedure exists from this attempt.

## Scope-aware visitor extension requirements

An offline audit using the original visitor measured:

| SQL | Actual outer columns | Visitor metadata |
|---|---:|---|
|Simple control|1|1column, success|
|IN-subquery|1|2columns already collected before unsupported exception|
|Derived UNION e.* control|2|29columns, visitor returns successfully|
|Actual first Knows hop|2|16columns collected before unsupported exception|

Evidence: sql-boundaries/original-audit-20261020T184557704514Z/report.json. Thus merely skipping unsupported IN-subquery nodes would leave incorrect result metadata.

A correct separately labelled frontend extension must:

1. Retain the original SQL AST, inheritance predicates, UNION, ordering and bound values.
2. Use schema resolution throughout nested scopes while collecting result metadata only for the outermost projection.
3. Collect parameters globally by lexical placeholder index, including inner predicates and JOIN conditions, preserving the original13/14binding order.
4. Infer each placeholder's SQL type from its actual comparison/schema expression; reject unresolved types explicitly.
5. Preserve result-set column position, names/aliases and duplicates expected by the original runtime.
6. Exercise simple SELECT, mixed outer/inner placeholders, empty and multiple subquery results, UNION aliases and IN null/duplicate semantics; then replay actual captured graphs and check generated SP behavior.

All20source result/count/category gates precede derivative performance measurements. Compiler-frontend compatibility repairs are reported separately from removal of Jac-specific runtime overhead.
