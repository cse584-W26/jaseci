# Typed relational backend: compiling archetypes to per-type tables

*Design note, 2026-08-13. Evidence gathered on the littleX feed workload
(2,550-tweet feed, 100 profiles, 5,000 tweets, 5,000 follows), branch
`perf/pg-native-opts` @ `21b7f2252`, side-by-side against the hand-tuned
Postgres baseline in DBHarness.*

## The question

The hand-tuned Postgres baseline serves the feed in **1.9 ms of DB time**;
the Jac pg-native runtime spends **~41 ms** for the same result set. Why —
and is DB parity reachable without giving up the language abstraction?

## What the store does today

Every anchor — every node of every type, every edge of every type — is one
row in a single table:

```sql
anchors(id uuid PK, kind text, arch_type text, arch_module text,
        root_id uuid, src uuid, dst uuid, undirected bool,
        props jsonb, fingerprint text, format_version int,
        updated_at timestamptz, seq bigserial,
        src_type text, dst_type text)   -- endpoint types, added 21b7f2252
```

Archetype fields live inside `props` jsonb. Relationality is two uuid
columns (`src`, `dst`) pointing back into the same table. The type system's
knowledge that `Follow` connects `Profile -> Profile` exists nowhere in the
schema (the `src_type`/`dst_type` denormalisation is the first sliver of it).

A chain like `[me ->:Follow:-> [?:Profile] --> [?:Tweet]]` therefore
compiles to a pointer walk: index-probe every incident edge, probe every
target node by primary key, discard type mismatches. The baseline expresses
the same reachability as a set predicate (`WHERE author_id IN (...)`) that
the planner satisfies with one hash join over one 124-page scan.

## Measured decomposition of the gap

All numbers are per-request on the same data, `EXPLAIN (ANALYZE, BUFFERS)`:

| layout | buffers | DB time |
|---|---|---|
| anchors table, pointer walk (before this branch) | ~37,000 | ~48 ms |
| + typed-endpoint index + batched ACL prefetch (today) | ~30,000 | ~41 ms |
| anchors table, set-predicate rewrite (prototype) | 1,052 | ~9 ms |
| per-type tables (the baseline itself) | **134** | **1.9 ms** |

Component costs isolated:

| component | buffers | ms | note |
|---|---|---|---|
| 2,500 pkey probes vs one seq scan | 5,457 vs 134 | 3.3 vs ~0.7 | access pattern |
| shipping 2,500 `props` jsonb blobs | +447 | **+0.6** | payload is nearly free *in the DB* |
| adjacency correlated subquery | +12,525 | +9.2 | computes edge lists nobody reads |
| 2-hop traversal statement | 10,972 | 8.3 | was 18,702 / 12.9 before typed endpoints |
| per-statement re-planning | — | ~0.5–1.0/stmt | no prepared-statement reuse |

Row fatness, measured directly: the same 5,000 tweets occupy **897 pages**
as jsonb-carrying anchors vs **124 pages** as typed columns (~700 B/row vs
~198 B/row). Clustering the table (`ORDER BY kind, arch_type, root_id`)
recovers almost nothing (5,904 -> 5,736 buffers): the cost is per-probe,
not per-page.

Two conclusions fall out:

1. **The set-vs-pointer distinction dominates** (30k -> 1k buffers), and
   the residual 8x (1,052 vs 134) is row fatness. Both are layout
   properties, not index defects — each individual pkey lookup already
   costs the btree minimum (3 buffers).
2. **The DB is not where the request time lives.** The feed costs ~290 ms;
   the DB is ~41 ms of it. Perfect schema parity caps out at roughly
   −35 ms. The rest is the app side (wire + deserialisation, see
   "Scope limit" below).

## Why the single table exists

The generic encoding buys real things the runtime relies on:

- **No migrations.** New archetype or new field = no DDL at runtime, no
  migration story imposed on user code.
- **Untyped hops.** `[-->]` is one index scan; under per-type tables it is
  a UNION over every edge table.
- **UUID -> row without knowing the type.** `batch_get(ids)` hits one pkey
  index. Per-type tables need an id -> table directory.
- **Uniform ownership/ACL.** `root_id` + access blob sit on every row
  identically; permission checks are type-agnostic.
- **Subtype polymorphism** via one `graph_types` closure table rather than
  per-hierarchy unions.

None of these is impossible under per-type tables — ORMs ship migrations
and joined-table inheritance daily — but each is real engineering the
generic design got for free.

## The trajectory already in the code

Two existing mechanisms are partial steps toward typed physics *inside*
the generic table:

- **Promotions** (`PgStore._apply_promotions`): a declared hot field
  becomes a `GENERATED ALWAYS AS (props->'archetype'->>'f') STORED` column
  with a partial index `WHERE arch_type = '...'`. Typed-column reads
  without changing the write path.
- **Typed-endpoint columns** (`src_type`/`dst_type`, this branch): the
  edge row carries its endpoints' archetype names, indexed as
  `(src, arch_type, dst_type)`, and the SQL compiler pushes the target
  type test into the edge scan. Measured: target probes 5,000 -> 2,500,
  traversal 12.9 -> 8.3 ms. NULL-tolerant so a stub-written edge is never
  dropped; the node join downstream stays authoritative.

The logical endpoint of this trajectory is full per-type compilation.

## Proposed design: derive the relational schema from archetypes

The language already has what an ORM makes the user write by hand: statically
declared archetypes with typed fields, and edge declarations that could carry
endpoint constraints. The compiler can therefore emit:

