"""Topology utils implementation."""

"""Check if topology_index is enabled. Env var JAC_INDEX_ENABLED overrides config."""
impl _is_enabled -> bool {
    import os;
    env = os.environ.get("JAC_INDEX_ENABLED");
    if env is not None {
        return env.lower() in ("1", "true", "yes");
    }
    try {
        import from jaclang.project.config { get_config }
        cfg = get_config();
        return cfg is not None and cfg.run.topology_index;
    } except Exception {
        return False;
    }
}

"""Get the root NodeAnchor that owns this anchor."""
impl _get_root_anchor(anchor: Any) -> Any {
    import from jaclang.jac0core.archetype { NodeAnchor as NA, Root }
    if anchor.root is None {
        if isinstance(anchor, NA) and isinstance(anchor.archetype, Root) {
            return anchor;
        }
        return None;
    }
    try {
        import from jaclang { JacRuntimeInterface as Jac }
        ctx = Jac.get_context();
        root = ctx.mem.get(anchor.root);
        if isinstance(root, NA) {
            return root;
        }
    } except Exception {
        ;
    }
    return None;
}

"""Get the archetype class name."""
impl _type_name(`obj: object) -> str {
    return `type(`obj).__name__;
}

"""Get the MRO type names for a node/edge archetype."""
impl _get_type_mro(`obj: object) -> list[str] {
    import from jaclang.jac0core.archetype {
        NodeArchetype,
        EdgeArchetype,
        WalkerArchetype,
        Archetype
    }
    stop_classes = (NodeArchetype, EdgeArchetype, WalkerArchetype, Archetype, object);
    mro_names: list[str] = [];
    for cls in `type(`obj).__mro__ {
        if cls in stop_classes {
            break;
        }
        mro_names.append(cls.__name__);
    }
    return mro_names;
}

"""Called after an edge is created between source and target."""
impl on_edge_created(source: Any, target: Any, `edge: Any) -> None {
    if not _is_enabled() {
        return;
    }
    if not source.persistent {
        return;
    }
    root_anchor = _get_root_anchor(source);
    if root_anchor is None {
        return;
    }
    import from jaclang.runtimelib.topology_index { TopologyIndex }
    idx = root_anchor.get_topology_index();
    if not isinstance(idx, TopologyIndex) {
        idx = TopologyIndex();
    }
    # Track cross-root ownership
    if target.root and target.root != root_anchor.id {
        idx.node_owners[str(target.id)] = target.root;
    }
    # Add edge with MRO fan-out (populates both forward and reverse entries)
    src_mro = _get_type_mro(source.archetype);
    tgt_mro = _get_type_mro(target.archetype);
    idx.add_edge(source.id, target.id, tgt_mro, _type_name(`edge.archetype), src_mro);
    if `edge.is_undirected {
        idx.add_edge(
            target.id, source.id, src_mro, _type_name(`edge.archetype), tgt_mro
        );
    }
    root_anchor.set_topology_index(idx);
}

"""Called when an edge is destroyed."""
impl on_edge_destroyed(source: Any, target: Any, `edge: Any) -> None {
    if not _is_enabled() {
        return;
    }
    if not source.persistent {
        return;
    }
    root_anchor = _get_root_anchor(source);
    if root_anchor is None {
        return;
    }
    import from jaclang.runtimelib.topology_index { TopologyIndex }
    idx = root_anchor.get_topology_index();
    if not isinstance(idx, TopologyIndex) {
        return;
    }
    idx.remove_edge(source.id, target.id);
    if `edge.is_undirected {
        idx.remove_edge(target.id, source.id);
    }
    root_anchor.set_topology_index(idx);
}

"""Called when a node is saved/persisted."""
impl on_node_saved(node_anchor: Any) -> None {
    # SAM builds index at edge-creation time, no action needed on save
    ;
}

"""Called when a node is destroyed."""
impl on_node_destroyed(node_anchor: Any) -> None {
    if not _is_enabled() {
        return;
    }
    if not node_anchor.persistent or node_anchor.root is None {
        return;
    }
    root_anchor = _get_root_anchor(node_anchor);
    if root_anchor is None {
        return;
    }
    import from jaclang.runtimelib.topology_index { TopologyIndex }
    idx = root_anchor.get_topology_index();
    if not isinstance(idx, TopologyIndex) {
        return;
    }
    idx.remove_node(node_anchor.id);
    root_anchor.set_topology_index(idx);
}

"""Try to extract the type name from a filter lambda."""
impl _extract_type_name_from_filter(filt: (Callable | None)) -> (str | None) {
    if filt is None {
        return None;
    }
    try {
        import from jaclang.jac0core.archetype { Archetype }
        if isinstance(filt, Archetype) {
            return `type(filt).__name__;
        }
    } except Exception {
        ;
    }
    try {
        closure = inspect.getclosurevars(filt);
        for val in `list(closure.nonlocals.values()) + `list(
            closure.globals.values()
        ) {
            if isinstance(val, `type) {
                import from jaclang.jac0core.archetype { Archetype as Arch }
                if issubclass(val, Arch) {
                    return val.__name__;
                }
            }
        }
    } except Exception {
        ;
    }
    return None;
}

