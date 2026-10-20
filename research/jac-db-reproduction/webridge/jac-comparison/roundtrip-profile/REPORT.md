# Jac: measured protocol flights and operation-to-SQL map

All twelve post-warmup requests certify **38 serialized query/response flights for original Jac and14 for final Jac**. This comes from actual protocol frames, backend ReadyForQuery boundaries and timestamp ordering, independently matched to every executed PostgreSQL statement.

The instrumented run records three requests per variant at0ms and2ms configured response delay, after ten warmup requests. It is separate from quiet latency timing. Every result matches the same nonempty IC5 oracle.

## What was measured

| Warm request, every replicate at both delays | Original | Final |
|---|---:|---:|
| SQL executions matched to backend log |38|14|
| Certified sequential command/response flights |38|14|
| Frontend protocol messages |152|56|
| Backend protocol messages |222|83|
| Frontend TCP read chunks |38|14|
| Backend TCP read chunks |39|14|
| DataRow messages |70|27|

Every frontend group is exactly `Bind → Describe(portal) → Execute → Sync`. It is followed by the corresponding backend reply ending in `ReadyForQuery`. The next Bind reaches the proxy only after the preceding ReadyForQuery's final chunk was delivered. There are no post-warmup Parse or Flush messages: each query uses a named prepared statement already established during warmup.

The baseline's39backend chunks carry38responses because one object-hydration reply spans chunks. Packet/chunk count, protocol message count, SQL execution count and synchronization-flight count are therefore separate measurements.

`results/certified-flights.json` lists all three replicates at each delay. `results/flight-summary.json` retains each flight's forwarded frontend timestamp, delivered Ready timestamp, backend PID, SQL stable ID, statement name and ordering proof. Its query-response span includes SQL execution and instrumentation as well as response delay. The separate quiet sweep's SELECT1 RTT calibrations remain in `../latency/results/`; they measure the transport independently of these IC5 query spans.

## Which operations are combined

| Logical operation on this input | Original SQL executions | Final SQL executions |
|---|---:|---:|
| Begin / lock setting / commit |3|3|
| Root and input-person hydration |2|2|
| Outbound / inbound Knows |2|2|
| Hydrate outbound7 / inbound3 friends |2|2|
| Per-friend HasMember traversal |10|1batch over all10friends|
| HasMember / Forum ancestry probes |0standalone|2standalone|
| Hydrate the one candidate forum |1|1|
| ContainerOf traversal |1|Included in count aggregation|
| Hydrate15posts |1batch|Removed from this execution|
| HasCreator traversal |15|Included in count aggregation|
| Hydrate newly seen creator |1|Removed from this execution|
| Grouped count, ordering, top20 |Application loop/sort|1SQL statement|
| **Total** |**38**|**14**|

The unchanged portion has ten SQL executions: transaction control, root/person/friend/forum hydration and the two Knows traversals. Membership changes from ten queries to one batched query plus two type probes, a net reduction of seven. The counting portion changes from eighteen queries—ContainerOf, fifteen HasCreator traversals and two object-load batches—to one grouped count/order/topK query, a reduction of seventeen. Together these account exactly for38→14.

The current final trace retains the two ancestry queries and the five hydration queries separately. The one forum is hydrated before the aggregate in this observed execution. The map describes this one-forum diagnostic's actual sequence.

`results/operation-map.json` contains the complete ordered38/14operation sequences, grouped changes and source anchors. `results/sql-catalog.json` and `results/sql/*.sql` preserve every exact SQL shape under stable content-based IDs. SQL IDs can repeat across graph operations because edge/type arguments differ; sanitized Bind metadata preserves those logical edge/type values and UUID-array cardinalities.

## Actual final sequence

1. Begin read-only repeatable-read transaction.
2. Set local lock timeout.
3. Load root anchor.
4. Load input person.
5. Traverse outbound Knows.
6. Load its seven friend anchors in one batch.
7. Traverse inbound Knows.
8. Load its three friend anchors in one batch.
9. Query HasMember subtype names.
10. Query Forum subtype names.
11. Fetch HasMember pairs for all ten friends in one frontier query.
12. Load the candidate forum anchor.
13. Aggregate qualifying creators/posts per forum, order and limit.
14. Commit.

The aggregate constructs qualifying forum/member pairs, follows HasCreator and ContainerOf relations inside SQL, groups counts, joins the forum mirror for ordering, and applies LIMIT. WeBridge's full/pruned CALL comparisons preserve their individual business-query sequence inside the procedure; their client-side exchange reduction is a distinct operation from this Jac SQL transformation. The root operation matrix records that comparison.

## Source anchors

The unchanged walker is `reproduction/benchmark/snb/jaseci-pg/app.jac:368`. Final prefetch lowering is in `jac-db/jac/jaclang/jac0core/passes/impl/pyast_gen_pass.impl.jac:3330`; runtime frontier fill is in `query_planner.impl.jac:1645`.

The two type probes originate from `_fast_adj_sql`'s loop over edge and target type names (`query_planner.impl.jac:1588`). `PgStore.subtype_names` emits `SELECT type_name FROM graph_types WHERE ancestor = :t` (`store.impl.jac:2771`). Both exact queries appear in every warm final request.

`Session.batch_get` (`session.impl.jac:453`) calls `PgStore.load_full` (`store.impl.jac:847`), matching the retained anchor-hydration SQL. The count/topK SQL builder is in `jac0core/impl/runtime.impl.jac:1284`. Full paths and line anchors are also stored in `source-anchors.json` and the compact operation map.

## Reanalysis and privacy

Run `python analyze.py` from this directory. It reads frame metadata, sanitized Bind metadata, request rows and actual server SQL logs. Every prepared-statement SQL shape is matched to the server log, including multiline statements, and backend PID agreement is verified.

`PUBLIC_FILES.json` lists the archive-safe inputs. `events.jsonl.gz` contains message types, sizes, timestamps and Parse SQL; Bind/DataRow values are omitted. UUID arrays in public Bind metadata are reduced to cardinalities. Public reanalysis succeeds with raw binary captures, private-named files and uncompressed event logs excluded; receipt: `results/public-reanalysis-test.json`.

Raw request-only database frame payloads remain local with mode0600. They contain no HTTP Authorization headers; the retained payload scan finds zero JWT-pattern matches. The proxy parses backend key frames only to retain the backend PID, omitting the cancellation secret. Both trace proxies and application services stopped and scoped PostgreSQL logging was restored, as recorded in the per-run receipts.
