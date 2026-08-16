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


def _shared_root_id -> (UUID | None) {
    # The shared root's id, or None when no resolver is registered (library /
    # CLI runs, where root.shared IS the caller's root).
    try {
        import from jaclang.jac0core.runtime { _shared_root_resolver }
        sr = _shared_root_resolver[1];
        if isinstance(sr, str) {
            return UUID(sr);
        }
        if _shared_root_resolver[0] is not None {
            srid = _shared_root_resolver[0]();
            if isinstance(srid, str) {
                return UUID(srid);
            }
        }
    } except Exception {
        return None;
    }
    return None;
}


# --- JAC_SQL_ACL: the read decision as a SQL predicate -----------------------
# check_access_level (jac0core/impl/runtime.impl.jac) decides, for caller root
# U and a persistent anchor with no custom __jac_access__:
#
#   owner (U == anchor.root, or U IS the anchor)      -> WRITE
#   else L = max(anchor.access.all, root.access.all)
#        if root.access.roots[U]   exists: L = it     (OVERRIDES - can lower)
#        if anchor.access.roots[U] exists: L = it     (OVERRIDES - can lower)
#   readable iff L >= 0
#
# The per-root half of that is anchor-INDEPENDENT, which is what makes this
# expressible without joining anything. For a fixed U every owner root falls
# into exactly one of three classes:
#
#   rc >= 0, or rc absent and root.all >= 0  -> EVERY row under it is readable
#   rc < 0                                   -> NO row under it is readable
#   rc absent and root.all < 0               -> reduces to anchor.acl_all >= 0
#
# (rc = root.access.roots[U]; the classes are disjoint). So two uuid arrays
# carry the whole root contribution and the mirror's own acl_all column
# carries the rest - no root mirror table, no per-row jsonb extraction, and
# no `anchors` join, which matters because the endpoint-column LATERAL exists
# precisely to have removed that join.
#
# Rows the predicate cannot judge from mirror scalars - those carrying
# per-anchor grants (acl_spec) and those owned by the shared root - are
# ADMITTED unconditionally and re-checked in python by the unchanged
# `specials` path. Over-admission is sound; under-admission would not be.
#
# CASE, not an AND/OR chain, specifically for NULL root_id: a NULL condition
# is "not matched" and falls through to the acl_all arm, which is what
# check_access_level does (`if to.root and ...`). The OR form would evaluate
# to NULL and silently drop the row.
#
# Arm ORDER is load-bearing: owner first, because an anchor under the caller's
# own root is WRITE even if it carries a self-revoke in its own grant map.
glob _acl_sql_engaged = [False],
     _ACL_SQL_CASE = (
         'CASE WHEN %M%.root_id = CAST(:acl_self AS uuid) THEN true'
         + ' WHEN %M%.acl_spec THEN true'
         + ' WHEN %M%.root_id = CAST(:acl_shared AS uuid) THEN true'
         + ' WHEN %M%.root_id = ANY(CAST(:acl_open AS uuid[])) THEN true'
         + ' WHEN %M%.root_id = ANY(CAST(:acl_closed AS uuid[])) THEN false'
         + ' ELSE %M%.acl_all >= 0 END'
     ),
     # One indexed pass over Root anchors (idx_anchors_kind_type), narrowed to
     # the roots that actually say something about this caller - on an app that
     # only ever calls grant() (littleX) it returns zero rows. Runs on the main
     # connection, so it shares the request's transaction and therefore its
     # snapshot with the mirror query it parameterises.
     #
     # jsonb_typeof guards both int casts for the same reason the mirror's
     # acl_all trigger expression does: a legacy or hand-written blob holding
     # "READ" instead of 0 would otherwise raise mid-request. `->> ... IS NOT
     # NULL` rather than the `?` containment operator, deliberately - `?`
     # collides with placeholder scanning in one of the two drivers.
     _ACL_ROOTS_SQL = (
         "SELECT a.id, CASE WHEN jsonb_typeof("
         + "a.props->'access'->'roots'->'anchors'->CAST(:acl_u AS text)"
         + ") = 'number' THEN (a.props->'access'->'roots'->'anchors'->>"
         + "CAST(:acl_u AS text))::int END, CASE WHEN jsonb_typeof("
         + "a.props->'access'->'all') = 'number' THEN "
         + "(a.props->'access'->>'all')::int ELSE -1 END "
         + "FROM anchors a WHERE a.kind = 'NodeAnchor' AND a.arch_type = 'Root' "
         + "AND (a.props->'access'->'roots'->'anchors'->>CAST(:acl_u AS text) "
         + "IS NOT NULL OR jsonb_typeof(a.props->'access'->'all') = 'number')"
     );