"""Use the SAM to resolve which node UUIDs survive type filters."""
impl plan_query(path: Any) -> (set[UUID] | None) {
    if not _is_enabled() {
        return None;
    }
    if not path.origin {
        return None;
    }
    origin_anchor = path.origin[0].__jac__;
    if not origin_anchor.persistent {
        return None;
    }
    root_anchor = _get_root_anchor(origin_anchor);
    if root_anchor is None {
        return None;
    }
    import from jaclang.runtimelib.topology_index { TopologyIndex }
    idx = root_anchor.get_topology_index();
    if not isinstance(idx, TopologyIndex) or len(idx) == 0 {
        return None;
    }
    chain: list[tuple[(str | None), (str | None), int]] = [];
    destinations = path.destinations[:-1] if path.edge_only else path.destinations;
    for dest in destinations {
        edge_type = _extract_type_name_from_filter(dest.`edge);
        node_type = _extract_type_name_from_filter(dest.nd);
        chain.append((edge_type, node_type, dest.direction.value));
    }
    if not chain {
        return None;
    }
    origin_ids = {nd.__jac__.id for nd in path.origin};
    return idx.resolve_chain(origin_ids, chain);
}

"""Load nodes by UUID set via bulk fetch. Only loads matching nodes."""
impl batch_load_nodes(node_ids: set[UUID]) -> list[Any] {
    import from jaclang { JacRuntimeInterface as Jac }
    ctx = Jac.get_context();
    import from jaclang.jac0core.archetype { NodeAnchor }

    # Bulk fetch only the matching anchors (single SQL query for L3)
    anchors = ctx.mem.bulk_get(node_ids);

    result = [];
    for (nid, anchor) in anchors.items() {
        if (
            isinstance(anchor, NodeAnchor)
            and anchor.archetype
            and Jac.check_read_access(anchor)
        ) {
            result.append(anchor.archetype);
        }
    }
    return result;
}

"""Extract a QueryFilter from a filter lambda by walking back to the UniIR AST."""
impl extract_query_filter(filt: (Callable | None)) -> Any {
    if filt is None {
        return None;
    }
    try {
        import from jaclang.runtimelib.query_filter {
            CompareOp, Predicate, QueryFilter
        }

        # Map Token.name strings to CompareOp enum values
        op_map = {
            'EE': CompareOp.EQ,
            'NE': CompareOp.NE,
            'LT': CompareOp.LT,
            'GT': CompareOp.GT,
            'LTE': CompareOp.LE,
            'GTE': CompareOp.GE,
            'KW_IN': CompareOp.IN,
            'KW_NIN': CompareOp.NOT_IN
        };

        code = getattr(filt, '__code__', None);
        if code is None {
            return None;
        }
        filename = code.co_filename;
        first_line = code.co_firstlineno;

        # Access the UniIR module hub at runtime
        import from jaclang.jac0core.runtime { JacRuntime }
        program = JacRuntime.get_program();
        if program is None or program.mod is None {
            return None;
        }
        hub = program.mod.hub;
        if filename not in hub {
            return None;
        }
        module = hub[filename];

        # Find the FilterCompr node at the matching source line
        import from jaclang.jac0core.unitree { FilterCompr }
        filter_nodes = module.get_all_sub_nodes(FilterCompr);
        target_fc = None;
        for fc in filter_nodes {
            if fc.loc.first_line == first_line {
                target_fc = fc;
                break;
            }
        }
        if target_fc is None {
            return None;
        }

        # Extract type name from f_type
        type_name: (str | None) = None;
        if target_fc.f_type is not None {
            import from jaclang.jac0core.unitree { Name }
            if isinstance(target_fc.f_type, Name) {
                type_name = target_fc.f_type.value;
            }
        }

        # Extract predicates from compares
        predicates: list = [];
        import from jaclang.jac0core.unitree {
            CompareExpr, Name as NameNode, Int, Float, String, Bool, Null
        }
        for cmp in target_fc.compares {
            if not isinstance(cmp, CompareExpr) {
                continue;
            }
            # left must be a simple Name (field reference)
            if not isinstance(cmp.left, NameNode) {
                continue;
            }
            field_name = cmp.left.value;

            # Must have at least one op and one right-hand value
            if not cmp.ops or not cmp.rights {
                continue;
            }
            op_token = cmp.ops[0];
            right_expr = cmp.rights[0];

            # Map the operator token to CompareOp
            op = op_map.get(op_token.name, None);
            if op is None {
                continue;
            }

            # Right-hand side must be a literal
            if isinstance(right_expr, (Int, Float, String, Bool, Null)) {
                value = right_expr.lit_value;
            } else {
                # Non-literal RHS — skip this predicate
                continue;
            }

            predicates.append(Predicate(field_name=field_name, op=op, value=value));
        }

        if not type_name and not predicates {
            return None;
        }

        return QueryFilter(type_name=type_name, predicates=predicates);
    } except Exception {
        # Any failure → graceful fallback
        return None;
    }
}

"""Load nodes with predicate pushdown — uses filtered_bulk_get when predicates available."""
impl filtered_batch_load_nodes(node_ids: set[UUID], query_filter: Any = None) -> list[Any] {
    import from jaclang { JacRuntimeInterface as Jac }
    ctx = Jac.get_context();
    import from jaclang.jac0core.archetype { NodeAnchor }

    # Use filtered_bulk_get if we have predicates to push down
    if query_filter is not None and query_filter.predicates {
        anchors = ctx.mem.filtered_bulk_get(node_ids, query_filter.predicates);
    } else {
        anchors = ctx.mem.bulk_get(node_ids);
    }

    result = [];
    for (nid, anchor) in anchors.items() {
        if (
            isinstance(anchor, NodeAnchor)
            and anchor.archetype
            and Jac.check_read_access(anchor)
        ) {
            result.append(anchor.archetype);
        }
    }
    return result;
}
