impl _acl_gated -> bool {
    import from jaclang.jac0core.runtime { JacRuntimeInterface }
    try {
        jctx = JacRuntimeInterface.get_context();
    } except Exception {
        return False;
    }
    ur = jctx?.user_root;
    return ur is not None and ur != jctx.system_root;
}


impl _acl_read_ok(anchor: Anchor) -> bool {
    import from jaclang.jac0core.archetype { AccessLevel }
    import from jaclang.jac0core.runtime { JacRuntimeInterface }
    level = JacRuntimeInterface.check_access_level(anchor);
    return level.value > AccessLevel.NO_ACCESS.value;
}


impl _prefetch_acl_roots(mem: Session, anchors: list[Anchor]) -> None {
    # check_access_level() reads the owner Root of each anchor to consult its
    # access blob. Left alone that is one single-row round trip per distinct
    # owner, every request, because the session cache starts cold - 53 serial
    # queries for a 2550-item feed. Warm them in one batch_get first; the ACL
    # code is untouched and simply finds them already resident. Pure prefetch:
    # same anchors fetched, same order of checks, same verdicts.
    roots: list[UUID] = [];
    seen: set[UUID] = set();
    for a in anchors {
        rid = a.root;
        if rid is None or rid in seen {
            continue;
        }
        seen.add(rid);
        if mem.__mem__.get(rid) is None {
            roots.append(rid);
        }
    }
    if roots {
        mem.batch_get(roots);
    }
}


impl _origin_anchors(q: GraphQuery) -> list[Anchor] {
    seen: set[UUID] = set();
    out: list[Anchor] = [];
    for arch in q.origin {
        oanch = arch?.__jac__;
        if isinstance(oanch, Anchor) and oanch.id not in seen {
            seen.add(oanch.id);
            out.append(oanch);
        }
    }
    return out;
}


impl _sql_pairs(
    mem: Session, origin_ids: list[UUID], q: GraphQuery, upto: int
) -> list[tuple[(UUID | None), (UUID | None)]] {
    store = mem.store;
    if store is None or not origin_ids {
        return [];
    }
    mem.read_barrier();
    cq = compile_query(q, upto);
    if cq.residual {
        logger.warning(
            f"graph query has non-pushable predicates at hops "
            f"{sorted(cq.residual.keys())}; they are re-checked on the "
            f"materialized results only"
        );
    }
    cq.params['origin'] = [str(i) for i in origin_ids];
    out: list[tuple[(UUID | None), (UUID | None)]] = [];
    for r in store.rows(cq.sql, cq.params) {
        nid = UUID(str(r[0])) if r[0] is not None else None;
        eid = UUID(str(r[1])) if r[1] is not None else None;
        out.append((nid, eid));
    }
    return out;
}


impl _edge_pair_for(e: EdgeAnchor, cur: Anchor, hop: QHop) -> (Anchor | None) {
    src = e.source;
    tgt = e.target;
    if src is None or tgt is None or e.archetype is None {
        return None;
    }
    other: (Anchor | None) = None;
    if hop.dir == 1 {
        if tgt.id == cur.id {
            other = src;
        } elif e.is_undirected and src.id == cur.id {
            other = tgt;
        }
    } elif hop.dir == 3 {
        if src.id == cur.id {
            other = tgt;
        } elif tgt.id == cur.id {
            other = src;
        }
    } else {
        if src.id == cur.id {
            other = tgt;
        } elif e.is_undirected and tgt.id == cur.id {
            other = src;
        }
    }
    if other is None {
        return None;
    }
    if hop.`edge is not None and not isinstance(e.archetype, hop.`edge) {
        return None;
    }
    for p in hop.epreds {
        if not p.matches(getattr(e.archetype, p.field, None)) {
            return None;
        }
    }
    return other if _hop_matches_node(other, hop) else None;
}


impl _hop_matches_node(anchor: Anchor, hop: QHop) -> bool {
    if not anchor.is_populated() or anchor.archetype is None {
        return False;
    }
    nd = hop.nd;
    if nd is not None {
        types = nd if isinstance(nd, tuple) else (nd, );
        for nt in types {
            if not isinstance(anchor.archetype, nt) {
                return False;
            }
        }
    }
    for p in hop.preds {
        if not p.matches(getattr(anchor.archetype, p.field, None)) {
            return False;
        }
    }
    want = hop.only_ids();
    return want is None or anchor.id in want;
}


