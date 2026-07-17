# Feature × Backend Support Matrix (feat/housekeeping, base bench/all-flags @ 9c40204b4)

Repo: `/home/aaron/Dev/Research/DatabaseResearch/JaseciFork`. Cells: **works / partial / missing / n/a** + one-phrase evidence.
File shorthand: `mongo.impl.jac` = `jac/jaclang/scale/memory/impl/memory_hierarchy.mongo.impl.jac` (same pattern for postgres / postgres_rel); `resolver.impl.jac`, `serializer.impl.jac`, `utils.jac` live under `jac/jaclang/runtimelib/`.
Cells updated by the 2026-07-16 housekeeping pass are marked **[HK]**.

| Optimization | mongo | postgres-KV | postgres-rel |
|---|---|---|---|
| **Projection pushdown** (JAC_PROJECTION) | **partial** - Route A (final-hop tail) only, native proj doc (mongo.impl.jac:~525-545); Route B needs `topology_sql` which mongo never advertises | **missing** - no `capabilities()`/`execute_plan` override at all; inherits empty set, resolver gate always fails. **[HK]** no-op now *asserted* (test_postgres_backend.jac: capabilities stay empty under JAC_PROJECTION, live read returns full anchors) | **works** - Routes A+B, narrow `data->'archetype'->%s` SELECT (postgres_rel.impl.jac:~85-135), capability env-gated. **[HK]** chain×projection composition now tested (sliced 2-hop chain drives rel_chain_count + rel_projection_count on one call) |
| **Projected-anchor API safety** | **works [HK]** | **n/a** (no projection path) | **works [HK]** - `_serialize_attrs` intersects emitted attrs with the anchor's `_projected_fields` marker via `__dict__.get` (serializer.impl.jac:17-28); slim anchors no longer leak class defaults into API payloads; lean×projection composition tested (test_lean_projection_compose.jac) |
| **Lean response** (JAC_API_LEAN_RESPONSE) | **works** | **works** | **works** - backend-agnostic; operates on built TransportResponse (jfast_api.impl.jac, server.impl.jac) |
| **UUID intern** | **works [HK]** - `deserialize_projected` now routes through lru-cached `_intern_uuid` at its single entry point (serializer.impl.jac:~790), closing the last uninterned path | **works** - no projection path, so no uninterned path (normal paths interned throughout serializer.impl.jac) | **works [HK]** - same `deserialize_projected` fix covers the pg-rel projected caller |
| **Order pushdown** (JAC_ORDER_PUSHDOWN) | **works [HK]** - Route-A final-hop tail: MongoBackend advertises `order_pushdown`, resolver sets `plan.order`, `cursor.sort()` before skip/limit (mongo.impl.jac:~546-555); mid-chain ordering stays structurally pg-rel-only (needs an edges table) | **n/a** - no QueryPlan integration to attach ordering to; resolver only sets `plan.order` when the backend advertises `order_pushdown`, so KV untouched | **works** - SQL `ORDER BY` on jsonb->>field text-sort inside its own hop+chain SQL (postgres_rel.impl.jac:~243/~380), not via plan.order; experiment flag, ISO-text-sort caveat. **[HK]** parser (`utils.order_pushdown_cfg`, shared by both backends) now fails loud on malformed input - bad arity/field/direction raise ValueError instead of silently defaulting to ASC |
| **Chain pushdown** (JAC_TOPOLOGY_SQL_CHAIN) | **n/a** - no join primitive to push into | **n/a** - no edges table exists on KV | **works** - one CTE per hop, single round-trip (postgres_rel.impl.jac:~253-350), default ON. **[HK]** composition with projection (Route B via `_materialize_ids_projected`) now tested |
| **batch_l3** (JAC_BATCH_L3) | **works** - single `$in` query (mongo.impl.jac:~854) | **works** - `WHERE id = ANY(%s)` one trip (postgres.impl.jac:~952) | **works** - inherits PostgresBackend.batch_get |
| **cross_root** (JAC_CROSS_ROOT_RESOLVE) | **works** | **works** | **works** - resolver-level, backend-agnostic (resolver.impl.jac:~39-102); on pg-rel bypassed when topology_sql answers the hop first |
| **read_only** (JAC_READ_ONLY) | **works** | **works** | **works** - backend-agnostic; CAVEAT: silently drops writes ("read_only is FAKE"). **[HK]** helper deduped to `utils.read_only_enabled` (was ×4 copies) |
| **Autocommit reads** (hardcoded, ex-5fbce338e) | **n/a** - pymongo has no implicit-txn-per-statement problem | **works [HK]** - the 5 unconditional sites (get/has/query/get_roots/batch_get) now route through one `PostgresBackend._read_conn` @contextmanager (memory_hierarchy.jac + postgres.impl.jac); behavior unchanged | **works [HK]** - 3 own sites (execute_plan, resolve_chain_sql, resolve_hop_sql) use the inherited `_read_conn`; still NOT flag-gated, cannot A/B |
| **GTI / topology_sql** | **partial** - GTI blob path works (anchor-level, backend-agnostic); `topology_sql` n/a | **partial** - GTI blob path works; `topology_sql` n/a (no edges table) | **works** - resolve_hop_sql/resolve_chain_sql via edges table; edges maintained in apply()'s txn, decoupled from JAC_TOPOLOGY_INDEX write hooks |
| **repair-memoize** (JAC_SCHEMA_REPAIR) | **works** | **works** | **works** - `_parse_repair_mode` @lru_cache intact (schema_rules.jac); untouched by lean/projection/housekeeping |
| **Floor fixes (ported) [HK]** | **works** | **works** | **works** - backend-agnostic: JAC_ACCESS_LOG toggle (env > toml `[server] access_log`, uvicorn.access dropped to WARNING when off), Redis down-probe 30s TTL (up AND down verdicts cached, redis.impl.jac), root_id process-level cache replacing per-request ContextVar (user_manager). Defect-4 `asyncio.to_thread(get_root_id)` hop deliberately NOT touched - new design work |

