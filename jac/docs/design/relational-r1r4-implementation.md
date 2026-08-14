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

## Status
- [x] plan written
- [ ] mirrors: DDL/trigger/backfill in store
- [ ] stream mirror fetch + exact ACL fast path
- [ ] StreamNode frag + serializer Fragment emit
- [ ] tests + parity + write-oracle + bench + commit
- [ ] R3: edge tables + join traversal (only if context remains;
      est −4 ms; needs id directory + untyped-hop UNION fallback)
