import from typing { cast }

import from jaclang.runtimelib.query_utils {
    _trace_enabled,
    _filter_type_name,
    _filter_has_predicates,
    _extract_field_predicates,
    _materialize_ids,
    _path_root_anchor
}


"""Whether an unsliced traversal's final hop preserves canonical edge-insertion
order. The `JAC_ORDERED_TRAVERSAL` env var overrides the `[run] ordered_traversal`
toml flag (truthy: 1 / true / yes / on, case-insensitive). Default off -- the
planner returns the faster unordered set-narrowing result; set it on to restore
canonical edge-insertion order. Slices are ordered regardless of this (decided
by the caller), so this only governs the unsliced single-hop case."""
def _ordered_traversal_enabled -> bool {
    import os;
    env = os.environ.get("JAC_ORDERED_TRAVERSAL");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    try {
        import from jaclang.project.config { get_config }
        cfg = get_config();
        return cfg is not None and cfg.run.ordered_traversal;
    } except Exception {
        return False;
    }
}


"""Whether multi-hop chains crossing root boundaries should stay on the
topology-index fast path (hopping between per-root indices) instead of bailing
to the edge walk. The `JAC_CROSS_ROOT_RESOLVE` env var overrides the
`[run] cross_root_resolve` toml flag (truthy: 1 / true / yes / on). Default
off."""
def _cross_root_resolve_enabled -> bool {
    import os;
    env = os.environ.get("JAC_CROSS_ROOT_RESOLVE");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    try {
        import from jaclang.project.config { get_config }
        cfg = get_config();
        return cfg is not None and cfg.run.cross_root_resolve;
    } except Exception {
        return False;
    }
}


def _trace_hop(
    strategy: str,
    hop_idx: int,
    in_count: int,
    out_count: int,
    hop: ChainHop,
    extra: str = ''
) -> None {
    if not _trace_enabled() {
        return;
    }
    edge_label = hop.edge_type or '*';
    node_label = hop.node_type or '*';
    suffix = f" {extra}" if extra else '';
    logger.info(
        f"[query] hop[{hop_idx}]:{strategy} edge={edge_label} node={node_label}"
        f" dir={hop.direction} in={in_count} out={out_count}{suffix}"
    );
}


def _trace_final(strategy: str, narrowed: int, extra: str = '') -> None {
    if not _trace_enabled() {
        return;
    }
    suffix = f" {extra}" if extra else '';
    logger.info(f"[query] final:{strategy} narrowed={narrowed}{suffix}");
}


def _try_pushdown(mem: Memory, plan: QueryPlan) -> list[NodeAnchor] {
    result: list[NodeAnchor] = [];
    for anchor in mem.execute_plan(plan) {
        if (
            plan.post_filter is not None
            and anchor.archetype is not None
            and not plan.post_filter(anchor.archetype)
        ) {
            continue;
        }
        result.append(cast(NodeAnchor, anchor));
    }
    if plan.slc is not None and 'slice' not in mem.capabilities() {
        result = result[plan.slc];
    }
    return result;
}


