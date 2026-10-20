# What each WeBridge CALL replaces

The independent offline verifier `audit_operation_map.py` reconstructs each request from the two surrounding status observers in raw `protocol.jsonl`. Every command has one fully received and one fully delivered response; the next command follows complete delivery. The following counts hold for all three post-warm requests in each arm. Response frames are MySQL protocol frames, not TCP packets.

| Java input | Direct command/response cycles | WeBridge cycles | Direct result sets | WeBridge result sets | Direct response frames | WeBridge response frames |
|---|---:|---:|---:|---:|---:|---:|
| Full graph-runtime behavior | 38 | 4 | 35 | 36 | 276 | 970 |
| Pruned runtime behavior | 31 | 4 | 28 | 29 | 176 | 608 |
| Set-oriented SQL aggregate | 4 | 4 | 1 | 2 | 9 | 17 |

Every request retains three outer transaction commands: START TRANSACTION READ ONLY, SET SESSION innodb_lock_wait_timeout=10, and COMMIT. WeBridge replaces the recorded business region with one CALL. Full Java has 35 original SELECTs in that region; pruned Java has 28; set-oriented Java already has one aggregate SELECT.

Performance Schema directly nested CALL events reveal what executes inside that CALL:

| Java input | Direct table SELECTs | Cursor materializations of original table SELECTs | Result/parameter metadata SELECTs | Variable/control events |
|---|---:|---:|---:|---:|
| Full | 25 | 10 | 11 | 2,447 |
| Pruned | 24 | 4 | 5 | 1,510 |
| Set-oriented | 1 | 0 | 1 | 12 |

Executed business categories are verified from actual direct P_S SELECT text and cursor-open events. Each cursor is matched to its generated declaration, literal query parameters and the following observed cursor-count metadata SELECT (the numeric cursor IDs must agree):

| Executed table operation inside CALL | Full | Pruned | Set-oriented |
|---|---:|---:|---:|
| Hydration | 7 | 0 | 0 |
| Knows | 2 | 2 | 0 |
| HasMember | 10 | 10 | 0 |
| ContainerOf | 1 | 1 | 0 |
| HasCreator | 15 | 15 | 0 |
| Set-oriented aggregate | 0 | 0 | 1 |

Thus full and pruned WeBridge retain 35 and 28 original table operations respectively. Their cursor materializations execute original SELECTs; cursor fetches, assignments and jumps are separate stored-program work. Metadata SELECT counts include the cursor result serialization SELECTs plus the final QUERY_ID/parameter SELECT. This explains why these counts are one higher than the older `result_select` subtotal, which classified only the cursor prefix. The set-oriented procedure retains its aggregate and adds one metadata SELECT.

The machine-readable `webridge-operation-map.json` includes the observed command sequences, all three receipts per arm, the exact direct-child P_S events for the last CALL, source paths and SHA256 of each generated procedure. Descendants nested beneath a direct child are excluded from event totals to avoid counting the same work twice. Protocol and P_S capture runs are diagnostic, separate from the uninstrumented latency sweeps.

Jac's independently reconstructed SQL operation map is `jac-comparison/roundtrip-profile/results/operation-map.json`, embedded in the machine-readable comparison. The selected request changes as follows:

| PostgreSQL operation | Jac original | Jac final |
|---|---:|---:|
| Outer transaction commands | 3 | 3 |
| Hydration SELECTs | 7 | 5 |
| Knows traversals | 2 | 2 |
| HasMember traversals | 10 | 1 batched traversal |
| HasMember/Forum type probes | 0 | 2 |
| ContainerOf traversal | 1 | 0 |
| HasCreator traversals | 15 | 0 |
| Fused post count/order/top-K | 0 | 1 |
| Total sequential statement cycles | 38 | 14 |

The final request hydrates the selected forum before its fused aggregate. All three post-warm requests at both 0ms and 2ms show the same operation sequence, with backend PID and SQL-log matching. `flight-summary.json` validates the actual sequential PostgreSQL Bind/Describe/Execute/Sync-to-Ready boundaries, separately from backend socket chunk counts.

Jac final uses a different transformation boundary: its compiler/runtime performs relational batching and reduces the selected request from 38 to 14 PostgreSQL statements, while WeBridge packages the Java business region inside a MySQL procedure. These are different database engines and access paths; the operation comparison identifies the transformations rather than attributing their latency differences to a single compiler effect. The matched Jac fixture and original/final statement receipts are under `jac-comparison/`; Java and WeBridge share the identical MySQL anchor fixture.

Recompute without live services:

```sh
python reproduction/webridge/roundtrip-comparison/audit_operation_map.py
```
