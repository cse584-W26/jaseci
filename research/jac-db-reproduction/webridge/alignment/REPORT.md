# Jac baseline → Java/WeBridge alignment

The functional Java port reproduces all 20 IC5 results and each input's original SQL count. MySQL independently observes the same query count as the JDBC application counter. The category ledger also matches every node-load, directional traversal, transaction, and initialization category.

## Measured gate

`alignment-gate.json`, `query-category-ledger.json`, and `java-all20-context-aligned.jsonl` retain the final results. `verification.json` records the offline verifier outcome. The complete cold pass contains 278,773 statements. Its four additional statements are the first identity lookup and three cold schema initialization queries. The corresponding warm original baseline contains 278,769 statements. A final repeat of input 0 returns the same empty result with 24 statements on both systems.

| Input | Jac cold pass | Java cold pass | MySQL independent | Jac original warm |
|---|---:|---:|---:|---:|
| 0 | 28 | 28 | 28 | 24 |
| 1 | 3938 | 3938 | 3938 | 3938 |
| 2 | 37302 | 37302 | 37302 | 37302 |
| 3 | 5188 | 5188 | 5188 | 5188 |
| 4 | 11465 | 11465 | 11465 | 11465 |
| 5 | 49 | 49 | 49 | 49 |
| 6 | 14243 | 14243 | 14243 | 14243 |
| 7 | 38225 | 38225 | 38225 | 38225 |
| 8 | 6202 | 6202 | 6202 | 6202 |
| 9 | 16986 | 16986 | 16986 | 16986 |
| 10 | 34 | 34 | 34 | 34 |
| 11 | 7448 | 7448 | 7448 | 7448 |
| 12 | 15948 | 15948 | 15948 | 15948 |
| 13 | 18379 | 18379 | 18379 | 18379 |
| 14 | 18014 | 18014 | 18014 | 18014 |
| 15 | 20370 | 20370 | 20370 | 20370 |
| 16 | 11048 | 11048 | 11048 | 11048 |
| 17 | 8448 | 8448 | 8448 | 8448 |
| 18 | 33 | 33 | 33 | 33 |
| 19 | 45425 | 45425 | 45425 | 45425 |

The Jac capture runs two complete 20-input passes. Each request has its original compressed PostgreSQL protocol log and result oracle. The comparison isolates walker backend PID 2126112, plus the first request's actual identity lookup on PID 2126064. All 20 warmed walker counts equal the historical census, and all 19 non-initial inputs have identical walker counts across the two fresh passes.

The SQL logger initially also captured our concurrent export/inspection connections. Their statements include `CREATE TEMP TABLE align_inputs`, `COPY`, and fixture metadata queries. `baseline-capture/other-backend-statements.json` identifies these exact statements and PIDs. `backend-filtered-counts.json` preserves both raw counts and the request backend counts. These captures establish behavior and query counts; their wall times include concurrent setup activity.

MySQL's independent count is the same connection's `Questions` delta, subtracting the one trailing observer `SHOW SESSION STATUS` statement. Actual server query logging exposed an additional JDBC-generated `select @@session.transaction_read_only` before COMMIT. `useLocalSessionState=true` makes the driver use its session state and removes that extra driver query. The retained `mysql-query-diagnostic.tsv` shows the complete evidence. The final independent counter equals the application's executed-query counter for all 21 validated requests.

## Identity and context memoization

`identity_probe.py` wraps the existing runtime methods in memory. `run_identity_probe.py` starts that diagnostic launcher, sends three actual input-0 requests, and restores the standard baseline service. Its retained `identity-trace.jsonl` proves this sequence:

1. `jwt_validation_middleware` invokes `JacScaleUserManager.get_root_id` on the main thread.
2. The first lookup reads `identity_users` and populates `_root_id_request_cache`.
3. Walker `asyncio.to_thread` execution inherits the populated context.
4. Subsequent requests on that keepalive connection reuse the context map. The optional `_root_memo_enabled` flag remains false.

