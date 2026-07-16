# Projection Pushdown (Mongo + PG-rel) + UUID-Intern Rider -- Final Spec

Date: 2026-07-13 (revised post-scout). Status: FINAL, awaiting user review.
Supersedes the draft of the same name. Companion:
`2026-07-13-pg-rel-backend-design.md`. All file:line refs = worktree
`JaseciFork-pgrel` @ `feat/pg-rel-mvp` (e979b5083).

## Problem

Post pg-rel, feed p50 ~113-120ms; remaining bill is hydration: ~2,550 full
anchors deserialized per request (serializer ~25% + hydration ~17% of active
samples) to build views that read a subset of anchor machinery. Projection
pushdown = fetch only needed archetype fields, skip per-anchor fixed costs.
Bundled with the already-built ORDER+slice hop path it becomes "hydrate one
page" (40 anchors, not 2,550) -- the 113 -> 40-70 lever. Covers BOTH engines:
upgrades the claim from "PG trick" to "runtime query planning generalizes".

## Measured composition evidence (why bundle, never alone)

- order-alone: **-4ms LOSS** (JSONB text-sort in PG > Timsort-on-2550).
- chain-alone: p50 wash at depth 2.
- projection-alone: est. +10-25ms (fixed-cost skips only; feed's TweetView
  reads ALL 6 Tweet fields, so field-narrowing ~ 0 on this workload).
- projection + ordered-slice (`feed_page`): the real figure -- hydrate 40.

## Decision 1 -- Integration point: `QueryPlan.projection` (P1, unchanged)

Add to `QueryPlan` (`runtimelib/query_plan.jac:15-27`):
`projection: (set[str] | None) = None`. `needs()`
(`impl/query_plan.impl.jac:11-27`) contributes `'projection'` when set, so
the existing subset test `plan.needs() <= mem.capabilities()`
(`resolver.impl.jac:453`) gates it with zero new negotiation machinery.

Rejected (unchanged from draft): projecting inside `resolve_hop_sql` (wrong
layer, returns ids); view-dict short-circuit (P3, language feature).

## Decision 2 -- What comes back: slim anchors, LOUD on unprojected access

`Serializer.deserialize_projected(...)` builds a real `NodeAnchor` via
`__new__`: sets `id`, `persistent=True`, `edges=[]`, `hash=0`, `version=0`,
`access=Permission()` (both READ on the refs()/access paths --
`note_traversal_reads` reads `.version`, `_check_access` reads `.access`;
verified), resolves the archetype class, `object.__new__` the archetype,
setattr ONLY projected fields with values routed through
`Serializer._deserialize_value` (raw setattr would leave `$ref`/typed
values as dicts -- silent corruption), links `archetype.__jac__ = anchor`,
stamps `anchor._projected_fields: set[str]`.

Skipped per-anchor fixed costs (measured hydration bill,
`serializer.impl.jac:556-637` + mongo `_load_anchor:871-934`):
access-map parse (:565), edges stubs + `_initial_edge_ids` (:586-604),
`_compute_hash` full re-serialize (:629-631), `_mongo_persist_repairs`
(:931), `snapshot_field_hashes` (:932).

**Hazard model (corrected in review):** unprojected fields are never set.
For factory-default fields (`list`/`dict`) access raises `AttributeError`
-- loud. For scalar-default `has` fields the jac dataclass CLASS attribute
answers instead -- SILENT default read (verified empirically:
`object.__new__` instances resolve `has b: int = 0` to `0`). So the
draft's silent-wrong-value hazard survives for scalars; mitigation is
declaration completeness (declare every field the walker reads) until S2
compiler verification. Documented, not solvable at this layer.

**Traversal-terminal contract:** projected anchors have `edges=[]`. On
pg-rel, hops resolve via the edges TABLE by source id, so traversal FROM a
projected node still works; on Mongo (blob/GTI hops) it would silently
return []. MVP contract: declare projections only for traversal-terminal
types (Tweet in feed). Ledgered, not enforced, until walker effect inference
(S2) can prove it.

## Decision 3 -- Safety: explicit declaration + read-only gate (S-MVP)

Both required, unchanged from draft:

1. **Declaration** -- RESOLVED open question 1: env-only for MVP,
   `JAC_PROJECTION="Tweet:content,created_at,author_username,likes,comments,seed_id"`
   (`;`-separated for multiple types). Mirrors `JAC_ORDER_PUSHDOWN` parser
   (`memory_hierarchy.postgres_rel.impl.jac:58-77`), ~15 lines, zero toml
   plumbing. toml surface arrives with compiler inference (S2), not before.
   No declaration -> no projection -> byte-identical behavior.
2. **Read-only gate**: projection attaches only when `_read_only_enabled()`
   (`memory.impl.jac:2015-2027`) -- commit never runs
   (`_collect_into:1788-1790` already returns early), so write-back
   corruption is structurally impossible.