impl _walk_memory(
    origins: list[Anchor], q: GraphQuery, upto: int
) -> list[tuple[Anchor, (EdgeAnchor | None)]] {
    frontier: list[Anchor] = list(origins);
    pairs: list[tuple[Anchor, (EdgeAnchor | None)]] = [(a, None) for a in origins];
    gated = _acl_gated();
    for hop in q.hops[:upto] {
        nxt: list[tuple[Anchor, (EdgeAnchor | None)]] = [];
        seen_edges: set[UUID] = set();
        for cur in frontier {
            if not isinstance(cur, NodeAnchor) or not cur.is_populated() {
                continue;
            }
            for e in list(cur.edges) {
                if e.id in seen_edges or not e.is_populated() {
                    continue;
                }
                other = _edge_pair_for(e, cur, hop);
                if other is not None {
                    if gated and not _acl_read_ok(other) {
                        continue;
                    }
                    seen_edges.add(e.id);
                    nxt.append((other, e));
                }
            }
        }
        pairs = nxt;
        seen_nodes: set[UUID] = set();
        frontier = [];
        for (a, _) in nxt {
            if a.id not in seen_nodes {
                seen_nodes.add(a.id);
                frontier.append(a);
            }
        }
    }
    return pairs;
}


def _resolve_pairs(
    mem: Session, q: GraphQuery, upto: int
) -> tuple[list[tuple[(UUID | None), (UUID | None)]], dict[UUID, Anchor]] {
    origins = _origin_anchors(q);
    local: dict[UUID, Anchor] = {};
    sql_ids: list[UUID] = [];
    mem_origins: list[Anchor] = [];
    for oanch in origins {
        if mem.store is not None and oanch.persistent {
            sql_ids.append(oanch.id);
        } else {
            mem_origins.append(oanch);
        }
        local[oanch.id] = oanch;
    }
    pairs = _sql_pairs(mem, sql_ids, q, upto);
    if upto == 0 {
        pairs = [(i, None) for i in sql_ids];
    }
    for (a, e) in _walk_memory(mem_origins, q, upto) {
        local[a.id] = a;
        if e is not None {
            local[e.id] = e;
        }
        pairs.append((a.id, e.id if e is not None else None));
    }
    return (pairs, local);
}


def _materialize_ids(
    mem: Session, ids: list[UUID], local: dict[UUID, Anchor]
) -> list[Anchor] {
    missing = [
        i
        for i in ids
        if i not in local
    ];
    fetched = mem.batch_get(missing) if missing else {};
    out: list[Anchor] = [];
    for i in ids {
        a = local.get(i) or fetched.get(i);
        if a is not None and a.is_populated() and a.archetype is not None {
            out.append(a);
        }
    }
    return out;
}


def _unique_nodes(pairs: list[tuple[(UUID | None), (UUID | None)]]) -> list[UUID] {
    seen: set[UUID] = set();
    out: list[UUID] = [];
    for (nid, _) in pairs {
        if nid is not None and nid not in seen {
            seen.add(nid);
            out.append(nid);
        }
    }
    return out;
}


impl resolve_query_prefix(mem: Session, q: GraphQuery, upto: int) -> list[UUID] {
    (pairs, _) = _resolve_pairs(mem, q, upto);
    return _unique_nodes(pairs);
}


glob _stream_class_cache: dict = {};


def _stream_class_ok(module_name: str, type_name: str) -> bool {
    key = (module_name, type_name);
    if (hit := _stream_class_cache.get(key)) is not None {
        return hit;
    }
    import from jaclang.runtimelib.serializer { Serializer }
    import from jaclang.jac0core.constructs { Archetype }
    cls = Serializer._get_class(module_name, type_name);
    ok = (
        cls is not None
        and getattr(cls, '__jac_access__', None)
            is getattr(Archetype, '__jac_access__', None)
    );
    _stream_class_cache[key] = ok;
    return ok;
}