1. **One table per node archetype** — typed columns from `has` declarations
   (promoting scalars; jsonb spillover for dynamic/complex fields), plus the
   uniform runtime columns (`id, root_id, access, updated_at`).
2. **One table per edge archetype** — `(src, dst, seq, props?)` with real
   foreign keys where the declaration constrains endpoint types; a generic
   edge table only for untyped/GenericEdge.
3. **An id directory** `anchor_dir(id -> table)` maintained on write, so
   `batch_get` and untyped operations keep working (one extra cheap lookup,
   or a cached negative).
4. **Chain compilation to joins.** A typed chain becomes joins across the
   per-type tables — which is precisely the baseline's query. Untyped hops
   fall back to UNIONs or the directory.
5. **DDL as compiler output.** Archetype change -> emitted migration
   (additive cases automatic; destructive cases surfaced to the user). This
   is the part ORMs make users own; the language can own it instead because
   the schema is derived, not authored.

### Soundness obligations

- Untyped hops and `GenericEdge` must keep exact semantics (UNION path).
- Subtype hierarchies: joined-table or single-table-per-hierarchy, decided
  per hierarchy; `graph_types` remains the closure oracle.
- ACL must stay type-agnostic: ownership columns replicated uniformly.
- The overlay contract (uncommitted session writes visible to queries)
  is unchanged — it lives above the store.
- Migration of existing single-table databases: one-time partitioned copy,
  or a compatibility view during transition.

### What it buys, honestly

- DB time for this workload: ~41 ms -> plausibly ~2–5 ms (near-parity).
- Kills the adjacency subquery *by construction* (edge tables are the
  adjacency).
- Row fatness gone (~700 B -> ~200 B/row); seq scans and set predicates
  become available to the planner.
- Paper claim upgrade: the runtime doesn't merely *hide* the DB behind the
  language — the language's type declarations are sufficient to *derive*
  the schema an expert would have written.

### Scope limit (read before celebrating)

At today's 290 ms/request, the app side — pgwire transfer of ~1.6 MB and
Python deserialisation of 2,500 anchors — is ~250 ms and survives any
schema change untouched. Schema compilation is the right long-term DB
answer; it is not the current bottleneck. Sequencing: app-side first.

## Addendum (2026-08-13 EOD): verdict after the streaming runtime landed

Re-measured once proven zero-materialization, typed-endpoint pruning, and
membership pushdown were in (`c4b7e1862`..`310ae86d3`). Both databases
surgically restored to the exact uniform-seed state and VACUUM FULLed
first (an earlier measurement on write-bench-bloated data overstated
everything ~1.45x). Canonical feed: server p50 **96 ms**, 2,552 items.
Driver-inclusive floors, raw psycopg, seed-clean data:

| floor | p50 |
|---|---|
| A: current schema, stream-path SQL (traversal + load_props) | **38.2 ms** |
| A1: traversal only | 6.5 |
| A2: props fetch, jsonb parsed to dicts | 29.6 |
| A2x: same, props as unparsed text | 17.6 (wire ≈ 6.6) |
| A2y: same, no props on wire | 11.0 (jsonb->dict parse ≈ 12.0) |
| B: relational schema, one typed query (baseline's own) | **8.7 ms** |

**Schema-sensitive share: ~30 ms of the 96.** The other ~58 ms is per-row
runtime semantics - slim anchors, Permission objects, ACL checks,
fragment memo, encode, session/txn, HTTP - and survives any schema
unchanged. A perfect per-type-table rewrite therefore lands the feed at
roughly **66-70 ms, not 15**: a ~1.4x, not the 7x that separates us from
the hand-tuned baseline.

The morning's case for the rewrite was ~250 ms of costs that the day's
runtime work eliminated by other means (adjacency subquery deleted from
the stream path, double row-reads gone, typed-endpoint pruning, no
archetype materialization). What is left for the schema to fix is mostly
**jsonb wire+parse (~19 ms)** and **pointer-walk vs hash-join +
double-fetch (~11 ms)**.

Two-thirds of that is reachable *without* the rewrite: emit the response
fragment server-side (`props->'archetype'` shaped by jsonb_build_object,
shipped as text, keyed by (id, xmin) into the existing fragment memo) and
Python never parses props at all - estimated −15-19 ms, schema-neutral,
no migration story. That is the next lever, ahead of the rewrite.

Verdict: the typed relational backend remains the right *architectural*
endgame - and the paper's best story stands (the language's declarations
derive the expert schema) - but as an engineering priority it is now
third, behind DB-side fragment projection and per-row ACL batching. It
buys 1.4x on today's runtime at the cost of the full migration/
polymorphism/id-directory scope below.

## Interim steps that don't need the full design

| step | saving | status |
|---|---|---|
| typed-endpoint index + compiler pushdown | −7.7k buffers, −4.6 ms | shipped (`21b7f2252`) |
| batched ACL root prefetch | 62 -> 12 stmts, ~−15 ms wall | shipped (`21b7f2252`) |
| drop adjacency subquery when unread | −12.5k buffers, −9.2 ms | needs sound design (naive lazy-edges broke overlay/cascade semantics — see revert of `8ec6f1a7b`) |
| named prepared statements in the driver | ~−3 ms | open, low risk |
| projection of bodies in the hop query | −5.9k buffers, −1 stmt | open; needs DISTINCT-ON for convergent paths |
