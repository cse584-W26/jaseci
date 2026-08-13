# C: compiler-proven zero materialization — implementation plan

*Working plan, 2026-08-13. Branch `perf/pg-native-opts` @ `ce219b2e2`
(server p50 178 ms / wall 209 ms on the littleX feed; PG baseline 14/29).
Target: eliminate anchor/archetype/permission/stub construction for chain
results that a compiler pass proves are only trivially observed. Landing
zone ~100–120 ms server-side (DB ~40 + driver ~15 + residual runtime).*

## Confirmed attachment points (verified in-source today)

- **Dataflow solver**: `jaclang/compiler/passes/main/dataflow.jac` —
  `solve_forward/solve_backward(cfg_nodes, transfer)` over `uni.UniCFGNode`
  with `bb_in`/`bb_out`.
- **Pass schedule**: `jaclang/jac0core/compiler.jac` `get_ir_gen_sched()`
  builds `[ASTValidation, SymTabBuild, DeclImplMatch, SemanticAnalysis,
  SemDefMatch, CFGBuild, (MTIRGen), JsxIntrinsicGuard, PlacementApply]`.
  Insert `StreamProofPass` after `CFGBuildPass`.
- **Runtime-visible channel**: `PyastGenPass.exit_archetype`
  (`jaclang/jac0core/passes/impl/pyast_gen_pass.impl.jac:1512`) already
  injects `__jac_async__ = <const>` as a class-body Assign. Inject
  `__jac_stream_fields__ = (<field names>)` the same way when the pass
  stamped the `uni.Archetype` node (attr `stream_fields: tuple | None`).
- **Hub is empty at runtime** for `.jir`-cached modules
  (`JacRuntime.program.mod.hub == {}`) — analysis CANNOT run lazily at
  registration; it must be a compile-time pass whose result rides the
  generated code. (Verified today: probe printed `hub keys: []`.)

## The proof contract

`StreamProofPass` analyses each walker archetype's abilities. A walker gets
`stream_fields = frozenset(F)` only if EVERY use of every chain-expression
result (`uni.EdgeRefTrailer`/atom trailer chains that lower to graph_query
resolve) in the ability body is one of:

1. direct element flow into a local list (list literal concat, `.append`),
2. `len()`, subscript/slice of the *list*,
3. `jid(x)` (reads anchor id only),
4. attribute read of a field in F where F ⊆ statically-scalar fields of the
   node types named in the chain (use `typecache.emit_plan` kinds 1/2 at
   runtime to re-guard),
5. `list.sort(key=f)` / `sorted(key=f)` where `f` resolves to a module-level
   function in the same module whose body is a single `return x.<field>`
   (field joins F),
6. membership of `jid(x)` results in a local set,
7. final `report` of a structure containing the list (serialization sink —
   satisfiable from stored props).

Kill conditions (any ⇒ no annotation, silently): attribute WRITE anywhere
to an element, passing an element to any call not whitelisted, `visit`,
`spawn`, `del`, connect/disconnect ops, `isinstance`/`type()` on elements,
returning/yielding elements, storing into `self.*`/globals, augmented
assignment through an element, `.edges` access, `getattr` with non-literal
name. Aliasing: track the value set through assignments with a forward
may-alias set over the CFG (solver above); any alias escaping kills.

Soundness stance: the pass may under-approve freely (fallback = today's
path); it must never over-approve. Every runtime fast path re-guards
dynamically and falls back to full materialization, so even an analysis bug
degrades to slow-correct, not wrong.

## Runtime side

1. `Session.resolve_stream(q)` used by `resolve_query` ONLY when
   `ctx.current_walker` class has `__jac_stream_fields__` and the query has
   no residual predicates: same `_sql_pairs` ids; then `store.load_props`
   (new: the `load_full` SELECT *without* the adjacency `string_agg`
   subquery — edges provably unobserved); ACL prefetch/check unchanged but
   on **slim anchors**: real `NodeAnchor.__new__` with id/root/access/
   persistent/hash=1, `archetype` = `StreamNode`, `edges` NEVER touched
   (attribute left unset; nothing observes it on this path by proof).
2. `StreamNode`: tiny class with `__slots__ = ('_props', '_anchor')`;
   `__getattr__` serves archetype fields from `_props['archetype']`
   (scalar/list-of-scalar direct; else `_deserialize_value`); anything else
   (including `__setattr__` on fields) triggers `_hydrate()`: full
   materialize via the normal path, swap `anchor.archetype`, delegate.
   `jid` support: `__jac__` property returns `_anchor`.
3. Serializer: in `_serialize_value`, a `StreamNode` in api_mode resolves
   via the (id, version) fragment memo; on miss builds the fragment
   directly from `_props['archetype']` through the emit-plan guards
   (values are already JSON-shaped for fingerprint-matched rows — re-guard,
   fall back to hydrate+normal serialize on any surprise).
4. Overlay: `local` (uncommitted in-session anchors) still wins in
   `_materialize_ids`; stream path only serves ids not present in
   `__mem__`/`local`. In-session mutated rows therefore never stream.

## Test plan

- Eligibility: chain→report walker gets the attr; each kill condition
  denies it (one test per condition).
- Parity: eligible walker returns byte-identical response with
  `JAC_STREAM=0` (env kill-switch) vs on.
- Fallback: eligible walker + runtime surprise (rule registered, foreign
  fingerprint, mutation via hydrate) still correct.
- Full runtimelib suite green.

## Status

- [ ] StreamProofPass skeleton + schedule insertion
- [ ] analysis: chain-expr discovery + use-walk + kill conditions
- [ ] pyast injection of `__jac_stream_fields__`
- [ ] store.load_props (no adjacency)
- [ ] StreamNode + slim-anchor path in resolve_query
- [ ] serializer StreamNode branch (fragment-from-props)
- [ ] tests + parity + full suite
- [ ] re-benchmark (wallbench.py 150)
