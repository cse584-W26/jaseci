# Projection Pushdown for pg-rel -- Design Spec (NO IMPLEMENTATION YET)

Date: 2026-07-13. Status: SPEC ONLY by user directive -- ideation + decisions
documented for review; implementation deliberately not started. Companion to
`2026-07-13-pg-rel-backend-design.md` (edges-as-rows MVP, since built + validated).

## Problem

The measured read-path tail on the feed workload is hydration: serializer ~25% +
anchor hydration ~17% of active samples (dump-loop profile, 2026-07-10), and the
same-session A/B showed hop resolution moving to SQL leaves ~113ms p50 -- the
remaining bill is dominated by deserializing ~2,550 full anchors per request to
produce view objects that use a subset of each anchor's payload.

Projection pushdown = fetch only the fields the walker will actually use
(`SELECT` on JSONB paths), skip full-anchor deserialization. It is the ONLY
open lever that touches this 42% band; chain pushdown and order pushdown do not.

## Why this is the hard one (the safety problem)

A partially-hydrated anchor is a landmine with two distinct failure modes:

1. **Wrong-value reads**: walker touches an unprojected field -> gets the
   archetype's default value silently. Worst kind of bug: no crash, wrong data.
2. **Write-back corruption**: the commit path's dirty-scan
   (`TieredMemory._collect_into`) hashes ALL fields via
   `Serializer._compute_hash` / `derive_dirty_fields`; missing fields read as
   changed -> a "clean" read request writes default values over real data.

Any design is therefore 20% SQL and 80% proving the walker can't observe the
difference.

## Decision 1 -- Integration point

- **P1 (chosen): `QueryPlan.projection` through `execute_plan`.** QueryPlan
  already carries `field_predicates`, `id_in`, `node_type_final`, `slc`, and
  capability negotiation (`plan.needs() <= mem.capabilities()`); the resolver's
  final-hop tail already builds a QueryPlan when the hop result is a set. Add
  `projection: (set[str] | None)`, a `'projection'` capability string, and
  implement `execute_plan` on PostgresRelBackend. Smallest seam, mirrors every
  pattern this branch already shipped.
- P2 (rejected): project inside `resolve_hop_sql`/`resolve_chain_sql`. Wrong
  layer -- those return IDs; mixing payload fetch into topology resolution
  couples the two pushdowns and breaks the fallback ladder's simplicity.
- P3 (rejected for now): bypass anchors entirely -- walker-less "select"
  reports where the runtime returns view rows straight from SQL. Biggest win,
  but it is a new language feature (report shape inference), not a backend
  increment. Revisit with the language team after annotations exist.

## Decision 2 -- What comes back

- **R1 (chosen): real NodeAnchors with partially-populated archetypes**, plus
  a transient marker `anchor._projected_fields: set[str]`. Keeps the
  `resolve_path_anchors -> list[NodeAnchor]` contract; walkers/`to_view` code
  unchanged. The marker exists so guards (below) can tell partial from full.
- R2 (rejected): lazy field-fault hydration (`__getattr__` on missing field
  fetches on demand). Safest semantics but requires surgery on the archetype
  attribute model (real attrs, not dict lookups) + per-access overhead on the
  hot path; complexity lands in shared runtime code, violating the
  attribution rule this branch has held.
- R3 (rejected): view dicts instead of anchors -- breaks the resolver contract
  and every downstream isinstance; that is P3 in disguise.

## Decision 3 -- Safety mechanism (the core decision)

- **S-MVP (chosen): explicit projection declaration + read-only gate, both
  required.**
  1. The walker (or its app) declares the projection explicitly -- an
     annotation the runtime consumes, e.g. walker-level
     `projects: {"Tweet": {"content", "created_at", "username", ...}}`
     surfaced through app config for the MVP (same env/config pattern as
     JAC_ORDER_PUSHDOWN) until real syntax exists. No declaration -> no
     projection -> full hydration. Explicit = auditable; the wrong-value
     hazard becomes a visible contract instead of an inference.
  2. Projection only activates when the read-only rung is active
     (`JAC_READ_ONLY` semantics): the commit path never runs, so failure
     mode 2 (write-back) is structurally impossible. Belt AND suspenders:
     `_collect_into` additionally skips any anchor carrying
     `_projected_fields` (cheap guard, protects mixed configurations).
