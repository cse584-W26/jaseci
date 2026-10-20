# Recorded parameter type metadata compatibility

The original conventional IC13 graph contains a CASE condition `?=?`. SQL-column inference cannot determine either operand's type, and synthesis failed with `Cannot infer positional parameter 0`. The same graph explicitly records both operands and all later UUID parameters as `_java_type: java/lang/String`.

This isolated overlay forwards those existing recorded JVM type facts from StoredProcedureManager to SQLAstVisitor. Its fallback applies only after the existing CAST, column, IN-list and limit inference paths cannot resolve a parameter. Known primitive JVM descriptors and String map to their existing SQL types. Missing or unknown facts remain errors. The original SQL, graph, symbolic engine and procedure generation algorithms remain unchanged.

`build.py` reproduces the overlay and records original/patched source SHA256 and diffs. `BindTypeTest.java` verifies that recorded String facts resolve ambiguous parameters and that the same statement without those facts still fails. The actual failed and successful synthesis attempts are retained in the conventional IC13 case.
