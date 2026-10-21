# Measurement boundaries and evidence

## Program and fixture identity

The frozen contracts define 27 logical workloads, eight configurations and
three added database-response delays. `coverage-contract.json` enumerates all
648 latency cells. Original reference schedules are separate from these cells.
Every reset, captured program, generated procedure and result gate retains its
source and fixture identities.

Native Jac uses PostgreSQL 18. Java and WeBridge use MySQL 5.7. Each Java /
WeBridge pair shares its business source and database representation. The full
Java form ports the graph-access path, including the proven owner-root identity
condition and guest identity reads. Its alignment ledger identifies JDBC
transaction controls, native schema-cache guards and connection placement.
The pruned and conventional forms have their own source and state gates.

The Jac baseline uses the pinned earlier runtime: TPC-C c12 and littleX ad469
CONTROL. It retains the compiler's existing loop-prefetch batching. The optimized
configuration uses final32; exact source identities and defaults accompany each
pair in `runtime-provenance.json`.

## Primary SQL round-trip measurement

`RTT_MEASUREMENT_PLAN.md` defines the primary timing metric: the sum of complete
database command/response exchange durations within each request, measured by a
compact protocol proxy. The cell median is taken over per-request sums. SQL
counts come from the same requests. Database execution, communication, added
response delay and compact instrumentation are inside this boundary; application
work between database calls is outside it. All request-owned connections are
included. Observer and outside-request initialization commands are excluded; SQL
initialization triggered inside a tagged request remains included.

The original quiet application measurements and server-only analyses retain
their separate definitions and actual coverage. The primary RTT collectors use
new source-pinned output paths and do not relabel those earlier measurements.

## Secondary database-server execution cost

Database time per request is the sum of non-overlapping database-server statement
phases. PostgreSQL contributes Parse, Bind, Execute and simple-statement durations
from every connection used by the request. MySQL contributes outermost foreground
statement durations from Performance Schema; an outer CALL is counted once, while
its nested SQL supplies attribution. Observer and outside-request initialization
queries are excluded; initialization SQL inside a tagged request remains included.
These are server elapsed
times, including database waits and result production within the server timer.
They are distinct from database CPU time and from application or wire timing.

The controlled optimization comparisons are original/final Jac on PostgreSQL
and direct Java/WeBridge on MySQL, holding the representation and business source
fixed within each pair. Their DB-time ratios measure each optimization in its own
engine. Cross-engine absolute times describe the measured implementations;
statement counts and retained/eliminated business SQL identify their work
boundaries. Work executed inside a procedure remains part of the SQL inventory.

The existing instrumented profiles retain their transport conditions and sample
counts. A separate zero-added-delay native pilot removes the per-packet trace
proxy, records server durations, drains complete results and applies the
independent final-state gate. It covers two t20 full-feed arms. This diagnostic
retains its own scope; primary RTT coverage is recorded separately.

## Secondary application latency

Earlier native application latency covers HTTP client wall time. Available native server
total-plus-commit headers are retained as a secondary boundary; invalid-item
HTTP 500 rollbacks use client timing. Java latency covers the source application
method. Connection setup, fixture reset, full-result persistence and correctness
exports take place outside that method's timer. The two application boundaries
are named in each normalized row.

Quiet measurements disable profiling and hold the common host lease. The
protected interval contains reset, requests and the committed-state gate.
Application processes use logical CPUs 9 and 19. Native process CPU accounting
uses 10 ms ticks; Java retains per-thread CPU measurements. The timing scripts
record effective database settings and their exact restoration.

## SQL and synchronization

Primary count distributions come from the same compact-proxy requests as the
reported RTT medians: thirty measured requests for pure operations and the
complete one-hundred-slot measured schedule for mixed latency. The tables show
per-request count ranges; JSON and CSV retain exact histograms, measured command
totals and mean commands per request. Counts include
executed transaction and session commands. A stored-procedure CALL is one client
SQL command, while nested statements remain in the separate SQL-work inventory.

Earlier detailed profiles count actual complete command/response exchanges across all
traced database connections. PostgreSQL's Parse + Sync exchange is represented
even when it executes no SQL statement. The all-connection audits match raw
SQL, tags and backend PIDs, including queries preceding the native server timer.
littleX's guest identity queries use an auxiliary native backend. Early graph-PID
censuses and later all-connection profiles have explicit scopes.