The Java `clientRootContext` implements this observed client-context lifetime. It resolves a real identity document, validates the identity/root, and retains that root for subsequent requests in the same client context. The request-local anchor cache remains separate and starts fresh on every request.

Source references are `runtime/baseline-source/jac/jaclang/scale/identity/impl/user_manager.impl.jac` (`get_root_id`, lines 117–146), its `_root_id_request_cache` declaration in `identity/user_manager.jac`, and the JWT middleware caller retained by the trace. `runtimelib/impl/server.impl.jac` (`_abegin_user_request_context`, line 323) supplies the worker request context.

## Functional port

`AlignedIc5.java` retains:

- Original UUID node/edge identity, edge sequence, full anchor properties, owner roots and permission maps.
- Separate outbound and inbound Knows traversals, membership-edge date predicates, per-forum post traversal, and a separate creator traversal for every post.
- Request-local `batch_get` hydration and object identity caching; owner-root prefetch and the source's owner/default/per-root ACL precedence.
- Source type-inheritance predicates via `graph_types`, node-type checks, traversal ordering, and per-hop node deduplication.
- A read-only transaction, lock-wait setting, commit/rollback, and cold schema/type initialization.
- The original joined-friend sets, per-post membership test, forum sorting, and top 20.

The source app's Person, Forum, and Post classes use the standard access hook. This port specializes the generic runtime to those actual IC5 classes and this declared read workload. Its entry boundary accepts the same service identity context already validated by the Jac request; the Java CLI begins at identity/root resolution. Request HTTP parsing and token cryptography sit outside that CLI boundary.

MySQL syntax translates the PostgreSQL UUID array/unnest origin to a scalar UUID origin and uses two UNION branches for the directed-or-undirected edge predicate. One graph hop remains one SQL statement. Each branch retains endpoint/type filtering and final edge sequence ordering. MySQL's session default is repeatable read; `START TRANSACTION READ ONLY` and the lock-wait setting preserve the source's snapshot/timeout intent on the dedicated client connection.

## Fixture and reproducibility

`export_graph.py` creates only connection-local PostgreSQL temporary tables. It exports the exact union of queried edge relations for these 20 declared inputs, their endpoint anchors, and transitive owner roots. The fixture contains:

- `align_friends`: 284
- `align_forums`: 12,894
- `align_posts`: 142,801
- `align_edges`: 300,901
- `align_ids`: 460,984

Original UUIDs, full properties, row versions, edge sequences, type registry, identity document, and schema fingerprint are retained. `graph-fixture/manifest.json` includes the export SQL, timings, sizes and SHA-256 checksums. The dedicated MySQL database is `jac_alignment` on container `jac-webridge-mysql57`, port 55337; `schema.sql`, `load_mysql.sh`, and `mysql-load.log` retain its setup.

Executed commands are preserved by their source scripts and result artifacts:

```bash
runtime/venv314/bin/python webridge/alignment/capture_baseline.py --out webridge/alignment/baseline-capture --rounds 2
runtime/venv314/bin/python webridge/alignment/export_graph.py --out webridge/alignment/graph-fixture
webridge/alignment/load_mysql.sh
# Preliminary complete trial retained identity lookup on every call:
taskset -c 16-17 webridge/alignment/run.sh 0 19 1
# Final context-aligned trial:
taskset -c 16-17 webridge/boot-jdk8/bin/java \
  -Dalignment.dir=/home/baichuan/jaseci/reproduction/webridge/alignment \
  -Dalignment.finalRepeatFirst=true \
  -cp 'webridge/alignment/classes:webridge/deps/*' AlignedIc5 0 19 1
# Offline verification uses the later, designated offline CPU pair:
taskset -c 9,19 python webridge/alignment/compare_categories.py
taskset -c 9,19 python webridge/alignment/verify_alignment.py
```

Commands above are relative to `reproduction/`. `identity-probe-driver.log` and `identity-probe-launch.json` retain the three-request diagnostic. Database-scoped PostgreSQL logging settings were restored in `capture_baseline.py`'s `finally` block; `baseline-capture/database-settings-before.json` and `restored.json` record that lifecycle. The baseline HTTP service was stopped after validation. Temporary MySQL general logging was disabled after the JDBC query diagnostic.

