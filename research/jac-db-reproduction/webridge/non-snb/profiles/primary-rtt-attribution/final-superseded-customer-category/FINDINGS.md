# Measured compact database-call RTT attribution

Fresh compact capture. Source-aware classifiers identify native and MySQL SQL operations. Category means sum to mean request RTT; primary medians are computed per request. CALL costs cover the complete outer response. Engine and transport are recorded per arm. Concrete SQL hashes match their catalogs.

|Case|Arm|Delay ms|n|Median RTT ms|Mean RTT ms|Largest category by mean|
|---|---|---:|---:|---:|---:|---|
|feed20 w|jac_final|0|30|13.167|13.207|traversal.2hop.projection_acl: 8.755 ms|
|feed20 w|jac_final|10|30|173.629|181.202|acl.root_permissions: 34.640 ms|
|feed20 w|jac_final|2|30|46.501|52.544|traversal.2hop.projection_acl: 16.937 ms|
|feed20 w|jac_original|0|30|13.635|13.602|traversal.2hop.projection_acl: 8.736 ms|
|feed20 w|jac_original|10|30|227.773|230.662|acl.root_permissions: 36.310 ms|
|feed20 w|jac_original|2|30|59.895|64.714|traversal.2hop.projection_acl: 18.707 ms|
|feed200 w|jac_final|0|30|62.822|63.368|traversal.2hop.projection_acl: 57.179 ms|
|feed200 w|jac_final|10|30|237.698|244.196|traversal.2hop.projection_acl: 89.380 ms|
|feed200 w|jac_final|2|30|96.185|98.094|traversal.2hop.projection_acl: 61.998 ms|
|feed200 w|jac_original|0|30|63.798|64.233|traversal.2hop.projection_acl: 57.340 ms|
|feed200 w|jac_original|10|30|274.085|277.129|traversal.2hop.projection_acl: 78.978 ms|
|feed200 w|jac_original|2|30|108.687|108.422|traversal.2hop.projection_acl: 63.707 ms|
|mixed200 w15|jac_final|0|100|4.542|4.457|acl.root_permissions: 1.148 ms|
|mixed200 w15|jac_final|10|100|154.887|149.422|acl.root_permissions: 30.045 ms|
|mixed200 w15|jac_final|2|100|36.232|38.402|acl.root_permissions: 7.948 ms|
|mixed200 w15|jac_original|0|100|4.850|4.733|acl.root_permissions: 1.118 ms|
|mixed200 w15|jac_original|10|100|200.382|187.808|acl.root_permissions: 30.297 ms|
|mixed200 w15|jac_original|2|100|45.853|48.412|acl.root_permissions: 8.107 ms|
|payment_name_GC w|jac_final|0|30|4.197|4.263|transaction.commit: 1.585 ms|
|payment_name_GC w|jac_final|10|30|134.122|134.534|hydrate.generic_anchor: 54.375 ms|
|payment_name_GC w|jac_final|2|30|31.811|36.533|hydrate.generic_anchor: 13.799 ms|
|payment_name_GC w|jac_original|0|30|3.976|4.038|transaction.commit: 1.635 ms|
|payment_name_GC w|jac_original|10|30|135.226|141.652|hydrate.generic_anchor: 54.691 ms|
|payment_name_GC w|jac_original|2|30|31.993|35.225|hydrate.generic_anchor: 13.322 ms|
|payment_name_GC w|java_conventional|0|30|3.838|3.888|transaction.setting: 2.646 ms|
|payment_name_GC w|webridge_conventional|0|30|3.229|3.352|stored_procedure.call: 3.352 ms|
|payment_name_GC w|java_full|0|30|52.438|66.593|relational.customer.select: 35.287 ms|
|payment_name_GC w|java_pruned|0|30|36.754|38.711|relational.customer.select: 31.453 ms|
|payment_name_GC w|java_conventional|2|30|24.480|25.179|transaction.setting: 7.516 ms|
|payment_name_GC w|webridge_conventional|2|30|5.302|5.350|stored_procedure.call: 5.350 ms|
|payment_name_GC w|java_full|2|30|65.424|66.867|relational.customer.select: 33.863 ms|
|payment_name_GC w|java_pruned|2|30|55.120|58.619|relational.customer.select: 34.059 ms|
|payment_name_GC w|java_conventional|10|30|97.421|98.973|transaction.setting: 24.046 ms|
|payment_name_GC w|webridge_conventional|10|30|43.694|114.262|stored_procedure.call: 114.262 ms|
|payment_name_GC w|java_full|10|30|169.971|174.665|graph.anchor_query: 54.114 ms|
|payment_name_GC w|java_pruned|10|30|124.771|129.437|relational.customer.select: 49.862 ms|
|feed20 w|java_conventional|0|30|9.516|9.649|relational.lx_tweets.select: 8.689 ms|
|feed20 w|webridge_conventional|0|30|9.181|9.727|stored_procedure.call: 9.197 ms|
|feed20 w|java_full|0|30|74.162|76.527|traversal.2hop.projection_acl: 41.972 ms|
|feed20 w|java_pruned|0|30|57.003|60.614|traversal.2hop.projection_acl: 40.820 ms|
|feed200 w|java_conventional|0|30|81.531|82.582|relational.lx_tweets.select: 81.375 ms|
|feed200 w|webridge_conventional|0|30|81.098|82.401|stored_procedure.call: 81.863 ms|
|mixed200 w15|java_conventional|0|100|34.489|57.501|relational.lx_tweets.select: 53.555 ms|
|mixed200 w15|webridge_conventional|0|100|34.239|29.755|stored_procedure.call: 29.382 ms|
|feed200 w|java_full|0|30|401.730|407.024|traversal.2hop.projection_acl: 325.454 ms|
|mixed200 w15|java_full|0|100|188.449|168.195|graph.anchor_query: 148.824 ms|
|feed200 w|java_pruned|0|30|380.957|383.183|traversal.2hop.projection_acl: 316.348 ms|
|mixed200 w15|java_pruned|0|100|167.970|150.636|graph.anchor_query: 143.569 ms|
|mixed200 w15|webridge_pruned|0|100|166.739|153.265|stored_procedure.call: 150.053 ms|
|feed20 w|java_conventional|2|30|18.082|19.448|relational.lx_tweets.select: 9.769 ms|
|feed20 w|webridge_conventional|2|30|13.205|13.336|stored_procedure.call: 8.534 ms|
|feed20 w|java_full|2|30|116.976|121.193|traversal.2hop.projection_acl: 41.671 ms|
|feed20 w|java_pruned|2|30|69.139|70.774|traversal.2hop.projection_acl: 38.859 ms|
|feed200 w|java_conventional|2|30|90.311|92.238|relational.lx_tweets.select: 82.553 ms|
|feed200 w|webridge_conventional|2|30|83.841|84.553|stored_procedure.call: 79.737 ms|
|mixed200 w15|java_conventional|2|100|45.312|41.418|relational.lx_tweets.select: 30.977 ms|
|mixed200 w15|webridge_conventional|2|100|40.722|36.296|stored_procedure.call: 31.555 ms|
|feed200 w|java_full|2|30|445.802|470.121|traversal.2hop.projection_acl: 346.404 ms|
|mixed200 w15|java_full|2|100|233.392|211.565|graph.anchor_query: 156.387 ms|
|feed200 w|java_pruned|2|30|396.844|397.537|traversal.2hop.projection_acl: 318.335 ms|
|mixed200 w15|java_pruned|2|100|183.560|166.184|graph.anchor_query: 149.639 ms|
|mixed200 w15|webridge_pruned|2|100|176.605|198.071|stored_procedure.call: 188.296 ms|
|feed20 w|java_conventional|10|30|59.959|62.436|transaction.setting: 42.010 ms|
|feed20 w|webridge_conventional|10|30|38.950|40.093|transaction.setting: 20.899 ms|
|feed20 w|java_full|10|30|295.529|296.928|transaction.setting: 84.554 ms|
|feed20 w|java_pruned|10|30|139.141|140.561|traversal.2hop.projection_acl: 51.759 ms|
|feed200 w|java_conventional|10|30|125.955|129.907|relational.lx_tweets.select: 88.091 ms|
|feed200 w|webridge_conventional|10|30|102.758|103.281|stored_procedure.call: 82.420 ms|
|mixed200 w15|java_conventional|10|100|89.106|93.044|relational.lx_tweets.select: 48.944 ms|
|mixed200 w15|webridge_conventional|10|100|68.957|67.634|stored_procedure.call: 46.699 ms|
|feed200 w|java_full|10|30|602.334|605.969|traversal.2hop.projection_acl: 317.829 ms|
|mixed200 w15|java_full|10|100|407.199|376.338|graph.anchor_query: 184.071 ms|
|feed200 w|java_pruned|10|30|441.456|445.528|traversal.2hop.projection_acl: 311.490 ms|
|mixed200 w15|java_pruned|10|100|250.123|233.277|graph.anchor_query: 180.201 ms|
|mixed200 w15|webridge_pruned|10|100|203.823|219.523|stored_procedure.call: 165.065 ms|

Each row is independently gated against the normalized primary median and request count. Per-request category sums and aggregate category means reconcile exactly. Raw SQL and their measured exchange costs are in attribution.json. The concrete SQL table records measured exchange costs.

Unavailable selected cells: 21; their stage evidence remains in JSON.
