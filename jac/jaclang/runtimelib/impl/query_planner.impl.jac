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


def _stream_from_mirror(
    mem: Session,
    q: GraphQuery,
    ids: list[UUID],
    resident: dict,
    mrows: list,
    fields: tuple
) -> (list[Anchor] | None) {
    # Exact ACL fast path over mirror scalars, replicating
    # check_access_level's read decision for rows WITHOUT per-anchor
    # specific grants: owner passes; otherwise the per-root contribution is
    # rc = root.access.roots.check(user) which OVERRIDES, else
    # max(anchor.all, root.all); readable iff level >= 0 (> NO_ACCESS).
    # Rows WITH specifics (acl_spec) take the full per-row path via
    # batch_get + _acl_read_ok. System root / unauthenticated contexts keep
    # the generic path entirely.
    import from jaclang.jac0core.runtime { JacRuntimeInterface }
    import from jaclang.runtimelib.streamnode { StreamNode }
    try {
        jctx = JacRuntimeInterface.get_context();
    } except Exception {
        return None;
    }
    ur = jctx?.user_root;
    gated = _acl_gated();
    if gated and ur is None {
        return None;
    }
    # anchors owned by the SHARED root carry runtime-level floor semantics
    # (CONNECT floor, resolver-driven) that live outside the access blobs;
    # never fast-path them - route through the full per-row check below.
    shared_id = None;
    try {
        import from jaclang.jac0core.runtime { _shared_root_resolver }
        sr = _shared_root_resolver[1];
        if isinstance(sr, str) {
            shared_id = UUID(sr);
        } elif _shared_root_resolver[0] is not None {
            srid = _shared_root_resolver[0]();
            if isinstance(srid, str) {
                shared_id = UUID(srid);
            }
        }
    } except Exception {
        shared_id = None;
    }
    by_id: dict = {};
    for r in mrows {
        by_id[r[0]] = r;
    }
    # prefetch distinct owner roots once (real anchors; ~#users, cheap)
    root_ids = list({r[1] for r in mrows if r[1] is not None});
    roots = mem.batch_get(root_ids) if (gated and root_ids) else {};
    ur_key = str(ur.id) if ur is not None else '';
    root_contrib: dict = {};
    for (rid, ra) in roots.items() {
        rc = ra.access.roots.check(ur_key);
        root_contrib[rid] = (
            rc.value if rc is not None else None,
            ra.access.all.value
        );
    }
    specials: list[UUID] = [];
    picked: dict = {};
    import from jaclang.runtimelib.store { intern_uuid }
    for r in mrows {
        # normalise driver differences: the pure-Python driver returns uuid
        # columns as strings and psycopg returns UUID objects; key everything
        # by interned UUIDs or the final assembly misses picked rows
        aid = intern_uuid(r[0]);
        root_id = intern_uuid(r[1]) if r[1] else None;
        acl_all = int(r[2]) if r[2] is not None else -1;
        acl_spec = (r[3] is True) or r[3] == 't';
        frag = r[4];
        if gated {
            if acl_spec or (shared_id is not None and root_id == shared_id) {
                specials.append(aid);
                continue;
            }
            if ur is not None and (root_id == ur.id or aid == ur.id) {
                ;   # owner (or the caller's own root): WRITE
            } else {
                (rc, rall) = root_contrib.get(root_id, (None, -1));
                level = rc if rc is not None else max(acl_all, int(rall));
                if level < 0 {
                    continue;
                }
            }
        }
        anchor = NodeAnchor.__new__(NodeAnchor);
        ad = anchor.__dict__;
        ad['id'] = aid;
        ad['root'] = root_id;
        ad['persistent'] = True;
        ad['hash'] = 1;
        ad['edges'] = [];
        ad['version'] = 0;
        fvals: dict = {};
        for (i, f) in enumerate(fields) {
            fvals[str(f)] = r[5 + i];
        }
        ad['archetype'] = StreamNode(fvals, anchor, frag);
        picked[aid] = anchor;
    }
    if specials {
        # full-fidelity fallback for rows carrying per-anchor grants
        got = mem.batch_get(specials);
        for sid in specials {
            sa = got.get(sid);
            if sa is not None and sa.is_populated() and _acl_read_ok(sa) {
                picked[sid] = sa;
            }
        }
    }
    out: list[Anchor] = [];
    for i in ids {
        if (ra := resident.get(i)) is not None {
            if ra.is_populated() and ra.archetype is not None
                and (not gated or _acl_read_ok(ra)) {
                out.append(ra);
            }
            continue;
        }
        if (pa := picked.get(i)) is not None {
            out.append(pa);
        }
    }
    if q.slc is not None {
        out = out[q.slc];
    }
    return out;
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
    # R1/R2/R4 mirror fast path: single-class final hop with a ready mirror
    # serves (proof fields + prebuilt fragment + ACL scalars) from typed
    # columns - no props parse, no Permission objects. Any miss falls
    # through to the generic path below.
    nd_last = q.hops[-1].nd if q.hops else None;
    if (
        need
        and isinstance(nd_last, type)
        and _stream_class_ok(
            getattr(nd_last, '__module__', ''), getattr(nd_last, '__name__', '')
        )
        and hasattr(store, 'ensure_mirror')
        and store.ensure_mirror(nd_last)
    ) {
        fields = getattr(type(wlk), '__jac_stream_fields__', ()) or ();
        mrows = store.load_mirror_rows(nd_last, need, tuple(fields));
        if mrows is not None {
            out2 = _stream_from_mirror(mem, q, ids, resident, mrows, fields);
            if out2 is not None {
                return out2;
            }
        }
    }
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


impl _try_stream_fused(mem: Session, q: GraphQuery) -> (list[Anchor] | None) {
    # R3: one statement for traversal + mirror fetch. Eligibility mirrors
    # _try_stream plus: single-class final hop with NO node predicates and NO
    # registered subtypes beyond the class itself (mirror membership must
    # equal the polymorphic type test exactly), and a ready mirror whose
    # columns cover the proof fields.
    import os;
    if os.environ.get('JAC_STREAM', '1').lower() in ('0', 'off', 'false') {
        return None;
    }
    import from jaclang.jac0core.osp_kernel { _current_scope }
    scope = _current_scope();
    wlk = scope.wlk if scope is not None else None;
    fields = getattr(type(wlk), '__jac_stream_fields__', None)
        if wlk is not None else None;
    if fields is None or q.edges_only or q.from_visit or not q.hops {
        return None;
    }
    store = mem.store;
    if store is None or not hasattr(store, 'mirror_info') {
        return None;
    }
    last = q.hops[-1];
    nd_last = last.nd;
    if not isinstance(nd_last, type) or last.preds {
        return None;
    }
    tname_last = getattr(nd_last, '__name__', '');
    if not _stream_class_ok(getattr(nd_last, '__module__', ''), tname_last) {
        return None;
    }
    try {
        subs = [
            t
            for t in store.subtype_names(tname_last)
            if t != tname_last
        ];
        if subs {
            return None;   # polymorphic hierarchy: membership != type test
        }
    } except Exception {
        return None;
    }
    if not store.ensure_mirror(nd_last) {
        return None;
    }
    info = store.mirror_info(nd_last);
    if info is None {
        return None;
    }
    fcols: list = [];
    for f in fields {
        c = info['cols'].get(str(f));
        if c is None {
            return None;
        }
        fcols.append(c);
    }
    cq = compile_query(
        q, len(q.hops), mirror={'table': info['table'], 'fcols': fcols}
    );
    if cq.residual {
        return None;
    }
    # split origins exactly like _resolve_pairs
    origins = _origin_anchors(q);
    local: dict[UUID, Anchor] = {};
    sql_ids: list[UUID] = [];
    mem_origins: list[Anchor] = [];
    for oanch in origins {
        if oanch.persistent {
            sql_ids.append(oanch.id);
        } else {
            mem_origins.append(oanch);
        }
        local[oanch.id] = oanch;
    }
    mem.read_barrier();
    cq.params['origin'] = [str(i) for i in sql_ids];
    import from jaclang.runtimelib.store { intern_uuid }
    ids: list[UUID] = [];
    seen_ids: set[UUID] = set();
    mrows: list = [];
    resident: dict = {};
    try {
        raw = store.rows(cq.sql, cq.params) if sql_ids else [];
    } except Exception as e {
        logger.warning(f"fused stream query failed (falling back): {e}");
        return None;
    }
    for r in raw {
        nid = intern_uuid(r[0]);
        if nid in seen_ids {
            continue;
        }
        seen_ids.add(nid);
        if nid in mem._deleted {
            continue;
        }
        a = local.get(nid) or mem.__mem__.get(nid);
        if a is not None {
            resident[nid] = a;
        } else {
            mrows.append(r);
        }
        ids.append(nid);
    }
    # session-only origins traverse the in-memory overlay, same as the
    # generic path; their results are resident by construction
    for (a, e) in _walk_memory(mem_origins, q, len(q.hops)) {
        if a.id in seen_ids or a.id in mem._deleted {
            continue;
        }
        seen_ids.add(a.id);
        resident[a.id] = a;
        ids.append(a.id);
    }
    return _stream_from_mirror(mem, q, ids, resident, mrows, fields);
}


impl resolve_query(mem: Session, q: GraphQuery) -> list[Anchor] {
    if not q.origin {
        return [];
    }
    if (fused := _try_stream_fused(mem, q)) is not None {
        return fused;
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