impl _try_stream(
    mem: Session, q: GraphQuery, ids: list[UUID], local: dict[UUID, Anchor]
) -> (list[Anchor] | None) {
    # Zero-materialization path, gated on the compiler's stream proof: the
    # current walker's class carries __jac_stream_fields__ ONLY if
    # StreamProofPass proved every observation of chain results is trivial
    # (jid / proven scalar fields / list plumbing / report). Ids already in
    # the session (overlay) are served as their real resident anchors, so
    # read-your-writes is preserved; everything else becomes a slim
    # NodeAnchor + StreamNode built straight from the stored row - no
    # archetype construction, no edge stubs, no adjacency fetch.
    import os;
    if os.environ.get('JAC_STREAM', '1').lower() in ('0', 'off', 'false') {
        return None;
    }
    import from jaclang.jac0core.osp_kernel { _current_scope }
    scope = _current_scope();
    wlk = scope.wlk if scope is not None else None;
    if wlk is None
        or getattr(type(wlk), '__jac_stream_fields__', None) is None
        or q.edges_only or q.from_visit {
        return None;
    }
    store = mem.store;
    if store is None or not hasattr(store, 'load_props') {
        return None;
    }
    cq = compile_query(q, len(q.hops));
    if cq.residual {
        return None;   # residual predicates need materialized values
    }
    resident: dict = {};
    need: list[UUID] = [];
    for i in ids {
        a = local.get(i) or mem.__mem__.get(i);
        if a is not None {
            resident[i] = a;
        } elif i not in mem._deleted {
            need.append(i);
        }
    }
    mem.read_barrier();
    rows = store.load_props(need) if need else {};
    import from jaclang.runtimelib.serializer { Serializer }
    import from jaclang.runtimelib.streamnode { StreamNode }
    out: list[Anchor] = [];
    for i in ids {
        if (ra := resident.get(i)) is not None {
            if ra.is_populated() and ra.archetype is not None {
                out.append(ra);
            }
            continue;
        }
        row = rows.get(i);
        if row is None or row.kind != 'NodeAnchor' {
            continue;
        }
        arch_props = row.props.get('archetype');
        if not isinstance(arch_props, dict) {
            return None;   # unexpected row shape: whole query falls back
        }
        if not _stream_class_ok(row.arch_module, row.arch_type) {
            # class overrides __jac_access__ (or is unknown): its access hook
            # may read instance fields, which requires real materialization
            return None;
        }
        anchor = NodeAnchor.__new__(NodeAnchor);
        ad = anchor.__dict__;
        ad['id'] = row.id;
        ad['root'] = row.root_id;
        ad['persistent'] = True;
        ad['hash'] = 1;
        ad['access'] = Serializer._deserialize_permission(
            row.props.get('access')
        );
        ad['edges'] = [];
        ad['version'] = 0;
        ad['_row_version'] = row.version;
        ad['_sn_arch_type'] = row.arch_type;
        ad['archetype'] = StreamNode(arch_props, anchor);
        out.append(anchor);
    }
    if _acl_gated() {
        _prefetch_acl_roots(mem, out);
        out = [
            a
            for a in out
            if _acl_read_ok(a)
        ];
    }
    if q.slc is not None {
        out = out[q.slc];
    }
    return out;
}


impl resolve_query(mem: Session, q: GraphQuery) -> list[Anchor] {
    if not q.origin {
        return [];
    }
    (pairs, local) = _resolve_pairs(mem, q, len(q.hops));
    ids = _unique_nodes(pairs);
    if (streamed := _try_stream(mem, q, ids, local)) is not None {
        return streamed;
    }
    out = _materialize_ids(mem, ids, local);
    if _acl_gated() {
        _prefetch_acl_roots(mem, out);
        out = [
            a
            for a in out
            if _acl_read_ok(a)
        ];
    }
    if q.slc is not None {
        out = out[q.slc];
    }
    return out;
}


impl resolve_query_edges(mem: Session, q: GraphQuery) -> list[Anchor] {
    if not q.origin or not q.hops {
        return [];
    }
    (pairs, local) = _resolve_pairs(mem, q, len(q.hops));
    edge_ids: list[UUID] = [];
    node_of: dict[UUID, UUID] = {};
    seen: set[UUID] = set();
    for (nid, eid) in pairs {
        if eid is None or eid in seen {
            continue;
        }
        seen.add(eid);
        edge_ids.append(eid);
        if nid is not None {
            node_of[eid] = nid;
        }
    }
    edges = _materialize_ids(mem, edge_ids, local);
    if _acl_gated() {
        # both the edges and the nodes they land on get access-checked below
        _prefetch_acl_roots(mem, edges);
        _prefetch_acl_roots(mem, _materialize_ids(mem, list(node_of.values()), local));
        kept: list[Anchor] = [];
        for ea in edges {
            if not _acl_read_ok(ea) {
                continue;
            }
            nid = node_of.get(ea.id);
            if nid is not None {
                ends = _materialize_ids(mem, [nid], local);
                if not ends or not _acl_read_ok(ends[0]) {
                    continue;
                }
            }
            kept.append(ea);
        }
        edges = kept;
    }
    if not q.from_visit {
        out_e: list[Anchor] = list(edges);
        if q.slc is not None {
            out_e = out_e[q.slc];
        }
        return out_e;
    }
    out: list[Anchor] = [];
    seen_nodes: set[UUID] = set();
    for ea in edges {
        out.append(ea);
        nid = node_of.get(ea.id);
        if nid is None or nid in seen_nodes {
            continue;
        }
        nodes = _materialize_ids(mem, [nid], local);
        if nodes {
            seen_nodes.add(nid);
            out.append(nodes[0]);
        }
    }
    if q.slc is not None {
        out = out[q.slc];
    }
    return out;
}
