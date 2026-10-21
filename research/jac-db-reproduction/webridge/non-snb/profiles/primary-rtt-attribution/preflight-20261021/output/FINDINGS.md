# Measured compact database-call RTT attribution

Existing compact capture only. CALL is one inclusive exchange; no nested P_S time added. Different engines/transport are explicit. Concrete SQL hashes are checked against catalogs. Category medians are not additive; only means reconcile.

|Case|Arm|Delay ms|n|Median RTT ms|Mean RTT ms|Largest category by mean|
|---|---|---:|---:|---:|---:|---|
|feed20 w|jac_final|0|30|13.167|13.207|type_registry: 10.347 ms|
|feed20 w|jac_original|0|30|13.635|13.602|type_registry: 10.255 ms|
|payment_name_GC w|java_conventional|0|30|3.838|3.888|transaction_or_session: 2.646 ms|
|payment_name_GC w|webridge_conventional|0|30|3.229|3.352|CALL_inclusive: 3.352 ms|
|feed20 w|java_conventional|0|30|9.516|9.649|business_SELECT: 8.689 ms|
|feed20 w|webridge_conventional|0|30|9.181|9.727|CALL_inclusive: 9.197 ms|

Each row is independently gated against the normalized primary median and request count. Per-request category sums and aggregate category means reconcile exactly. Raw SQL and their measured exchange costs are in attribution.json. These measurements identify costs; they do not establish an optimizer cause.

Unavailable selected cells: 0; their stage evidence remains in JSON.