3. **Belt + suspenders**: `_collect_into`'s anchor loop (:1792-1793)
   additionally skips any anchor with `_projected_fields` -- protects
   mixed/misconfigured runs.
4. **L1/L2 rule** -- RESOLVED open question 2: projected anchors NEVER enter
   L1 or L2. Skip points are exact: `TieredMemory.execute_plan`
   `memory.impl.jac:1986` (L1 insert), `:1988/:1996` (L2 batch_put).
   (`batch_get` :2045/:2054/:2062 never sees projected anchors -- floor path
   only.) Cost: repeat access within one request; feed touches each tweet
   once.

RESOLVED open question 3 (S2 scope, recorded for
walker-effect-inference-plan, not MVP work): method bodies on node types
(`to_view`) ARE in scope for inference when statically resolvable;
un-analyzable call -> no tag -> full hydration.

## Decision 4 -- Composition routes (NEW; corrects the draft)

Scout finding: the ordered/sliced path returns a **list** at
`resolver.impl.jac:441` and bypasses the QueryPlan tail entirely -- the
draft's "ORDER BY/LIMIT rides execute_plan" would never fire. Corrected
design puts ORDER+slice where it already works (hop/chain SQL,
`postgres_rel.impl.jac:335-371/:228-270`) and projection at
materialization:

- **Route A (set path, plain `feed`)**: final-hop tail already builds
  QueryPlan (`resolver.impl.jac:445-453`). Attach
  `plan.projection = cfg[node_type_final]` when declaration exists AND
  read-only AND `'projection' in mem.capabilities()` (the caps pre-check
  avoids regressing backends that would otherwise pass the subset test)
  AND the final hop has NO post_filter -- `_try_pushdown` runs post
  filters against the archetype, and a slim archetype would answer
  scalar predicates with class defaults (silently wrong filter results).
  `_try_pushdown` -> `execute_plan` -> 2,550 slim anchors. This is the
  projection-alone increment, measurable on BOTH engines.
- **Route B (list path, `feed_page`)**: hop/chain SQL returns ordered+sliced
  ids (already built). New branch at `:441`: when projection is licensed
  (same three conditions), call `_materialize_ids_projected(mem, ids,
  node_type)` -- builds `QueryPlan(id_in=set(ids), node_type_final=...,
  projection=...)`, runs `_try_pushdown`, reorders results to the input id
  order in Python (20-40 items, trivial). No ORDER BY/LIMIT inside
  execute_plan at all -- ids arrive pre-sliced. Route B additionally
  requires `'topology_sql' in caps`: on pg-rel the ordered ids come from
  SQL without hydration, but Mongo's ordered walk hydrates candidates to
  sort them, so a projected re-fetch there would be a net loss -- Mongo
  keeps its existing list path.

## Decision 5 -- Capability gating (NEW)

- **PG-rel**: gains `execute_plan` for the first time. Caps become
  `{'topology_sql'} | ({'id_in','type_pushdown','projection'} if projection
  declared else {})` -- WITHOUT the flag, caps stay `{'topology_sql'}` and
  every existing path is byte-identical (feed currently always takes the
  `_materialize_ids` floor; that must not change un-flagged).
  **Fallback rule (review finding):** once caps are on, plans for
  UNDECLARED types (projection None -- e.g. the Profile hop) also pass the
  subset test and route here; `execute_plan` must full-hydrate them
  (`batch_get(plan.id_in)` + arch_type filter), never return empty.
  Deliberately
  NOT advertising `'slice'` (the `_try_pushdown` guard
  `resolver.impl.jac:147-149` reapplies slices in Python) or
  `'field_pushdown'` (blob-only, ledgered).
- **Mongo**: already advertises `{'type_pushdown','field_pushdown','id_in',
  'slice'}` (`mongo.impl.jac:486-488`) and `_try_pushdown` already fires on
  plain feed. Add `'projection'` unconditionally -- inert unless a plan
  carries a projection, which requires the env declaration.

## Engine specifics

**PG-rel `execute_plan(plan)`** (new, `postgres_rel.impl.jac`):

```sql
SELECT id, arch_module, arch_type,
       data->'archetype'->'content', data->'archetype'->'created_at', ...
FROM anchors WHERE id = ANY(%s) [AND arch_type = %s]
```

`->` (not `->>`) preserves JSON types (lists/dicts come back as Python
objects via psycopg jsonb). `id` stays TEXT (KV inheritance). Rows feed
`deserialize_projected`. Only `id_in` + `node_type_final` + `projection`
handled; anything else in `needs()` fails the subset test upstream.

**Mongo `execute_plan`** (extend `mongo.impl.jac:525-546`): when
`plan.projection` set, pass a projection doc to the existing
`self.collection.find(filt, projection_doc)` (:531):
`{'type':1,'arch_type':1,'arch_module':1,'data.id':1,'data.__type__':1,
'data.__module__':1,'data.archetype.__type__':1,'data.archetype.__module__':1}`