Structural note: **postgres-KV is not a peer** for query-plan pushdown - empty `capabilities()`, no `execute_plan`; every pushdown is missing by construction, not by bug (now asserted as an invariant, not just assumed). pg-rel never advertises `field_pushdown`/`slice` (mongo does); mongo now also advertises `order_pushdown` (pg-rel orders inside its own SQL instead).

## Flags Appendix (env var → default → toml mirror → documented in ENV.md?)

| Env var | Default | toml `[run]` mirror | Doc'd? |
|---|---|---|---|
| JAC_TOPOLOGY_INDEX | on (True) | yes (`topology_index`) | **yes [HK]** |
| JAC_ORDERED_TRAVERSAL | off | **yes [HK]** - loader wired (config.impl.jac:747, was dead) | **yes [HK]** |
| JAC_CROSS_ROOT_RESOLVE | off | yes | **yes [HK]** |
| JAC_BATCH_L3 | off | yes | **yes [HK]** |
| JAC_READ_ONLY | off | yes | **yes [HK]** (helper now shared: `utils.read_only_enabled`) |
| JAC_API_LEAN_RESPONSE | off | yes | **yes [HK]** (helper now shared: `utils.lean_response_enabled`) |
| JAC_PROJECTION | unset | **none** (env-only) | **yes [HK]** |
| JAC_ORDER_PUSHDOWN | unset (off) | **none** | **yes [HK]** (now mongo Route-A + pg-rel; fail-loud parser) |
| JAC_TOPOLOGY_SQL | on | **none** | yes |
| JAC_TOPOLOGY_SQL_CHAIN | on | **none** (pure env, unlike siblings) | **yes [HK]** |
| JAC_ACCESS_LOG | on (truthy) | `[server] access_log` (env wins) | **yes [HK]** (new this pass) |
| JAC_SCALE_BACKEND | auto | `[scale.database].backend` | yes |
| JAC_READ_AUTOCOMMIT | on (True) | none (env-only) | **yes [HK]** (A/B ablation flag over `_read_conn`; covers postgres + postgres-rel) |
| JAC_LAZY_HYDRATION | off | none (env-only) | **yes** (floor-path `_materialize_ids` stub deferral; **GTI-inert by design** - mid-chain nodes are bare UUIDs on the fast path, so only the walk fallback engages) |
| JAC_MEM_POOL | off | none (env-only) | **yes** (per-worker `ScaleTieredMemory` free-list; checkout/release scrub L1 + changes = isolation invariant) |

# Gaps

## Resolved by the housekeeping pass (2026-07-16)