def _build_hops(path: ObjectSpatialPath) -> list[ChainHop] {
    destinations = path.destinations[:-1] if path.edge_only else path.destinations;
    chain: list[ChainHop] = [];
    for dest in destinations {
        chain.append(
            ChainHop(
                dest=dest,
                edge_type=_filter_type_name(dest.`edge),
                node_type=_filter_type_name(dest.nd),
                direction=dest.direction.value,
            )
        );
    }
    return chain;
}


def _hop_via_walk(
    mem: Memory, ids: set[UUID], dest: ObjectSpatialDestination
) -> set[UUID] {
    import from jaclang { JacRuntimeInterface }
    anchors = _materialize_ids(mem, list(ids));
    archetypes: list[NodeArchetype] = [
        cast(NodeArchetype, a.archetype)
        for a in anchors
        if a.archetype is not None
    ];
    next_nodes = JacRuntimeInterface.edges_to_nodes(archetypes, dest);
    return {cast(UUID, n.__jac__.id) for n in next_nodes};
}


def _hop_via_walk_ordered(
    mem: Memory, ids: set[UUID], dest: ObjectSpatialDestination, slc: slice
) -> list[UUID] {
    import from jaclang { JacRuntimeInterface }
    anchors = _materialize_ids(mem, list(ids));
    archetypes: list[NodeArchetype] = [
        cast(NodeArchetype, a.archetype)
        for a in anchors
        if a.archetype is not None
    ];
    next_nodes = JacRuntimeInterface.edges_to_nodes(archetypes, dest);
    ordered: list[UUID] = [cast(UUID, n.__jac__.id) for n in next_nodes];
    return ordered[slc];
}


"""Predicate-pushdown fast path for a value-filtered final hop.

The in-process walk (`_hop_via_walk`) materializes *every* neighbor just to
apply a `where`-style field comparison. When the backend can filter archetype
fields natively (`field_pushdown`) we can instead:

  1. narrow to the type-matching candidate set via the topology index — pure
     UUIDs, no node loads — exactly as the type-only hop does; then
  2. hand the backend `{_id IN narrowed} AND {field predicates}` so it returns
     only the rows that already pass the comparison.

Returns the materialized anchors, or None to signal "couldn't push down —
use the walk". Bails (None) whenever pushdown would be unsafe or unhelpful:
no capable backend, an edge-side predicate (filters the edge row, not the
node), a slice (ordering/limit interacts with the retained post-filter), no
usable index, foreign-root inputs, or nothing extractable from the lambda.

The original node filter is retained as the plan's `post_filter`, so even a
*partial* extraction stays correct — the backend pre-narrows, the lambda has
the final say (including the `isinstance` type guard and any comparison we
could not lift). `node_type_final` is deliberately left unset: the index
already narrowed by type with MRO/subclass fan-out, and a literal
`arch_type` equality would wrongly drop subclass instances."""
def _try_field_pushdown(
    mem: Memory,
    current_ids: set[UUID],
    last_hop: ChainHop,
    idx: (TopologyIndex | None),
    root_anchor: (NodeAnchor | None),
    slc: (slice | None)
) -> (list[NodeAnchor] | None) {
    if slc is not None or idx is None or root_anchor is None {
        return None;
    }
    caps = mem.capabilities();
    if 'field_pushdown' not in caps or 'id_in' not in caps {
        return None;
    }
    # Edge-side predicates filter the edge archetype, which execute_plan does
    # not see — leave the whole hop to the walk so they're applied correctly.
    if _filter_has_predicates(last_hop.dest.`edge) {
        return None;
    }
    field_preds = _extract_field_predicates(last_hop.dest.nd);
    if not field_preds {
        return None;
    }
    # The index can only resolve hops whose every input ID it owns.
    import from jaclang.runtimelib.topology_index { SELF_ROOT }
    if not all(
        (lid := idx.node_to_lid.get(uid)) is not None
        and idx.node_table[lid][2] == SELF_ROOT for uid in current_ids
    ) {
        return None;
    }
    triple = (last_hop.edge_type, last_hop.node_type, last_hop.direction);
    narrowed = idx.resolve_chain(current_ids, [triple]);
    if narrowed is None {
        return None;
    }
    plan = QueryPlan(
        root_id=root_anchor.id,
        chain=[],
        field_predicates=field_preds,
        id_in=narrowed,
        post_filter=last_hop.dest.node_filter,
    );
    if not (plan.needs() <= caps) {
        return None;
    }
    _trace_final('field-pushdown', len(narrowed), f"preds={field_preds}");
    return _try_pushdown(mem, plan);
}


def _get_usable_index(root_anchor: (NodeAnchor | None)) -> (TopologyIndex | None) {
    if root_anchor is None {
        return None;
    }
    idx = root_anchor.get_topology_index();
    if not isinstance(idx, TopologyIndex) or len(idx) == 0 {
        return None;
    }
    return idx;
}


def _resolve_prefix(
    mem: Memory,
    ids: set[UUID],
    prefix_hops: list[ChainHop],
    idx: (TopologyIndex | None)
) -> set[UUID] {
    current: set[UUID] = ids;
    for (i, hop) in enumerate(prefix_hops) {
        next_ids = resolve_hop(mem, current, hop, idx, i, slc=None);

        current = cast(set[UUID], next_ids);
    }
    return current;
}


impl resolve_hop(
    mem: Memory,
    current_ids: set[UUID],
    hop: ChainHop,
    idx: (TopologyIndex | None),
    hop_idx: int,
    slc: (slice | None) = None
) -> (set[UUID] | list[UUID]) {
    has_pred = (
        _filter_has_predicates(hop.dest.nd) or _filter_has_predicates(hop.dest.`edge)
    );
    in_count = len(current_ids);
    if not has_pred and idx is not None {
        import from jaclang.runtimelib.topology_index { SELF_ROOT }
        if all(
            (lid := idx.node_to_lid.get(uid)) is not None
            and idx.node_table[lid][2] == SELF_ROOT for uid in current_ids
        ) {
            if slc is not None {
                ordered = idx.resolve_chain_ordered(
                    current_ids, hop.edge_type, hop.node_type, hop.direction, slc
                );
                _trace_hop(
                    'index:ordered',
                    hop_idx,
                    in_count,
                    len(ordered),
                    hop,
                    f"slc={slc.start}:{slc.stop}"
                );
                return ordered;
            }
            triple = (hop.edge_type, hop.node_type, hop.direction);
            narrowed = idx.resolve_chain(current_ids, [triple]);
            if narrowed is not None {
                _trace_hop('index:set', hop_idx, in_count, len(narrowed), hop);
                return narrowed;
            }
        }
    }

    if slc is not None {
        walked_ordered = _hop_via_walk_ordered(mem, current_ids, hop.dest, slc);
        _trace_hop(
            'walk:ordered',
            hop_idx,
            in_count,
            len(walked_ordered),
            hop,
            f"slc={slc.start}:{slc.stop}"
        );
        return walked_ordered;
    }
    walked = _hop_via_walk(mem, current_ids, hop.dest);
    _trace_hop('walk:set', hop_idx, in_count, len(walked), hop);
    return walked;
}


impl resolve_path_anchors(
    mem: Memory, path: ObjectSpatialPath, slc: (slice | None) = None
) -> list[NodeAnchor] {
    if not path.origin {
        return [];
    }
    chain = _build_hops(path);
    if not chain {
        return [nd.__jac__ for nd in path.origin];
    }

    if not path.origin[0].__jac__.persistent {
        import from jaclang { JacRuntimeInterface }
        origin: list[NodeArchetype] = path.origin;
        destinations = path.destinations[:-1] if path.edge_only else path.destinations;
        for dest in destinations {
            origin = JacRuntimeInterface.edges_to_nodes(origin, dest);
        }
        anchors: list[NodeAnchor] = [n.__jac__ for n in origin];
        if slc is not None {
            anchors = anchors[slc];
        }
        return anchors;
    }

    root_anchor = _path_root_anchor(mem, path);

    idx = _get_usable_index(root_anchor);
    current: set[UUID] = {cast(UUID, nd.__jac__.id) for nd in path.origin};
    # Cross-root fast path: resolve the whole multi-hop chain across root
    # boundaries by hopping between per-root topology indices, rather than
    # bailing to the edge walk at the first foreign node. Only engages for
    # unfiltered, unsliced multi-hop chains; predicates, ordering, slicing and
    # field pushdown are left to the per-hop path below. A None result means a
    # foreign root failed to load -- fall through to the correct (slower) walk.
    if (
        idx is not None
        and len(chain) > 1
        and slc is None
        and _cross_root_resolve_enabled()
        and not any(
            _filter_has_predicates(h.dest.nd) or _filter_has_predicates(h.dest.`edge)
            for h in chain
        )
    ) {
        triples = [(h.edge_type, h.node_type, h.direction) for h in chain];
        crossed = idx.resolve_chain_cross_root(mem, current, triples);
        if crossed is not None {
            _trace_final('cross-root', len(crossed));
            if root_anchor is not None {
                plan = QueryPlan(
                    root_id=root_anchor.id,
                    chain=[],
                    id_in=crossed,
                    post_filter=None,
                );
                if plan.needs() <= mem.capabilities() {
                    return _try_pushdown(mem, plan);
                }
            }
            return _materialize_ids(mem, list(crossed));
        }
    }
    if len(chain) > 1 {
        current = _resolve_prefix(mem, current, chain[:-1], idx);
    }
    last_hop = chain[-1];
    last_has_post_filter = _filter_has_predicates(last_hop.dest.nd);
    # Predicate pushdown: when the final hop carries a field comparison and the
    # backend can filter fields natively, narrow by type via the index and push
    # the comparison down to the backend instead of loading every neighbor to
    # filter it. None means "not eligible" — fall through to the walk below.
    if last_has_post_filter {
        pushed = _try_field_pushdown(mem, current, last_hop, idx, root_anchor, slc);
        if pushed is not None {
            return pushed;
        }
    }
    post_filter: (Callable[[Archetype], bool] | None) = (
        last_hop.dest.node_filter if last_has_post_filter else None
    );
    use_ordered = (not last_has_post_filter) and (
        slc is not None or (len(chain) == 1 and _ordered_traversal_enabled())
    );
    effective_slc: (slice | None) = None;
    if use_ordered {
        effective_slc = slc if slc is not None else slice(None, None, None);
    }
    result = resolve_hop(mem, current, last_hop, idx, len(chain) - 1, effective_slc);
    if isinstance(result, list) {
        return _materialize_ids(mem, result);
    }

    if root_anchor is not None {
        plan = QueryPlan(
            root_id=root_anchor.id,
            chain=[],
            id_in=result,
            node_type_final=last_hop.node_type,
            slc=slc,
            post_filter=post_filter,
        );
        if plan.needs() <= mem.capabilities() {
            _trace_final('pushdown', len(result));
            return _try_pushdown(mem, plan);
        }
    }
    _trace_final('floor', len(result));
    return _materialize_ids(mem, list(result), post_filter=post_filter, slc=slc);
}
