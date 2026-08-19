# Relational schema program: derive the database from the program

*Design note, 2026-08-18, branch `feat/relational-schema` off main
`fdbf693d6`. Supersedes the mirror-table trajectory of
`typed-relational-backend.md` / `relational-r1r4-implementation.md`
(branch `perf/relational-program`): mirrors are read-only derived state
over the monolithic `anchors` table; this program replaces the monolith
itself.*

## Decision

Two PRs, DB first -- flipped from the earlier planner-first sequencing
because the planner consumes the extracted schema:

- **PR-A `feat/relational-schema`** -- schema extraction (compiler pass) +
  relational storage as source of truth + read-path correctness.
- **PR-B `feat/schema-aware-planner`** (branched from A) -- the
  `perf/relational-program` planner work (StreamProofPass, fused
  single-statement stream query, distributed top-K, exact-ACL fast path)
  re-targeted at real typed tables. "Membership in the mirror IS the type
  test" (R3) holds natively for a real per-type table; the mirror layer
  and its trigger maintenance are not carried forward. Its column design
  (`frag`, `acl_all`, `acl_spec`, typed field columns) moves into the
  typed tables from birth.

## Target schema

```sql
nodes(id uuid PK, arch_type text, arch_module text, root_id uuid,
      seq bigserial)                      -- thin id->type directory

n_<type>(id uuid PK REFERENCES nodes(id) ON DELETE CASCADE,
         root_id uuid REFERENCES nodes(id),
         <typed column per scalar has-field>,
         <uuid FK column per node-ref has-field>,
         <jsonb column per obj/dynamic has-field>,
         acl_all smallint, acl_spec boolean, access jsonb,
         frag text, extra jsonb)          -- one per node archetype

edges(id uuid PK, edge_type text NOT NULL,
      src uuid NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
      dst uuid NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
      root_id uuid, undirected boolean, seq bigserial, props jsonb)
-- ONE edges table (not per-edge-type): untyped [-->] stays one scan,
-- which bare ++> GenericEdge usage requires. LIST partitioning by
-- edge_type is the opt-in tightening path (per-partition FKs).

obj_<type>(node_id uuid REFERENCES nodes(id) ON DELETE CASCADE,
           field text NOT NULL, idx int,
           <typed column per scalar field>,
           PRIMARY KEY (node_id, field))  -- flat-scalar embedded objs:
-- row presence = obj existence (None vs field-NULL disambiguated by
-- absence); (node_id, field, idx) extends to list[Obj]; shared across
-- all archetypes embedding the type because ids are globally unique
-- via the directory.
```

PK everywhere is the anchor UUID. Real FKs become possible exactly
because the directory exists: `edges.src` cannot reference "one of N
typed tables", but it can reference `nodes(id)` which cascades into the
typed row.

Field tiers (what a `has` declaration becomes):

| declared type | tier | column |
|---|---|---|
| str/int/float/bool/bytes/UUID/datetime/... | scalar | typed column |
| enum | enum | text |
| node/edge archetype | node_ref / edge_ref | uuid FK -> nodes(id) (today a `{'$ref': uuid}` blob in props jsonb) |
| list[node] | node_ref_list | uuid[] (ordered; element FKs advisory) |
| obj/class value | obj | side table when provably flat-scalar, else jsonb |
| dict, unions, `any`, unresolved | json | jsonb |

Only top-level declared fields get columns/FKs; a `$ref` nested deeper
inside an obj stays inside that field's jsonb -- correct, just not
DB-enforced.

## Schema extraction (PR-A stage 1, shipped with this note)

`GraphSchemaPass` (jac0core, boundary-analysis schedule, after
`EndpointEffectPass`) derives:

- **Node/edge/obj table specs** from archetype `has` declarations, with
  the field tiering above and `flat_scalar` eligibility for objs.
- **Edge endpoint relations**: declared endpoints
  (`edge Post: Profile --> Tweet`) are authoritative; for edges declared
  without endpoints, every `ConnectOp` site contributes an observed
  `(src, dst)` pair. Operand types resolve syntactically (constructor
  calls, `here` via the ability's event signature, `self` via the
  enclosing archetype, `root` -> Root); an unresolvable operand records
  an **open** endpoint (`None`), never a guess. Bare `++>` records
  against `GenericEdge`.

Soundness stance: the planner never needs endpoint closure for
correctness -- joining a typed table IS the type test. The observed map
only decides when an untyped hop may skip the UNION-over-typed-tables;
open endpoints degrade plans, not results.

Output: `interop_manifest.graph_schema` (plain JSON dict), persisted
through the .jir cache (`_build_interop_dict` / restore -- the cache
persists manifest fields explicitly; forgetting that is silent schema
loss on cache-hit loads). Inspect with `jac db schema <file.jac>`.

## A2 shadow storage (shipped)

`runtimelib/relational.jac`: with `JAC_RELATIONAL=shadow` every
`PgStore.upsert`/`delete` also routes rows relationally in the SAME
transaction -- nodes directory + per-archetype typed table (created
lazily: `CREATE IF NOT EXISTS` + per-column `ADD COLUMN IF NOT EXISTS`,
catalogued in `graph_tables`) + edges -- so anchors and the relational
copy can never diverge across a commit boundary. Table plans resolve
manifest-first (the compiler's graph_schema via the loaded module),
reflection-fallback (`Serializer._get_class` + `get_field_types`), so
dynamically created types still route; a type with neither stays
directory-only. Value coercion is guarded per tier: a value that does
not match its column type lands in the row's `extra` jsonb instead of
failing the write. `frag` is deliberately NOT prebuilt here -- it lands
with PR-B where its consumer lives (additive ALTER).

`relational_parity(store)` (and `jac db parity`) compares anchors
against the relational copy: directory presence/type/root, edge
endpoints/type/undirected, and typed scalar/enum/ref columns against
the props projection. It is read-only and flag-independent. Shadow
verification: the entire existing PG persistence surface (session,
unit-of-work, lifecycle, migration e2e, dangling-ref heal, graph query,
OSP suites) passes with the flag ON, plus dedicated tests in
tests/runtimelib/test_relational_shadow.jac.

## Remaining PR-A stages

- **A3 read path**: sqlcompile joins over edges + typed tables,
  `graph_types` stays the subtype oracle (hierarchy = UNION ALL over
  concrete-type tables), batch_get via directory batched per type.
  Cutover order: backfill (INSERT..SELECT from anchors), validate FKs,
  flip reads, then anchors becomes the fallback for walkers/objects and
  schema-less types only.
- Obj side tables (flat-scalar tier) remain queued behind cutover.
- Order preservation: `seq` on edges is traversal insertion order.

## Postgres features queued behind the reorg

UUIDv7 anchor ids (btree locality, no schema change); covering index
`(src, edge_type) INCLUDE (dst, seq)` for index-only hops; LATERAL
top-K per source for PR-B's pushdown; LIST partitioning of edges for
proven-closed edge types; named prepared statements in pgwire; GIN
(jsonb_path_ops) on spillover; CREATE STATISTICS on (arch_type,
root_id). RLS folded ACL stays exploratory-only.