MySQL profiles match JDBC session-status boundaries to complete wire responses.
They exclude the observer SHOW STATUS commands from application totals.
Performance Schema supplies actual stored-program statements, cursor opens and
CALL events. The analyzer verifies captured event counts against the server's
owned-thread totals. Cursor declarations are bound to generated SQL hashes.
Transaction controls, savepoints, metadata/result returns and business SQL have
separate categories. Nested statement timers overlap parent CALL time.

W1/W2 profiles retain the first three measured requests after ten warmup calls.
W3 profiles retain the full 100 measured-slot schedule after 110 warmup calls.
Per-request target aliasing and observed schema guards remain in the recorded
distributions. Quiet-run latency and instrumented timing have separate artifacts.

## Compiler outcomes and runtime paths

WeBridge artifacts retain baseline, record, native replay, synthesis, installation
and actual execution stages. Original frontend failures and explicit compatibility
overlays have separate receipts. Final transaction capture uses JDBC autocommit
boundaries. The MySQL session and routine-creation modes preserve strict flags
and add NO_UNSIGNED_SUBTRACTION.

Actual wire CALLs, remaining direct SQL and per-request runtime flags identify
active, mixed and fallback execution. Whole-plan routing records distinguish
requested shapes, available specializations and real runtime guard fallback.
littleX summaries retain the request-completion SDK-enabled flag separately
from actual CALL counts. For multi-region requests this flag describes the
final region; raw region records and inside/outside SQL show the full path.
Compiler-stage failures have stage artifacts in the matrix. Executed requests
receive latency values only after their result and state gates pass.
One failed source capture supplies the same stage evidence to its three
response-delay cells. The coverage totals distinguish these terminal cells
from the number of compilation attempts and actual timed runs.

## Independent correctness and public storage

TPC-C's independent Python model evolves the original seed through every
transaction and compares all eight mutable business relations at cent precision.
Full 900-request gates, repeated representative cells and affected-row profiling
snapshots have distinct scopes. A failed whole-plan committed-state check is
retained separately from successful representative-cell measurements.
`seed-inputs/` retains the exact seed-42 JSONL files, original manifest and
hash-verified generator. The independent model selects this portable copy
automatically when its manifest is present.

littleX's independent source-fixture model checks every returned business field,
feed order and state transition. Final gates compare actual Profile, Tweet and
Follow state against the evolved model; duplicate Follow edges are observable.
Paired direct/procedure equality is retained in addition to model checks.

Large response streams use lossless indexed JSONL chunks with ordered part and
whole-stream hashes. Identical gzip state payloads share content-addressed
objects through relative links. `archive-manifest.json` records original gzip
hashes, retained object hashes and exact uncompressed hashes. The archive and
result-link verifiers check public paths independently of the collection tree.
Indexed response chunks retain their exact compressed bytes, preserving their
recorded part hashes. `verify_chunks.py` independently reconstructs every
indexed stream in order and checks part sizes, row counts and the complete
uncompressed stream hash inside the public archive.

### SQL aggregation boundaries

Distinguish statement-level batching (Jac hydration and object flush), request-level execution bundling (multiple SQL statements inside a WeBridge CALL), and removed runtime setup. The SQL-category profiles record all three separately. A CALL can reduce frontend synchronization while retaining multiple internal business SQL statements.

### Unicode connection verification

The original littleX data contain four-byte Unicode. The extended JDBC driver's default connection rejected emoji writes; a collation-only URL allowed INSERT but two later Tweet mutations changed existing emoji into four question marks. Byte-level round-trip probes identified explicit `SET NAMES utf8mb4 COLLATE utf8mb4_bin` as the effective connection initialization. The final snapshot preserves the business source and SQL, records the initialization queries outside each API timer, and passes the original 210-request mixed schedule against exact final entity/relation rows. `littlex/connection-init-fix` and its pointer retain the source comparison, session settings, probes and before/after state evidence. Superseded matrices are excluded explicitly; final latency and original-schedule references use the corrected initialization consistently.