- S2 (successor, not MVP): compiler-derived projection -- a
  `__jac_field_projection__` tag computed from walker-body analysis, exactly
  parallel to the existing `__jac_field_predicates__` tagging used by filter
  pushdown. Conservative rule: any un-analyzable access (dynamic getattr,
  method call into non-analyzed code) -> no tag -> full hydration. This is
  the durable home ("specialized syntax later"), and it turns the explicit
  declaration into a compiler-verified one (declared ⊉ used = compile error).
- S3 (rejected): trust-the-walker with no declaration (project to the view
  fields seen in practice). Silent wrong-value reads; no.

## Chosen design (assembled)

1. `QueryPlan.projection: set[str] | None` + `needs()` contributes
   `'projection'` when set.
2. Resolver final-hop tail (already QueryPlan-shaped): attach the projection
   for the final node type when (a) declaration exists for that type,
   (b) read-only rung active, (c) backend advertises `'projection'`.
   Anything missing -> today's behavior, byte-identical.
3. `PostgresRelBackend.execute_plan(plan)`:
   `SELECT id, type, arch_module, arch_type, data->'archetype'->>f1, ... FROM
   anchors WHERE id = ANY(%s)` (+ `node_type_final` filter; composes with
   `id_in` from the hop/chain result). Builds anchors via a slim constructor
   that sets only projected archetype fields, skips edges-stub construction,
   access-map parse, and `snapshot_field_hashes` (read-only rung = never
   diffed), stamps `_projected_fields`.
4. Order/limit composition: `plan.slc` + JAC_ORDER_PUSHDOWN key can ride the
   same statement (`ORDER BY data->'archetype'->>key LIMIT n`) -- this is
   where projection + order + slice finally becomes "hydrate one page".
5. Fallback ladder unchanged: any error -> full `_materialize_ids` floor.

## Sizing (honest, UNVERIFIED until benched)

Feed's TweetView consumes most Tweet fields, so the field-narrowing win is
modest; the real savings are the per-anchor fixed costs skipped: serializer
envelope/type resolution, edges-stub list construction, access-map parse,
field-hash snapshotting. Estimate 10-25ms of the current ~113ms feed p50 on
its own; combined with order+limit (hydrate ~20 instead of 2,550) it is the
difference between ~113 and the 40-70 band. The decisive variant is
projection+limit, not projection alone.

## Testing plan (when implemented)

- Unit: execute_plan projection SQL (fields present/absent, missing field ->
  default + marker; node_type filter; order+slice composition).
- Safety: dirty-scan guard test -- projected anchor in a changeset context
  must never produce intents (marker skip), even with read-only off.
- Seam: read-only walker with declaration -> projected path (assert marker +
  reduced fields); same walker without declaration -> full anchors,
  byte-identical results for fields in the view.
- Parity: littleX feed with projection on == oracle-identical feed bytes.
- Negative: walker touching an undeclared field in a test asserts the default
  -- documented hazard made visible (this test is the argument for S2).

## Out of scope

Typed columns (separate design), Mongo execute_plan parity, write-path
anything, P3 view short-circuit, L2 caching of projected anchors (projected
anchors must NOT enter L2 write-through; MVP runs read-only where commit/L2
write-through never fires -- note for the implementer).

## Open questions for review

1. Declaration surface for MVP: env/config (`JAC_PROJECTION="Tweet:content,created_at,..."`)
   vs app jac.toml table? (Env matches the flag family; toml reads better for
   multi-type declarations. Lean: toml `[run.projection]` table, env override.)
2. Should projected anchors enter L1 at all? Per-request L1 makes it safe-ish
   (same walker, same declaration), but skipping L1 insertion entirely is the
   conservative default and costs only repeat-access within one request.
3. Does `to_view`-style method access count as "the walker uses field X" for
   the future compiler analysis (S2)? Method-body analysis scope decides how
   often S2 can fire without annotations.