## Stage 2: separate overhead-removal derivative

`PrunedIc5.java` derives directly from the validated full port. `prepare_pruned.py`, `pruned-vs-full.diff`, and `removal-ledger.json` identify every change and its base source hash. Flags independently remove identity resolution, ACL checks/root initialization and prefetch, schema lifecycle, and full-anchor hydration. Hydration removal requires ACL removal because the original ACL path reads object permissions.

Hydration removal projects only Forum forum_id/title scalar fields inside the existing Forum traversal, and uses lightweight UUID/type records for friends, posts and creators. The title is read with typed JDBC getString. The initial generic getObject decoder returned binary-collation bytes, causing an observed input1 title mismatch; its failed source and exact diff remain under `ablations/20261020T185554Z/no_auth_acl_schema_hydration/diagnosis.json`. The corrected source retains the same SQL and parameters.

The corrected all-removal configuration passed all20 result oracles plus a warm repeat of input0. Independently observed MySQL Questions equals the executed JDBC count on every request. Each input also retains the full port's exact counts for every directional Knows/HasMember/ContainerOf/HasCreator hop. Receipt: `ablations/20261020T190438Z/no_auth_acl_schema_hydration/gate.json`.

| Measured query category, 20 inputs | Full port | All four removals |
|---|---:|---:|
| Domain traversal statements |247870|247870|
| BEGIN / setting / COMMIT |60|60|
| Full-anchor hydration queries |30839|0|
| Cold identity/schema initialization |4|0|
| Total |278773|247930|
| Warm repeat of input0 |24|20|

The algorithm retains its friend/forum/post/creator loops, joined-friend sets, ordering and top20. The count reduction removes the recorded object/lifecycle queries. The derivative continues to execute one query for every original domain hop, including every per-post creator lookup. The entire original hop SQL still uses generic anchors and type-inheritance predicates, with only the required Forum scalars added to its projection.

All five cumulative configurations completed 21 requests each in `ablations/20261020T190438Z/`. `exact-removal-verification.json` verifies per-input category deltas and result oracles across all105 requests.

| Cumulative configuration | Cold20 statements | Warm repeat0 |
|---|---:|---:|
| Full port |278773|24|
| Remove identity resolution |278772|24|
| Also remove ACL/root prefetch |278752|23|
| Also remove schema lifecycle |278749|23|
| Also remove hydration |247930|20|

The successive reductions are one cold identity query,20 owner-root loads, three cold schema checks, and30819 remaining object loads. Gate timings are single diagnostic passes with interleaved compiler CPU on9,19. Earlier interrupted prefixes are marked `coordination-aborted`, with incomplete cold20/repeat fields left null.

The integration typed/region adapters read the projected BIGINT Forum identifier using `getLong` plus `wasNull`, matching the original WeBridge recorded ResultSet API. Other projected fields use `getString`. The final region adapter passed another21-request result/category/server-count gate: `../integration/cases/pruned-region-getlong-gate-20261020/gate-20261020T191708057203Z/verification.json`. The adapter diff and build receipt are in `../integration/pruned-getter-fix/`.

## Source hashes

- `AlignedIc5.java`: `acc9b168a3fb579829f2c52c8a07b7be3361a9be9d983bfd9bec0412003246a2`
- `PrunedIc5.java`: `32d67d833ed0624809316029af67586cd50f1b0f55bdc7446bb560fac0c2a3e7`
- `capture_baseline.py`: `72da7a1930fa6b0a43b44cc2ba68e9c6f01d809a53ae9edf3383169ccdfb1763`
- `export_graph.py`: `f622eec79413149e53710b18f96a2e17b2af7651f79af1a24c4addcb7642b584`
- `compare_categories.py`: `2c3d7824f4ff92d3713547fd15fd75813aa6093aa389db7a2a67a19f814499aa`
- `verify_alignment.py`: `b94d84fecb48e75804641e51df18d7431a171232901097cebcaba8b325dbe89f`
