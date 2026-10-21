# Measured compact database-call RTT attribution

Fresh compact capture. Source-aware classifiers identify native and MySQL SQL operations. Category means sum to mean request RTT; primary medians are computed per request. CALL costs cover the complete outer response. Engine and transport are recorded per arm. Concrete SQL hashes match their catalogs.

|Case|Arm|Delay ms|n|Median RTT ms|Mean RTT ms|Largest category by mean|
|---|---|---:|---:|---:|---:|---|
|feed20 w|jac_final|0|30|13.167|13.207|traversal.2hop.projection_acl: 8.755 ms|
|feed20 w|jac_original|0|30|13.635|13.602|traversal.2hop.projection_acl: 8.736 ms|
|payment_name_GC w|java_conventional|0|30|3.838|3.888|transaction.setting: 2.646 ms|
|payment_name_GC w|webridge_conventional|0|30|3.229|3.352|stored_procedure.call: 3.352 ms|
|feed20 w|java_conventional|0|30|9.516|9.649|relational.lx_tweets.select: 8.689 ms|
|feed20 w|webridge_conventional|0|30|9.181|9.727|stored_procedure.call: 9.197 ms|

Each row is independently gated against the normalized primary median and request count. Per-request category sums and aggregate category means reconcile exactly. Raw SQL and their measured exchange costs are in attribution.json. The concrete SQL table records measured exchange costs.

Unavailable selected cells: 0; their stage evidence remains in JSON.
