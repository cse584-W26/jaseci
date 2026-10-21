# Native Jac comparison

TPC-C uses the unchanged copied W1 application and seed42 data generator. The original runtime is c12ba889d484d7fcdfb3780ac98d416d1e13ec8b; final uses the retained32c5d1dbb Jac subtree. Both use the same PBS CPython3.14 runtime and original HTTP walker interface. The historical fb13 TPC-C run remains a separate reference.

`seed_tpcc.py` creates a fresh dedicated database using the application's original HTTP seed driver, then creates an immutable template after the service stops. `export_tpcc.py` exports every initial anchor and identity/type record. `census_tpcc.py` clones the template and executes seven original seed4242 transactions, in agreed order: original indices0,1,3,28,35,50,54. These cover GC/BC Payment by ID and last name,5/15-line NewOrder and invalid-item rollback. Each request retains the exact HTTP input/result, timing headers, database backend IDs and ordered PostgreSQL duration log. Before/after business counts and numeric totals run outside each capture window.

For writes, fresh initial state is restored before each compared arm/condition; each arm executes the same operation order. Generated UUIDs and `_now()` timestamps are retained in raw state and normalized explicitly in cross-language business-state comparison. They are not expected to match byte-for-byte across independent transactions. Payment uses the Jac application's BC history-string and upper-median-by-first-name semantics.

All live stages use the shared `non-snb/measurement_lease.py`. Quiet timing follows logging-off persistent-proxy0/2/10ms delay conditions, calibrated with actual SELECT1 roundtrips. SQL/protocol instrumentation runs separately. Services, database settings and owned server sessions receive explicit cleanup receipts. A15GB free-space reserve bounds retained captures; the same owned working clone is restored sequentially.

LittleX immutable historical fixture clone/export belongs to the littleX agent; native original/final HTTP execution will reuse those exact exported initial states. W1 includes own tweets, giving51×tier entries per user in these fixtures. W3 retains the original t200 write fractions0/5/15/30.