- `{'data.archetype.<f>':1}` per field. Precedent: edge-refresh reads
already project (:746/:758). Projected docs route to
`deserialize_projected` instead of `_load_anchor`.

## UUID-intern rider (flagless, after projection)

Re-port the serializer half of orphan `feat/perf-l1-uuid` commit
`de012d6a3` (the `pushdown_skip` half of that commit is NOT re-ported --
superseded by this design's L1 rule):

- `@lru_cache(maxsize=65536)` on `def _intern_uuid(id_str) -> UUID` in
  `runtimelib/serializer.jac` -- body INLINE IN THE DECL (Jac impl-splitting
  drops decorators; known trap).
- Replace the 6 bare `UUID(` sites in `serializer.impl.jac` (verified
  present, 2026-07-13): `_deserialize_jac_ref`, `coerce`, `_get_class` stub,
  `_deserialize_anchor` id/root/edge-frozenset.
- Flagless (pure value-equality perf change; precedent repair-memoize/
  typecache). `to_uuid` (`runtimelib/utils.jac:31-36`) and its Mongo/Redis
  hot sites stay untouched -- matches the old impl's scope.
- A/B AFTER projection lands (projection shrinks its residual value); drop
  if within noise.

## `feed_page` workload (decision: build it; it is the headline figure)

- Harness: register `feed_page` in `WORKLOADS` (`harness/run.py:97-101`) +
  `fetch_feed_page`; oracle gets a `feed_page` parity case.
- Baselines (USER implements; paste-ready blocks provided in plan):
  `ORDER BY created_at DESC LIMIT 20` in `littleXs/postgres/app.py`
  (FEED_SQL :228-235), `sqlalchemy/app.py` (`.limit(20)` ~:270),
  `neo4j/app.py` (Cypher `LIMIT 20` ~:196), each behind a new
  `/feed_page` endpoint (existing `/feed` untouched).
- Jac (`littleXs/jaseci-rel/app.jac`, editable copy): new
  `walker load_feed_page` -- both visit streams sliced
  (`visit [...][:20]` with `JAC_ORDER_PUSHDOWN=Tweet:created_at:desc`),
  deliver merges <=40 candidates, sorts desc, takes 20.
- **Parity is EXACT**: each stream's contribution to the global top-20 is
  contained in that stream's top-20, so merge-of-per-stream-top-20 = global
  top-20. (This also retires the two-visit-stream caveat that invalidated
  the skip-sort probe.)
- Jac config for the run: `JAC_PROJECTION=Tweet:... JAC_ORDER_PUSHDOWN=
  Tweet:created_at:desc JAC_READ_ONLY=1` + standard pg-rel flags
  (`BATCH_L3=1, GTI=0, CHAIN=0`). Note: expression index on
  `(data->'archetype'->>'created_at')` becomes worthwhile once LIMIT exists;
  optional follow-up, measure without it first.

## Sizing (honest, UNVERIFIED until benched)

Route A alone: +10-25ms est (fixed-cost skips across 2,550 anchors).
Route B (`feed_page`): hydrate 40 not 2,550 -- the 113 -> 40-70 band. Note
`feed_page` changes the response contract; it is a NEW workload reported
alongside `feed`, never a replacement.

## Testing plan

- Unit: JAC_PROJECTION parser; `deserialize_projected` (projected fields
  set, unprojected access raises AttributeError, `__jac__` link, marker).
- Backend: PG-rel execute_plan SQL (id_in + arch_type + jsonb types
  round-trip); Mongo projection doc (projected doc -> slim anchor; no
  projection -> `_load_anchor` unchanged).
- Safety: `_collect_into` skips marked anchor even with read-only OFF;
  `TieredMemory.execute_plan` does not insert marked anchors into L1/L2.
- Seam: declared + ro + caps -> Route A fires (marker present, counter);
  any condition missing -> byte-identical full anchors. Route B: ordered
  list path with projection -> order preserved, 20 slim anchors.
- Parity: `feed` with projection on == oracle feed bytes; `feed_page`
  top-20 == baseline top-20.
- Counters: `projection_count` on both backends (bench observability,
  matches `rel_hop_count` pattern).

## Bench protocol

A/B/A same-session, ratios only. Rungs: (1) feed baseline no-projection,
(2) feed + Route A (both engines -- the "generalizes" datapoint),
(3) feed_page jac vs feed_page baselines (headline), (4) uuid-intern on/off
rider. Pause + notify user before any server boot.

## Out of scope

Typed columns; write-path anything; P3 view short-circuit; toml declaration
surface; `:ro`/effect inference (S2, see walker-effect-inference-plan
memory); Mongo ordered-index feed_page (GTI ordered_traversal integration
-- Mongo runs feed_page via its existing path, unprojected list floor, and
that asymmetry is reported honestly); expression index on created_at
(optional follow-up).
