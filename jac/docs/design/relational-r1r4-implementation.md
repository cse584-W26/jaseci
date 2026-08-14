# R1–R4 implementation working notes (live)

*Target: littleX feed server p50 ≤ 30.2 ms (measured SQLAlchemy bar).
Start: 96 ms @ `2323d3566`. Strategy: R1+R2+R4 collapse into ONE
mechanism — per-archetype mirror tables that precompute the response
fragment and ACL scalars in triggers; the stream path fetches typed
columns for the PROOF FIELDS plus fragment text. R3 (edge tables) last,
smallest win (~4 ms), biggest commitment.*

## The converged design (R1+R2+R4-lite)

Mirror per registered NODE archetype, derived at runtime from
`emit_plan`/`get_field_types` (no compiler change needed):

```sql
CREATE TABLE IF NOT EXISTS g_n_<type>_<mod6>(   -- mod6 = md5(module)[:6]
    id uuid PRIMARY KEY,
    root_id uuid,
    acl_all smallint NOT NULL DEFAULT -1,       -- props->'access'->>'all', typeof-guarded
    acl_spec boolean NOT NULL DEFAULT false,    -- access.roots.anchors non-empty
    frag text NOT NULL,                          -- FULL api fragment, prebuilt:
    -- jsonb_build_object('_jac_type',arch_type,'_jac_id',replace(id::text,'-',''),
    --                    '_jac_archetype','node') || strip_dunder(props->'archetype')
    <typed column per kind-1/2 field, typeof-guarded casts>
);
```

Maintenance: two triggers on `anchors` (INSERT/UPDATE with
`WHEN NEW.kind='NodeAnchor' AND NEW.arch_type='<T>'`; DELETE with OLD
guards) — same txn as the write, so mirrors are exact. Backfill once at
ensure-time: `INSERT..SELECT..ON CONFLICT DO NOTHING`. Mirrors are
derived state: rebuildable, write path untouched, anchors stays truth.

Read path (only inside `_try_stream`, i.e. proof-gated):
1. last hop `nd` is a single class with a ready mirror → SELECT
   `id, root_id, acl_all, acl_spec, frag, <proof fields>` (typed cols).
2. ACL fast path replicating check_access_level EXACTLY for
   `acl_spec=false` rows: owner → pass; else prefetch distinct roots via
   batch_get once; per root compute `rc = root.access.roots.check(ur)`;
   `level = rc if rc is not None else max(acl_all, root.access.all)`;
   pass iff level >= 0. `acl_spec=true` rows: collect, materialize via
   batch_get, run `_acl_read_ok` (full fallback per row).
   (Semantics source: runtime.impl check_access_level: per-anchor
   specific OVERRIDES root contribution which maxes over anchor.all.)
3. StreamNode gets `{proof_field: value}` + `frag` text. Serializer emits
   `orjson.Fragment(frag)` in api mode (stdlib fallback: json.loads).
4. Anything missing (mirror not ready, multi/untyped nd, no orjson...) →
   existing load_props path unchanged.

Memo: fragment text comes prebuilt → the (id,xmin) memo is BYPASSED on
this path (no double bookkeeping, no cross-keyspace collisions).

## Files
- `store.jac`/`store.impl.jac`: `mirror_ready(cls)`, `ensure_mirror(cls)`
  (DDL+triggers+backfill, advisory lock, in-process cache),
  `load_mirror_rows(cls, ids, fields)`.
- `query_planner.impl.jac`: `_try_stream` mirror branch + exact-ACL fast
  path; keep old path as fallback.
- `streamnode.jac`: accept fields dict + frag.
- `serializer.impl.jac`: StreamNode branch emits Fragment when frag set.

## Verification per phase
- 58-test surface + parity (JAC_STREAM=0 vs on, parsed-equal) after each.
- Write bench oracle after mirror triggers land (writes must stay
  oracle-exact WITH triggers firing).
- wallbench 150 for numbers. DBs must be seed-clean first.

## Status — R1/R2/R4 SHIPPED as `a5c3aac34`

- [x] mirrors: DDL/trigger/backfill (jsonb field columns; frag prebuilt in
      trigger; acl_all/acl_spec scalars; CREATE OR REPLACE TRIGGER; backfill
      after triggers with DO NOTHING so concurrent writes win)
- [x] stream mirror fetch + exact ACL fast path (owner pass; per-root
      override-then-max; specials/per-anchor-grants, __jac_access__
      overriders, and shared-root-owned rows take the full per-row path)
- [x] StreamNode frag + orjson.Fragment emit; unproven reads lazily
      inflate from the fragment (found via shared-root suite: report-sink
      comprehensions read fields the proof never collected)
- [x] driver normalisation (pure-Python uuid-as-string vs psycopg UUID)
- [x] 58 tests, value-parity vs JAC_STREAM=0, write oracle exact WITH
      triggers (create 2.17 ms — ~0.3 ms trigger cost — like 2.63,
      follow 4.06)
- [ ] R3: edge tables + join traversal (open; est −4 ms; needs id
      directory + untyped-hop UNION fallback)

**Final seed-clean, same-session:** Jac server p50 **40.1 ms**
(wall 66.8) vs SQLAlchemy **30.9** (p95: Jac ~50 vs SQLAlchemy 55.8 —
Jac is TIGHTER at the tail) vs hand-tuned 14.3. Day trajectory:
305 -> 96 -> 40 server-side; ORM gap now 1.3x at p50, better at p95.

Native-lowering gotchas found while landing (compiler bugs to report):
gen-exprs with binary ops inside join(), heterogeneous tuples into dict
values, and list-literal + variable concatenation all ICE the native
pathway, and E5092 demotion can leave NO bytecode with NO recorded error
— the module compiles to nothing silently. Also jac->SQL string escaping
loses a backslash layer (use left(key,2) <> '__' instead of LIKE E'\_%').
