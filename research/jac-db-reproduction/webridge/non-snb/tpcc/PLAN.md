# TPC-C-derived transaction comparison

The source workload implements New-Order and Payment for one warehouse. The
comparison retains the original seed-4242 plan, including final-item rollback,
by-name upper-median selection, stock wraparound, and bad-credit customer data.

## Executable arms

`TpccSql.java` implements ordinary relational transactions using typed reads and
prepared statements. `TpccGraph.java` follows the captured Jac request sequence,
including identity, ACL, hydration, transaction boundaries, and eager write
flushes. Its pruned mode removes identity/schema checks, owner ACL hydration,
separate hop-result hydration, and type-registry maintenance. Genuine WeBridge records each source
program, replay the original native engine, synthesize its emitted procedures,
and execute those procedures through its original invocation manager.

All live work acquires the shared `../measurement_lease.py` lease. Native engine
and generated-procedure locks remain in use. Each mutating gate or measured
plan starts from an independent reset of the frozen fixture. Output equality
is paired with normalized database state checks; rollback requires unchanged
district counters, stocks, orders, lines, and edges after a partially processed
invalid order.

## Correctness cases

1. Successful New-Order with five and fifteen lines.
2. Missing final item after earlier valid lines, exercising real rollback.
3. Payment by customer ID and by last name, including good and bad credit.
4. Multiple same-last-name matches, preserving first-name sort and upper median.
5. A deterministic mixed plan against the same fresh initial state.

Generated node/edge identifiers and wall-clock timestamps are normalized only
for comparison. Business identifiers, quantities, balances, tax calculations,
customer data, and relationship counts remain exact oracle fields.

## Source-level semantic alignment

The Jac bad-credit prefix is `c_id,d_id,w_id,str(round(amount,2))|`. The existing
handwritten PostgreSQL benchmark uses a different five-ID prefix and fixed
two-decimal formatting. Our relational comparison follows the Jac expression;
the original benchmark difference is recorded rather than silently accepted.

The Java two-decimal helper rounds the exact binary double with half-even,
matching Python's `round(float, 2)` at binary rounding boundaries. Fixture
numeric values and source outputs will validate this choice before timing.

The original Jac HTTP loader initializes History with `h_data="seed"` and
`h_date=Customer.c_since`; the original relational JSONL has random history
text. `relational_fixture.py` declares that seed projection and saves a separate
matched fixture. The original relational-seed gate remains a diagnostic.

## Native access sequence

Both five-line and fifteen-line New-Order requests use one heterogeneous
`jobj_many` prefetch for all Item and Stock IDs. It includes the two absent
zero-ID references in the rollback case. The source flushes the District,
Placed edge and Order before that prefetch; it flushes modified stocks and
created line/edge nodes before the final missing-object fetch or commit.
Each flush maintains the type registry. These are actual writes inside the
request transaction, so rollback reverts earlier flushed mutations.

Warm native counts are 12/17/10/14/14/11/10 for the seven representatives.
The rollback's seventeenth command is PostgreSQL `DEALLOCATE ALL` after
ROLLBACK. The Java full port retains its sixteen graph/runtime/transaction
commands; MySQL driver work is recorded separately. The initial connection's
isolation setup and schema metadata are retained as cold setup work.

Graph UUIDs and sequence slots are allocated before the compiled region and
inside the whole-request timer. Their fresh values become explicit compiler
parameters, so repeated generated-procedure calls create distinct graph
objects and preserve monotonic edge order. Business-ID-to-JID mapping follows
the original HTTP driver's request preparation. Sequence gaps and generated
UUID spellings are outside the normalized business-state oracle.

## Oracle scopes

The source, seven procedure gates, and original 900-request plans retain full
normalized snapshots of all eight mutable relations. Monetary fields compare
by exact cents; original raw values remain in the native raw snapshots and
Java graph raw-mutated-anchor files. Representative latency cells retain the
affected customer/district/item footprint, new orders/lines, paying-district
histories and every global entity count. All oracle queries run outside the
request timers.

## Evidence to retain

Source and class SHA-256s; deterministic plans and fixture hashes; reset receipts;
actual SQL request census; native recorder resource logs; generated SQL and
compiler failures; output/state oracles; protocol request and response cycles;
raw timing rows and latency calibration; owned-session absence after bounded
calls; instrumentation snapshots and exact restoration receipts.

## Transaction-complete WeBridge integration

The final Java source captures JDBC `setAutoCommit(false)` and `setAutoCommit(true)` with each transaction body. A measured SDK probe records these controls as transaction nodes. The same probe records only the SELECT when transactions use raw Statement `BEGIN` and `COMMIT`. Upstream savepoint generation requires a transaction-begin node and a closing transaction node. Both direct Java and WeBridge execute the final JDBC dialect. Invalid-item requests perform a real rollback and restore the connection's auto-commit state; the restoration appears separately in the SQL ledger.

All business connections use SERIALIZABLE, read-only disabled, and the existing MySQL strict modes plus `NO_UNSIGNED_SUBTRACTION`. Connection setup runs before request timers and has its own environment/elapsed receipt. Procedure installation applies the same additive session mode and records `information_schema.ROUTINES.SQL_MODE`, because MySQL retains creation-time routine modes. The global SQL mode remains unchanged.

The preserved default-mode body-only Payment attempt executed a generated CALL, encountered an unsigned subtraction error in integer parsing, attempted `ROLLBACK TO null`, and repeated warehouse/district writes through source fallback. Its full-state gate rejected the resulting doubled YTD values. The final transaction-complete Payment-name-GC case passes all stages, returns the exact original output, preserves all eight mutable relations, and records one active CALL through API completion.

The SQL frontend compatibility layer extracts positional placeholders inside DML assignments/expressions and recognizes NUMERIC as the existing DECIMAL type. Each case freezes the exact overlay classes and SHA values alongside its source, schema, and inputs. Original frontend failures and the rejected runtime attempt remain separate records.

## Full-state oracle and reset proof

The graph oracle streams relevant nodes and typed parent edges once, resolves the same Customer/District, OrderLine/Order, and History/Customer dependencies as the original views, then sorts and serializes every original business column. Its eight exact JSONL digests match the frozen view-based post900 state. The measured full export takes 5.731 seconds, including a 3.589-second scan of 1,062,321 rows. Per-relation projection/sort/write times are retained.

Reset restores marked preexisting anchors from the immutable initial graph and removes postinitial sequence rows. A complete ordered digest of all 13 business columns verifies that both reset and initial databases contain 1,281,535 identical rows. The engine-specific row-version field has a separate dirty-marker check.
