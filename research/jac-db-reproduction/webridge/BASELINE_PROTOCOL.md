# Jac–Java–WeBridge baseline protocol

The baseline has two sequential stages. Each stage has its own source, validation receipts, SQL counts, and timings.

## Stage 1: reproduce Jac execution

The Java port reproduces the Jac request, including identity/context lookup, schema initialization, permissions, object hydration, graph traversal order, and transaction boundaries. For every input, validate both the returned result and the number of SQL commands observed independently at the database. Record cold initialization and warm execution separately.

The reference is `alignment/AlignedIc5.java`. Its source hash, all-input gates, query-category correspondence, and independent database counters are recorded under `alignment/`.

The shared execution boundary starts with the service identity already authenticated and includes identity/root resolution plus the database-backed request body. HTTP parsing and token cryptography precede this boundary. Java baseline and optimized timings use this same boundary. Jac captures establish the input/result/database-behavior correspondence; cross-language timing comparisons must state their ingress boundaries explicitly.

## Stage 2: remove Jac-specific overhead

Starting from the validated full port, remove individual runtime services whose benchmark preconditions permit replacement. Record the removed work, replacement, precondition, and source hash in `alignment/removal-ledger.json`. Validate all input results and retained domain traversal counts after each ablation. Report cumulative and individual effects where measured.

The candidate services are identity/context setup, cold schema discovery, permission evaluation under the declared single-owner fixture, and full runtime object hydration. The domain traversal algorithm, date predicate, membership tests, sorting, result limit, and transaction remain the reference computation.

## WeBridge compatibility and measurement

Track JDBC access adaptations, explicit compilation-region boundaries, and SQL frontend changes separately under `integration/`. Validate their complete-request results and SQL behavior against the relevant baseline stage before measuring WeBridge.

For each measured configuration, report complete-request time, application-to-database commands, table-access work, compilation cost, generated procedures, and fallback behavior. Preserve the original engine's captured graphs and failure logs alongside successful runs.

## Original-paper reproduction

Maintain the original My-Blog/WeBench experiment as a separate experiment under `paper/` and `paper-audit/`. Its protocol records paper settings, artifact repairs, machine topology, raw latency samples, and SQL census. Use it to validate the original WeBridge installation and behavior.