1. ~~HIGH - Projected/slim anchors leak default-valued fields into API responses~~ - fixed (ed2b4dc41 + e53189aed: marker read via `__dict__.get` to avoid `Anchor.__getattr__` → `populate()` recursion); lean×projection now tested (5434f362f).
2. ~~MEDIUM - Floor-fix defects 2 & 3 unported~~ - ported (1111c349a): access-log toggle, Redis probe TTL, root_id process cache. Defect 4's `to_thread` hop intentionally out of scope (see remaining #3).
3. ~~MEDIUM - Doc/code drift~~ - ENV.md retitled for bench/all-flags, ~11 flags documented, dead worktree pointer removed, PORT_NOTES_REL.md test-count addendum (438c73679).
4. ~~MEDIUM - `ordered_traversal` toml key dead~~ - wired + tested (c7773bb6e).
5. ~~MEDIUM - Chain pushdown × projection untested~~ - sliced 2-hop chain test asserting rel_chain_count + rel_projection_count on one call (5434f362f).
6. ~~LOW - Mongo order pushdown missing~~ - built, Route-A tail, capability-gated (c0bbd1c3c).
7. ~~LOW - JAC_ORDER_PUSHDOWN parser silently defaults to ASC~~ - fail-loud ValueError + malformed-input tests (1407ede87).
8. ~~LOW - `deserialize_projected` skips `_intern_uuid`~~ - fixed at single entry point (62036e32d).
9. ~~LOW - Helper duplication~~ - env-flag helpers deduped into utils.jac (a2d9eb533); pg autocommit ritual factored into `_read_conn` (51a8fc8b2).
10. ~~LOW - KV projection no-op unasserted~~ - asserted invariant (5434f362f).
11. ~~LOW - Hygiene debris in main checkout~~ - `.tools/` (444MB), CROSSROOT_NOTES.md, PR6565.diff purged; `.gitignore` updated but **uncommitted** in the main checkout (can't commit to bench/all-flags directly - fold into the next merge).

## Remaining

1. ~~**MEDIUM - `asyncio.to_thread(get_root_id)` hop still present**~~ (floor-fix defect 4) - **resolved** (branch feat/lazy-hydration): `JacScaleUserManager.aget_root_id` now serves process-cache hits inline on the event loop and only routes cache misses (which block on Mongo/PG in `_identity_storage`) through `to_thread`. Semantics-preserving (the base wrapper's `get_root_id` already checked the cache first), so it ships unflagged per floor-fix precedent.
2. **MEDIUM - pg read autocommit cannot be A/B'd.** Now one `_read_conn` choke point, so adding a flag is a one-line change if the ablation is ever wanted.
3. **LOW - `?._projected_fields` attribute-access pattern** survives at memory.impl.jac:~1797/~1988. Both sites are guarded (populated / fresh-from-execute_plan anchors), but the pattern routes through `Anchor.__getattr__` for marker-less anchors; if a future call site sees an unpopulated anchor it can recurse like the T5 bug did. Prefer `__dict__.get('_projected_fields')` for new sites.
4. **LOW - Order pushdown is text-sort** (jsonb->>field / mongo string field): safe only for lexicographically-sortable values (ISO-8601 timestamps), not numeric. Both backends share the caveat; documented in ENV.md.
5. **LOW - mongo mid-chain ordering structurally out of reach** (no edges table); pg-rel-only by construction, same class as chain pushdown.
6. **LOW - pg-rel never advertises `field_pushdown`/`slice`** (mongo does) - Route-A predicate/slice work on pg-rel goes through its own SQL paths instead; asymmetry is deliberate but undocumented in code comments.
7. **NOTE - rel e2e still gated** (server boot required; PORT_NOTES_REL.md "Pending"): `jac start` boot, GTI off, cold restart, littleX rel_ parity, sanity bench.
8. **NOTE (no action, decision item)** - merged stale branches (feat/cross-root-batch, feat/postgres-l3-r2, feat/read-only-ablation, fix/pg-l3-read-trips, fp-new-main) are delete candidates but destructive - user decision. littleXs/jaseci-rel divergence in DBHarness is deliberate experiment code (read-only repo, report only).
9. **NOTE - pre-existing test frictions** (identical on pristine bench/all-flags, not introduced here): test_schema_repair_mongo fails 2 tests when batched after the projection/mongo suites (passes 4/4 alone); test_postgres_rel_selection fails 1 test when batched after test_postgres_rel_backend (passes 5/5 alone); test_serve has a known HMR failure. All are shared-DB/batch-order artifacts under JAC_TEST_JOBS=0.

# Changelog - housekeeping pass 2026-07-16 (branch feat/housekeeping)

| Commit | Task | Summary |
|---|---|---|
| 438c73679 | T2 | docs(env): retitle ENV.md for bench/all-flags, document undocumented flags |
| c7773bb6e | T3 | fix(config): wire ordered_traversal toml key into RunConfig loader |
| 1111c349a | T4 | perf(scale): port old-base floor fixes - access-log toggle, redis probe TTL, root_id process cache |
| ed2b4dc41 | T5 | fix(serializer): guard projected anchors from leaking class defaults |
| c0bbd1c3c | T6 | feat(scale): mongo Route-A order pushdown via JAC_ORDER_PUSHDOWN |
| a2d9eb533 | T7 | fix(runtimelib): dedupe env-flag helpers into utils.jac |
| 51a8fc8b2 | T8 | refactor(scale): factor pg read-connection autocommit ritual into _read_conn |
| 1407ede87 | T9 | fix(runtimelib): fail loud on malformed JAC_ORDER_PUSHDOWN |
| 62036e32d | T10 | fix(serializer): intern UUIDs on deserialize_projected path |
| 5434f362f | T11 | test(scale): cover lean × projection, chain × projection, KV projection no-op |
| e53189aed | follow-up | fix(serializer): read _projected_fields via `__dict__`, not `__getattr__` (RecursionError in schema-repair round-trips introduced by T5) |

T1 (hygiene purge of the main checkout) has no commit - untracked-file deletion plus an uncommitted `.gitignore` edit in the main checkout.