def _acl_sql_ctx(mem: Session) -> (dict | None) {
    # -> {'sql': <CASE text, %M% = mirror alias>, 'params': {...}} or None,
    # None meaning "leave the ACL decision in python exactly as before". Every
    # failure mode returns None, so the flag can only ever add a filter that
    # agrees with the python one or fall back to it wholesale.
    import os;
    if os.environ.get('JAC_SQL_ACL', '0').strip().lower()
        not in ('1', 'on', 'true') {
        return None;
    }
    if not _acl_gated() {
        return None;   # system root / unauthenticated: no filtering at all
    }
    import from jaclang.jac0core.runtime { JacRuntimeInterface }
    try {
        jctx = JacRuntimeInterface.get_context();
    } except Exception {
        return None;
    }
    ur = jctx?.user_root;
    store = mem.store;
    if ur is None or store is None or not hasattr(store, 'rows') {
        return None;
    }
    u = str(ur.id);
    # Flush first: the caller's own uncommitted grants have to be inside the
    # transaction (and through the mirror triggers) before either this
    # prefetch or the query it parameterises reads anything, or a walker
    # could fail to see a permission it just granted itself.
    mem.read_barrier();
    open_ids: list = [];
    closed_ids: list = [];
    try {
        for r in store.rows(_ACL_ROOTS_SQL, {'acl_u': u}) {
            rid = str(r[0]);
            rc = int(r[1]) if r[1] is not None else None;
            rall = int(r[2]) if r[2] is not None else -1;
            if rc is not None {
                if rc >= 0 {
                    open_ids.append(rid);
                } else {
                    closed_ids.append(rid);
                }
            } elif rall >= 0 {
                open_ids.append(rid);
            }
        }
    } except Exception as e {
        logger.warning(
            f"sql-acl root prefetch failed (falling back to the python "
            f"check): {e}"
        );
        return None;
    }
    shared = _shared_root_id();
    # Every other exit from this function is a SILENT fallback to the python
    # check, which is exactly what makes "is the flag actually doing anything?"
    # unanswerable from the outside. Say so once per process on the way in.
    if not _acl_sql_engaged[0] {
        _acl_sql_engaged[0] = True;
        logger.info(
            "JAC_SQL_ACL engaged: mirror reads now carry the access predicate "
            "as SQL (rows with per-anchor grants and shared-root rows are "
            "still re-checked in python)"
        );
    }
    # ponytail: recomputed per graph query rather than memoised. One indexed
    # pass over ~#users rows that returns nothing at all unless somebody
    # granted at root level, versus a memo whose invalidation surface is the
    # whole transaction lifecycle (commit clears _txn_changed, rollback and
    # _recover_conflict rewind it, _ensure_txn can downgrade the isolation
    # and take a NEW snapshot mid-request). Memoise it keyed on a snapshot
    # sequence added to Session if this ever shows up in a profile.
    return {
        'sql': _ACL_SQL_CASE,
        'params': {
            'acl_self': u,
            'acl_shared': str(shared) if shared is not None else None,
            'acl_open': open_ids,
            'acl_closed': closed_ids
        }
    };
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
    cq = compile_query(q, upto, promotions=getattr(store, 'promotions', {}));
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
    fields: tuple,
    sql_filtered: bool = False
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
    shared_id = _shared_root_id();
    by_id: dict = {};
    for r in mrows {
        by_id[r[0]] = r;
    }
    # prefetch distinct owner roots once (real anchors; ~#users, cheap).
    # sql_filtered: the query already applied the exact same rule as a WHERE
    # (see _acl_sql_ctx), so there is nothing left for the per-root
    # contribution to decide and this whole batch_get disappears.
    root_ids = list({r[1] for r in mrows if r[1] is not None});
    roots = mem.batch_get(root_ids)
        if (gated and root_ids and not sql_filtered) else {};
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
    import json;
    import from jaclang.runtimelib.store { intern_uuid }
    # The mirror's f_* columns are jsonb, selected AS TEXT by both feeders
    # (store.load_mirror_rows and the fused sqlcompile SELECT), so every row
    # carries each field's JSON *text*. Decode it back to the value the
    # props path would have produced - without this a str field reaches the
    # walker still quoted ('"Ada"') and an int reaches it as '42'.
    jload = json.loads;
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
            } elif not sql_filtered {
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
            raw = r[5 + i];
            fvals[str(f)] = jload(raw) if raw is not None else None;
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
    cq = compile_query(q, len(q.hops), promotions=getattr(store, 'promotions', {}));
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


impl _try_stream_fused(
    mem: Session, q: GraphQuery, use_pipe: bool = True
) -> (list[Anchor] | None) {
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
    mirror_spec: dict = {'table': info['table'], 'fcols': fcols};
    # JAC_SQL_ACL: push the read decision into the mirror join / LATERAL. It
    # has to be decided HERE, before compile_query, because the predicate must
    # sit INSIDE the per-source LATERAL - i.e. before its LIMIT - or rejected
    # rows keep eating the fetch cap, which is the whole reason `slack`
    # exists. None = unchanged behaviour, python decides.
    acl = _acl_sql_ctx(mem);
    if acl is not None {
        mirror_spec['acl'] = acl['sql'];
        mirror_spec['acl_params'] = acl['params'];
    }
    pipe = getattr(type(wlk), '__jac_stream_pipeline__', None) if use_pipe else None;
    limit_active = False;
    if (
        pipe is not None
        and len(pipe) == 3
        and not mem._dirty
        and q.slc is None
        and q.hops[-1].only is None
    ) {
        ocol = info['cols'].get(str(pipe[0]));
        if ocol is not None {
            # distributed top-K: the walker's merged sort+[:K] only ever
            # needs each source's top-K under the same (field, traversal)
            # order. Fetch top-(K+slack); the assembly below falls back to
            # an unlimited rerun if drops exceed the slack.
            mirror_spec['order_col'] = ocol;
            mirror_spec['desc'] = bool(pipe[1]);
            mirror_spec['limit'] = int(pipe[2]);
            # Slack sizing. With the ACL in python the filter runs AFTER the
            # LATERAL's LIMIT, so a page whose top rows are all unreadable can
            # lose true top-K items off the fetched prefix - hence a slack of
            # a whole extra K (min 40). With the ACL in SQL the filter is
            # inside the LIMIT and the only residual drops are the rows the
            # predicate deliberately over-admits for python to re-check
            # (per-anchor grants, shared-root ownership) plus session-deleted
            # ids, so a small constant covers it. The unlimited-rerun backstop
            # below is what makes ANY value here safe; it is not an
            # optimisation, it is the correctness net, and it stays.
            _slack_dflt = 8 if acl is not None else max(40, int(pipe[2]) * 2);
            mirror_spec['slack'] = int(
                os.environ.get('JAC_ACL_SLACK', str(_slack_dflt))
            );
            limit_active = True;
            # R5: ask the store for a denormalised endpoint column on the
            # final hop's edge, which lets the compiler walk the last hop as
            # a per-source index range scan instead of joining `anchors`
            # (see PgStore.ensure_mirror_endpoint). Only for a plain OUTGOING
            # hop with no edge predicates - anything else is not expressible
            # as one column, and the flat join stays the answer. The hop's
            # edge type is passed when it names one ([->:Post:->]) and left
            # empty when it does not ([-->(?:Tweet)], the common case); the
            # store derives and verifies it from the data either way.
            if (
                last.dir == 2
                and not last.epreds
                and hasattr(store, 'ensure_mirror_endpoint')
            ) {
                epc = store.ensure_mirror_endpoint(
                    nd_last,
                    str(getattr(last.`edge, '__name__', ''))
                        if last.`edge is not None else '',
                    ocol
                );
                if epc is not None {
                    mirror_spec['endpoint_col'] = epc;
                }
            }
        }
    }
    cq = compile_query(
        q, len(q.hops), mirror=mirror_spec, promotions=getattr(store, 'promotions', {})
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
    drops = 0;
    for r in raw {
        nid = intern_uuid(r[0]);
        if nid in seen_ids {
            continue;
        }
        seen_ids.add(nid);
        if nid in mem._deleted {
            drops += 1;
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
    out = _stream_from_mirror(
        mem, q, ids, resident, mrows, fields, sql_filtered=acl is not None
    );
    if limit_active and out is not None {
        cap = mirror_spec['limit'] + mirror_spec['slack'];
        acl_drops = drops + (len(ids) - len(out));
        if len(raw) >= cap and acl_drops > mirror_spec['slack'] {
            # ACL/delete drops may have pushed true top-K items below the
            # fetched prefix: rerun this source unlimited (rare)
            out = _try_stream_fused(mem, q, False);
        }
    }
    return out;
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
