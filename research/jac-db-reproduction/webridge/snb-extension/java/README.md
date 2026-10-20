# Full and pruned Java programs

`SnbAccess.java` preserves the original graph-store session, ordered directed/undirected hops, request-local anchor map, identity context, ACL checks, schema lookup, read-only transaction, and transaction-setting command. The full configuration uses these paths unchanged. The pruned configuration switches off identity, ACL, schema verification, and separately hydrated graph objects; hop results project the required archetype data instead. All variants retain the business traversal and ordering.

`SnbWeBridge.java` wraps the same request body with the original WeBridge recorder, native concolic engine, SQL synthesizer, and stored-procedure invocation manager. The region begins after the original transaction-setting command and ends before commit. These outer commands execute on every request. Each input's scalar parameters are symbolized; the service identity remains the fixed benchmark account.

`control.py` compiles and runs isolated query/variant cases, records source/input hashes and commands, and uses the existing process-group resource supervisor. Native captures share the original engine graph-file lock. Existing numeric-width, JDBC string decoding, and SQL frontend compatibility overlays are reused explicitly in the classpath.

Porting gates: native Jac SQL census, original-input result equality, independent server command counts, successful original-engine capture/synthesis/install/CALL, and per-request stored-procedure activation. Native PostgreSQL SQL constructs must be checked against the artifact's MySQL 5.7 before any cross-engine adaptation is declared equivalent.
