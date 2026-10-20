# Native JSON result type compatibility

Actual conventional IS2 synthesis failed first in TypeConverter and then in SQLVarType because the shared Person mirror declares native JSON. The reference consumes that JSON through JDBC String getters.

Two isolated dispatch mappings route JSON to the compiler's existing longtext/LONGTEXT category. This preserves the full payload width, including values exceeding VARCHAR(512). The original SQL and procedure generation algorithm are unchanged. Original-source SHA256, diffs and actual failed synthesis logs are retained; JSONTypeTest verifies ten existing mappings and the JSON dispatch. The successful retry uses the same immutable original-engine graph.
