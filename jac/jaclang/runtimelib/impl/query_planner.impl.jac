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


def _acl_sql_ctx(mem: Session, force: bool = False) -> (dict | None) {
    # -> {'sql': <CASE text, %M% = mirror alias>, 'params': {...}} or None,
    # None meaning "leave the ACL decision in python exactly as before". Every
    # failure mode returns None, so the flag can only ever add a filter that
    # agrees with the python one or fall back to it wholesale.
    # `force` skips the JAC_SQL_ACL env test and NOTHING else: acl_filter_ids
    # has no python path to fall back to (there are no objects to check), so
    # for it the predicate is the decision, not an optimisation of one.
    import os;
    if not force and os.environ.get('JAC_SQL_ACL', '1').strip().lower()
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
    if not _acl_sql_engaged[0] and not force {
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


impl acl_filter_ids(mem: Session, cls: (type | str), ids: list[str]) -> (set | None) {
    # T7b: the read verdict for an ID-LEVEL result - a closure that hands the
    # walker (hex, depth) pairs, or a zero-field projected hydration. Both
    # answer with ids alone, so there is no anchor for check_read_access to
    # look at; ask the archetype's mirror instead.
    #
    # -> the subset of `ids` that EXISTS in cls's mirror AND is readable, or
    # None meaning "cannot decide here" (no store, no mirror API, no mirror,
    # or gated with no ACL context). None is NOT "admit everything": the
    # caller must fall back to its own hydrated/legacy path, which carries the
    # python verdict. Ungated (system root / library run) still runs the
    # statement, with the predicate replaced by TRUE, because the EXISTENCE
    # half of the answer is owed either way - jobj_many() drops missing ids
    # and so must this.
    store = mem.store;
    # bound through getattr, not `store.x`: Store is a duck-typed backend here
    # (the pg store adds the mirror API), exactly as the rest of this module
    # treats it
    rowsf = getattr(store, 'rows', None);
    ensure = getattr(store, 'ensure_mirror', None);
    minfo = getattr(store, 'mirror_info', None);
    if rowsf is None or ensure is None or minfo is None
        or not isinstance(cls, type) or not ensure(cls) {
        return None;
    }
    gated = _acl_gated();
    ctx = _acl_sql_ctx(mem, True) if gated else None;
    if gated and ctx is None {
        return None;   # gated but the predicate is unavailable: cannot decide
    }
    pred = 'TRUE';
    spec = 'false';
    params: dict = {};
    if ctx is not None {
        pred = str(ctx['sql']).replace('%M%', 'm');
        # the two row classes _ACL_SQL_CASE admits unconditionally because it
        # cannot judge them from mirror scalars: per-anchor grants and rows
        # owned by the shared root. _stream_from_mirror re-checks exactly
        # these in python (its `specials` path) and so must we - the CASE's
        # over-admission is only sound WITH that re-check.
        spec = '(m.acl_spec OR m.root_id = CAST(:acl_shared AS uuid))';
        params = dict(ctx['params']);
    }
    params['ids'] = [str(UUID(i)) for i in ids];
    mem.read_barrier();
    sql = 'SELECT m.id, ' + spec + ' AS special FROM ' + str(minfo(cls)['table'])
        + ' m WHERE m.id = ANY(CAST(:ids AS uuid[])) AND (' + pred + ')';
    ok: set = set();
    specials: list = [];
    for r in rowsf(sql, params) {
        # .hex, no dashes - the ids the caller holds come from object_ref()
        h = str(r[0]).replace('-', '');
        if (r[1] is True) or r[1] == 't' {
            specials.append(h);
        } else {
            ok.add(h);
        }
    }
    if specials {
        # zero extra statements when there are none, which is every benchmark
        import from jaclang.jac0core.runtime { JacRuntimeInterface }
        for (i, o) in zip(specials, JacRuntimeInterface.get_objects_many(specials)) {
            if o is not None {
                ok.add(i);
            }
        }
    }
    return ok;
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


def _materialize_projected(
    mem: Session, ids: list[UUID], proj: tuple
) -> (list[Anchor] | None) {
    # C2: the compiler proved this chain's elements are observed only through
    # `proj`'s fields (+ jid / isinstance / truth), so hand the ids to the T6
    # path - proj_cache, then hydrate_projected off the mirror columns, then
    # the legacy per-id load for whatever the mirror cannot answer - instead
    # of decoding one anchor blob each. Order is preserved and a dropped id
    # is dropped exactly as _materialize_ids drops an unpopulated anchor.
    #
    # ACL: get_objects_many gives the FULL read verdict per id (the mirror
    # predicate inside hydrate_projected, check_read_access on every legacy
    # fallback) and answers None for a denied or unknown id, so the caller
    # must NOT re-run _acl_read_ok over the result: a projected anchor
    # deliberately carries no `access` scalar (hydrate_projected builds no
    # Permission), which is exactly why the verdict is applied where the
    # scalars are. Returning None here means the path did not run at all, and
    # the caller takes the untouched legacy path, ACL filter included.
    # ponytail: this ignores the walk's `local` dict and re-asks the session
    # for those ids; Session.get answers them from __mem__ with no round trip
    # (that is also what preserves read-your-writes), so the cost is a dict
    # lookup per resident id, not a fetch.
    import from jaclang.jac0core.runtime { JacRuntimeInterface }
    try {
        archs = JacRuntimeInterface.get_objects_many(
            [i.hex for i in ids], _proj=proj
        );
    } except Exception as e {
        logger.warning(f"projected chain hydration failed (falling back): {e}");
        return None;
    }
    out: list[Anchor] = [];
    for a in archs {
        an = getattr(a, '__jac__', None) if a is not None else None;
        if isinstance(an, Anchor) {
            out.append(an);
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
    # item #25: lowered visit walkers dispatch entry abilities on the
    # element's type; a mirror-backed stand-in must carry it like the
    # anchors-backed one does (the mirror is per-archetype, so the query's
    # terminal node type IS the row type)
    _tnd = q.hops[-1].nd if getattr(q, 'hops', None) else None;
    _tname = getattr(_tnd, '__name__', '') if isinstance(_tnd, type) else '';
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
        if _tname {
            ad['_sn_arch_type'] = _tname;
        }
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


# --- T6: projected hydration for compiler-stamped jobj / jobj_many ---------

class _Unloaded {
    # Stand-in for a field the compiler proved the walker never reads.
    # Dataclass `has` defaults are CLASS attributes, so without a per-instance
    # placeholder an unprojected read would silently answer the default (a
    # wrong VALUE); with it, every observation fails loud. repr stays inert
    # so logging/debugging an instance never trips it.
    def __init__(self: _Unloaded, name: str) {
        object.__setattr__(self, '_f', name);
    }
    def _bad(self: _Unloaded) -> None {
        raise RuntimeError(
            "projected field " + str(self._f) + " read outside the compiler's proof"
        );
    }
    def __bool__(self: _Unloaded) -> bool { self._bad(); return False; }
    def __eq__(self: _Unloaded, other: object) -> bool { self._bad(); return False; }
    def __lt__(self: _Unloaded, other: object) -> bool { self._bad(); return False; }
    def __hash__(self: _Unloaded) -> int { self._bad(); return 0; }
    def __int__(self: _Unloaded) -> int { self._bad(); return 0; }
    def __len__(self: _Unloaded) -> int { self._bad(); return 0; }
    def __iter__(self: _Unloaded) -> object { self._bad(); return iter(()); }
    def __str__(self: _Unloaded) -> str { self._bad(); return ''; }
    def __format__(self: _Unloaded, spec: str) -> str { self._bad(); return ''; }
    def __repr__(self: _Unloaded) -> str { return '<unloaded ' + str(self._f) + '>'; }
}


glob _unloaded_tmpl_cache: dict = {};


def _unloaded_template(cls: type, fields: tuple) -> dict {
    key = (cls, fields);
    if (hit := _unloaded_tmpl_cache.get(key)) is not None {
        return hit;
    }
    import from jaclang.runtimelib.typecache { field_names }
    tmpl: dict = {};
    for f in field_names(cls) {
        if str(f) not in fields {
            tmpl[str(f)] = _Unloaded(str(f));
        }
    }
    _unloaded_tmpl_cache[key] = tmpl;
    return tmpl;
}


impl hydrate_projected(
    mem: Session, cls: type, ids: list[UUID], fields: tuple
) -> tuple {
    # -> (built: {UUID: Archetype}, absent: [UUID]). Real `cls` instances
    # carrying ONLY `fields` (from the mirror's jsonb columns, decoded and
    # coerced exactly as the full path does) on a slim persistent NodeAnchor;
    # `absent` is every id the mirror could not answer with the same ACL
    # verdict as the full path (other archetype, missing, per-anchor grants,
    # shared-root rows, denied, NULL column) - the caller loads those the
    # legacy way, so the positional result is identical by construction.
    # ponytail: the ACL block below duplicates _stream_from_mirror's rather
    # than refactoring a parity-proven function mid-ladder; fold both onto
    # one helper as a follow-up.
    import sys;
    import json;
    import from jaclang.jac0core.runtime { JacRuntimeInterface }
    import from jaclang.runtimelib.serializer { Serializer }
    import from jaclang.runtimelib.typecache { get_field_types }
    import from jaclang.runtimelib.store { intern_uuid }
    if not fields {
        # T7: ZERO projected fields. The compiler proved the walker observes
        # these results only through `jid(x)` (plus isinstance / truth) -- the
        # id the caller already handed us -- so there is nothing to SELECT: no
        # load_mirror_rows, no decode, no bytes.
        # T7b (review RISK from T7): there is still a verdict to give. A
        # stand-in the requester may not read is a leak the projected path
        # never had, so ask the mirror who exists and is readable (ids only,
        # two statements when gated: the ACL root prefetch and the filter
        # itself) and hand everyone else back as `absent` -- the caller then
        # answers those the legacy way, with the full python verdict, exactly
        # as it does for a row the mirror cannot judge. A None verdict means
        # the mirror could not decide at all, so EVERY id goes back.
        allowed0 = acl_filter_ids(mem, cls, [u.hex for u in ids]);
        if allowed0 is None {
            return ({}, list(ids));
        }
        tmpl0 = _unloaded_template(cls, ());
        tname0 = str(cls.__name__);
        absent0: list = [];
        built0: dict = {};
        for uid in ids {
            if uid.hex not in allowed0 {
                absent0.append(uid);
                continue;
            }
            anchor0 = NodeAnchor.__new__(NodeAnchor);
            ad0 = anchor0.__dict__;
            ad0['id'] = uid;
            ad0['root'] = None;
            ad0['persistent'] = True;
            ad0['hash'] = 1;
            ad0['edges'] = [];
            ad0['version'] = 0;
            ad0['_sn_arch_type'] = tname0;
            arch0 = cls.__new__(cls);
            d0 = arch0.__dict__;
            d0.update(tmpl0);
            setattr(arch0, '__jac__', anchor0);
            ad0['archetype'] = arch0;
            built0[uid] = arch0;
        }
        if PROJECT_DEBUG {
            sys.stderr.write(
                'PROJECT-RT cls=' + tname0 + ' fields=() ids=' + str(len(ids))
                + ' rows=0 built=' + str(len(built0)) + ' absent='
                + str(len(absent0)) + ' bytes=0 acl=' + str(len(allowed0))
                + chr(10)
            );
        }
        return (built0, absent0);
    }
    nothing = ({}, list(ids));
    store = mem.store;
    if store is None or not hasattr(store, 'load_mirror_rows')
        or not hasattr(store, 'ensure_mirror') {
        return nothing;
    }
    if not _stream_class_ok(str(cls.__module__), str(cls.__name__)) {
        return nothing;
    }
    try {
        jctx = JacRuntimeInterface.get_context();
    } except Exception {
        return nothing;
    }
    ur = jctx?.user_root;
    gated = _acl_gated();
    if gated and ur is None {
        return nothing;
    }
    if not store.ensure_mirror(cls) {
        return nothing;
    }
    mem.read_barrier();
    mrows = store.load_mirror_rows(cls, ids, tuple(fields));
    if mrows is None {
        return nothing;
    }
    shared_id = _shared_root_id();
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
    ftypes = get_field_types(cls);
    tmpl = _unloaded_template(cls, tuple(str(f) for f in fields));
    jload = json.loads;
    tname = str(cls.__name__);
    built: dict = {};
    nbytes = 0;
    for r in mrows {
        aid = intern_uuid(r[0]);
        root_id = intern_uuid(r[1]) if r[1] else None;
        acl_all = int(r[2]) if r[2] is not None else -1;
        acl_spec = (r[3] is True) or r[3] == 't';
        if gated {
            if acl_spec or (shared_id is not None and root_id == shared_id) {
                continue;   # per-anchor grants / shared root: full path
            }
            if ur is not None and (root_id == ur.id or aid == ur.id) {
                ;   # owner (or the caller's own root)
            } else {
                (rc, rall) = root_contrib.get(root_id, (None, -1));
                level = rc if rc is not None else max(acl_all, int(rall));
                if level < 0 {
                    continue;   # denied: legacy path answers None (+diagnostic)
                }
            }
        }
        vals: dict = {};
        ok_row = True;
        for (i, f) in enumerate(fields) {
            raw = r[5 + i];
            if raw is None {
                ok_row = False;   # field absent from props: let the full path decide
                break;
            }
            nbytes += len(raw);
            v = Serializer._deserialize_value(jload(raw));
            tt = ftypes.get(str(f));
            if tt is not None {
                (cv, cok) = Serializer.coerce(v, tt);
                if cok {
                    v = cv;
                }
            }
            vals[str(f)] = v;
        }
        if not ok_row {
            continue;
        }
        anchor = NodeAnchor.__new__(NodeAnchor);
        ad = anchor.__dict__;
        ad['id'] = aid;
        ad['root'] = root_id;
        ad['persistent'] = True;
        ad['hash'] = 1;
        ad['edges'] = [];
        ad['version'] = 0;
        ad['_sn_arch_type'] = tname;
        arch = cls.__new__(cls);
        d = arch.__dict__;
        d.update(tmpl);
        d.update(vals);
        setattr(arch, '__jac__', anchor);
        ad['archetype'] = arch;
        built[aid] = arch;
    }
    absent = [i for i in ids if i not in built];
    if PROJECT_DEBUG {
        sys.stderr.write(
            'PROJECT-RT cls=' + tname + ' fields=' + str(tuple(fields))
            + ' ids=' + str(len(ids)) + ' rows=' + str(len(mrows))
            + ' built=' + str(len(built)) + ' absent=' + str(len(absent))
            + ' bytes=' + str(nbytes) + chr(10)
        );
    }
    return (built, absent);
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
                    # JAC_FUSED_FEED (sqlcompile._fused_feed_enabled): drive
                    # the statement from ONE ordered scan of the sort index
                    # and demote the traversal to a membership filter. Only
                    # worth it when there IS a traversal to demote - a
                    # single-hop query already reaches its one source's
                    # top-K through the (endpoint, sort) index directly, and
                    # the global form would only add a filter to it.
                    if (
                        os.environ.get('JAC_FUSED_FEED', '1').strip().lower()
                            in ('1', 'true', 'yes', 'on')
                        and len(q.hops) >= 2
                        and hasattr(store, 'ensure_mirror_order_index')
                        and store.ensure_mirror_order_index(nd_last, ocol)
                    ) {
                        mirror_spec['global_topk'] = True;
                    }
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


impl _pf_dbg(msg: str) -> None {
    import sys;
    print('ADJPREFETCH-RT ' + msg, file=sys.stderr, flush=True);
}


impl _adj_memo(mem: Session) -> (dict | None) {
    # T3's per-request adjacency memo lives on the ExecutionContext (a fresh
    # object per request, server.impl.jac) - NOT on the Session, which a
    # request SHARES with its parent context, and which would leak rows
    # across requests.
    #
    # Refused outright while this session has any write in flight: the same
    # `_dirty / _deleted / _txn_changed` triple session.impl.jac:730-734 uses
    # for "no writes in this txn". A write can change adjacency and the memo
    # would still answer from before it - refusal over staleness, in both
    # directions (fill and read), which is why both go through here.
    if not LOOP_PREFETCH {
        return None;
    }
    import from jaclang.jac0core.runtime { JacRuntimeInterface }
    if mem._dirty or mem._deleted or mem._txn_changed {
        if PREFETCH_DEBUG {
            _pf_dbg('memo off: writes in flight');
        }
        return None;
    }
    try {
        jctx = JacRuntimeInterface.get_context();
    } except Exception {
        if PREFETCH_DEBUG {
            _pf_dbg('memo off: no request context');
        }
        return None;
    }
    # 0904 default-on: the adjacency memo is intra-request state; a write
    # walker could attach an edge between the hint and the use, so only
    # proven read-only requests use it. (The _dirty/_deleted/_txn_changed
    # refusal above catches a write already in flight; this catches one
    # that has not landed yet.)
    if not jctx.request_read_only {
        if PREFETCH_DEBUG {
            _pf_dbg('memo off: request not proven read-only');
        }
        return None;
    }
    memo = getattr(jctx, 'adj_memo', None);
    if memo is None and PREFETCH_DEBUG {
        _pf_dbg('memo off: context has no adj_memo');
    }
    return memo;
}


impl _hop_key(dir: int, edge_type: any, node_type: any, epreds: any) -> tuple {
    # C1: the memo key CARRIES the edge predicate, so a filtered fill can
    # never answer an unfiltered (or differently filtered) reference to the
    # same (origin, dir, edge, node). `repr` of the value because the memo is
    # a plain dict: an unhashable or ill-behaved value degrades to a key that
    # does not match, i.e. a miss and the ordinary path - never a wrong hit.
    return (
        int(dir), edge_type, node_type,
        tuple((p.field, p.op, repr(p.value)) for p in (epreds or []))
    );
}


impl _memo_key(q: GraphQuery) -> (tuple | None) {
    # Only a single hop is memoizable. Node predicates and `only` (what
    # `x in [chain]` lowers to) narrow the row set AFTER the join, so a memo
    # entry could not answer them; edge predicates ride the key instead.
    if len(q.hops) != 1 {
        return None;
    }
    h = q.hops[0];
    if h.preds or h.only is not None {
        return None;
    }
    return _hop_key(int(h.dir), h.`edge, h.nd, h.epreds);
}


impl _memo_pairs(
    mem: Session, q: GraphQuery, allow_fast: bool = True
) -> (tuple[list[tuple[(UUID | None), (UUID | None)]], dict[UUID, Anchor]] | None) {
    # ALL-or-nothing: one origin missing from the memo and the whole query
    # falls through to the generic path unchanged. A partial answer would be
    # a wrong answer.
    #
    # `allow_fast=False` also refuses a key whose level was filled by D3's
    # `_fast_adj_sql` - see the `(None, key)` marker in _fill_adj_level.
    memo = _adj_memo(mem);
    if not memo or mem.store is None {
        return None;
    }
    key = _memo_key(q);
    if key is None {
        if PREFETCH_DEBUG {
            _pf_dbg('read miss: hop shape not memoizable ' + repr(q));
        }
        return None;
    }
    if not allow_fast and memo.get((None, key)) {
        if PREFETCH_DEBUG {
            _pf_dbg('read skip: fast-filled key, caller needs the node join');
        }
        return None;
    }
    origins = _origin_anchors(q);
    if not origins {
        return None;
    }
    pairs: list[tuple[(UUID | None), (UUID | None)]] = [];
    local: dict[UUID, Anchor] = {};
    for oanch in origins {
        if not oanch.persistent {
            # a memory-only origin is served by _walk_memory, never by SQL
            return None;
        }
        hit = memo.get((oanch.id, key));
        if hit is None {
            if PREFETCH_DEBUG {
                _pf_dbg('read miss: origin not memoized, key=' + str(key));
            }
            return None;
        }
        local[oanch.id] = oanch;
        pairs.extend(hit);
    }
    return (pairs, local);
}


impl prefetch_adjacency(
    mem: Session,
    origins: list,
    dir: int,
    edge_type: any = None,
    node_type: any = None,
    chain: (tuple | None) = None,
    epreds: (tuple | None) = None,
    ids_only: bool = False
) -> None {
    # Fill the memo for a WHOLE frontier in one statement per LEVEL. Level 1
    # takes the loop's own collection; each further level in `chain` takes the
    # previous level's targets, so a nested edge-reference loop
    # (`for post in [fo->:ContainerOf:->] { [post->:HasCreator:->] }`) costs
    # two statements for the whole request instead of one per post.
    memo = _adj_memo(mem);
    store = mem.store;
    if isinstance(origins, dict) {
        # the `for (k, v) in d.items()` hint hands over the DICT itself: its
        # VALUES are the loop's elements, and taking them here rather than in
        # the emitted `list(d.values())` keeps a hint from ever raising where
        # the loop it precedes would not
        origins = list(origins.values());
    }
    if memo is None or store is None or not origins {
        if PREFETCH_DEBUG {
            _pf_dbg(
                'fill skip: memo=' + str(memo is not None) + ' store='
                + str(store is not None) + ' origins=' + str(len(origins or []))
            );
        }
        return;
    }
    eps = _adj_qpreds(epreds);
    q = GraphQuery(
        list(origins),
        hops=[QHop(dir=int(dir), `edge=edge_type, nd=node_type, epreds=eps)]
    );
    key = _memo_key(q);
    if key is None {
        if PREFETCH_DEBUG {
            _pf_dbg('fill skip: hop shape not memoizable');
        }
        return;
    }
    ids: list[UUID] = [];
    for a in _origin_anchors(q) {
        # _origin_anchors already deduped by id: a repeated origin in the
        # list would otherwise get its rows twice (f0.ord 1 AND 2).
        if a.persistent and (a.id, key) not in memo {
            ids.append(a.id);
        }
    }
    if not ids {
        if PREFETCH_DEBUG {
            _pf_dbg('fill skip: nothing new (all origins already memoized)');
        }
        return;
    }
    # D5: `ids_only` is PER LEVEL - it is the compiler's claim about the loop
    # that consumes THAT level's targets. This argument is level 1's; a chain
    # level carries its own as a 5th tuple element.
    nxt = _fill_adj_level(mem, memo, ids, key, 1, eps, ids_only);
    lvl = 1;
    for hop in (chain or ()) {
        lvl += 1;
        # ponytail: an origin that was ALREADY memoized at the level above
        # contributes no targets here (its pairs are in the memo, not in
        # `nxt`), so a partially warm level 1 leaves the walker's own
        # per-origin statement for those - a missed hint, never a wrong
        # answer. Read them back out of the memo if a workload ever mixes
        # two hints over overlapping origin sets.
        # a chain level gains a 4th element only when it carries a predicate
        hp = _adj_qpreds(hop[3] if len(hop) > 3 else None);
        k2 = _hop_key(int(hop[0]), hop[1], hop[2], hp);
        nxt = _fill_adj_level(
            mem, memo, [i for i in nxt if (i, k2) not in memo], k2, lvl, hp,
            bool(hop[4]) if len(hop) > 4 else False
        );
    }
}


impl _adj_qpreds(spec: any) -> list {
    # C1: the hint hands over (field, op, value) triples - the same three
    # arguments the loop's own lowering passes to QPred - so the fill issues
    # character-for-character the statement the walker would have issued per
    # origin, and the memo holds exactly the pairs it would have returned.
    return [
        QPred(field=str(s[0]), op=str(s[1]), value=s[2])
        for s in (spec or ())
    ];
}


impl _fast_adj_sql(store: any, key: tuple, epreds: (list | None)) -> (tuple | None) {
    # D3: the SAME level statement, spelled for the shape the generic form
    # cannot plan well - a DIRECTED hop between two archetypes that have no
    # subtypes. compile_query pays for four things this shape does not need:
    # a direction disjunction no index can serve, three
    # `IN (SELECT ... graph_types)` subtype subqueries, a CASE join key, and a
    # PK probe into fat `anchors` per ROW only to re-test a type the EDGE row
    # already carries. Measured on the live SF1 SNB store, the ic5 first nest
    # (16 Person origins, HasMember with joinDate > d, 2929 Forum rows), warm,
    # 6 executes then EXPLAIN (ANALYZE, BUFFERS) on a generic plan:
    # 21.2ms / 20338 buffers -> 3.7ms / 3725. Same rows in the same ORDER -
    # EXCEPT ALL both ways over row_number()-tagged rows is 0 in both
    # directions. D3_IMPL.md carries both plans.
    #
    # Equivalent to the generic statement row-for-row, not merely on SNB:
    #  - the UNDIRECTED arm is kept (_dir_cond's second disjunct). It is a
    #    second index probe per ORIGIN, not per row - 48 buffers here - and
    #    dropping it would silently lose every `<++>` edge a directed hop is
    #    allowed to traverse. `e.<far> <> f.id` keeps a self-loop from
    #    arriving twice, which is the one row both arms could match.
    #  - the endpoint-type test stays NULL-TOLERANT the way
    #    _endpoint_type_cond is: an edge written while its endpoint was an
    #    unpopulated stub carries NULL src_type/dst_type, and the EXISTS is
    #    that row's authority. It is `never executed` once the store's
    #    boot backfill has run, so it costs nothing on a converted graph.
    #  - a non-NULL src_type/dst_type IS the endpoint's own arch_type (the
    #    store derives it there and on backfill), so the equality is the same
    #    test the dropped `JOIN anchors n1` applied - the assumption
    #    get_hop_counts already declares load-bearing.
    #
    # ponytail: the dropped node join also asserted the endpoint row still
    # EXISTS. An edge left dangling by a deleted node is kept here and dropped
    # downstream by _materialize_ids (resolve_query) exactly as an
    # unpopulated anchor is. resolve_query_edges reports the EDGE, which
    # _materialize_ids does not drop, so it refuses a fast-filled memo entry
    # outright (`_memo_pairs(..., allow_fast=False)`, the `(None, key)`
    # marker _fill_adj_level writes) and re-issues the generic statement.
    # Re-adding the join here costs 19.9ms against 3.7 - measured, same rows
    # - so it stays a declared ceiling for the ids/object paths; put
    # `JOIN anchors n ON n.id = e.<far> AND n.arch_type = '<T>'` back if a
    # workload ever leaves dangling edge rows behind.
    #
    # ponytail: an UNTYPED hop (`[-->]`, edge or node None) is declined rather
    # than given its own spelling - there is no literal to pin and the generic
    # form is already free of the subtype subqueries there. A missed
    # optimisation, never a wrong answer, same for `<-->` (dir 3).
    import from jaclang.runtimelib.sqlcompile { _pred_cond }
    dir = int(key[0]);
    if dir not in (1, 2) {
        return None;
    }
    (et, nt) = (key[1], key[2]);
    if et is None or nt is None or isinstance(nt, tuple) {
        return None;
    }
    ename: str = str(et if isinstance(et, str) else getattr(et, '__name__', ''));
    tname: str = str(nt if isinstance(nt, str) else getattr(nt, '__name__', ''));
    # interpolated as LITERALS below, the spelling get_adjacency_pairs and
    # get_closure use so postgres can PROVE a partial index's predicate
    # (a bound :et stops it doing so under a generic plan) - so nothing but a
    # bare identifier may reach the string builder
    if not ename.isidentifier() or not tname.isidentifier() {
        return None;
    }
    try {
        for n in (ename, tname) {
            if [
                t
                for t in store.subtype_names(n)
                if t != n
            ] {
                # `[?:T]` is an isinstance test; an equality cannot answer a
                # polymorphic hierarchy. (store.subtype_names is memoized per
                # store and self-invalidates when a new archetype registers -
                # see PgStore.subtype_names - so this is not a round trip.)
                return None;
            }
        }
    } except Exception {
        return None;
    }
    params: dict = {};
    pred_sql: str = '';
    for (j, p) in enumerate(epreds or []) {
        # the SAME term compile_query would emit for this predicate, built by
        # the same function, so the fast statement cannot drift from the
        # generic one on jsonb shape, casts or NULL handling
        cond = _pred_cond('e', p, params, f"p{j}");
        if cond is None {
            return None;   # not pushable: the generic path's residual owns it
        }
        pred_sql += ' AND ' + str(cond);
    }
    near: str = 'dst' if dir == 1 else 'src';
    far: str = 'src' if dir == 1 else 'dst';
    arms: list[str] = [];
    for k in (0, 1) {
        # k=0 is the DIRECTED arm; k=1 is _dir_cond's undirected disjunct,
        # the same edge walked the other way round
        nc: str = far if k else near;
        fc: str = near if k else far;
        arms.append(
            f"SELECT e.{fc} AS nid, e.id AS eid, f.id AS oid,"
            + ' f.ord AS ord, e.seq AS seq'
            + ' FROM unnest(CAST(:origin AS uuid[])) WITH ORDINALITY AS f(id, ord)'
            + f" JOIN anchors e ON e.kind = 'EdgeAnchor' AND e.arch_type = '{ename}'"
            + f" AND e.{nc} = f.id"
            + (f" AND e.undirected AND e.{fc} <> f.id" if k else '')
            + f" AND (e.{fc}_type = '{tname}' OR (e.{fc}_type IS NULL AND EXISTS ("
            + f"SELECT 1 FROM anchors n WHERE n.id = e.{fc}"
            + f" AND n.kind = 'NodeAnchor' AND n.arch_type = '{tname}')))"
            + pred_sql
        );
    }
    return (
        'SELECT u.nid, u.eid, u.oid FROM (' + ' UNION ALL '.join(arms)
            + ') u ORDER BY u.ord, u.seq, u.eid',
        params
    );
}


impl _fill_adj_level(
    mem: Session, memo: dict, ids: list[UUID], key: tuple, level: int,
    epreds: (list | None) = None, ids_only: bool = False
) -> list[UUID] {
    # ONE level of the fill: the exact statement `_sql_pairs` would issue for
    # each origin separately, plus `f0.id` in the SELECT (with_origin) so the
    # rows can be partitioned back per origin. `ORDER BY f0.ord, e1.seq,
    # e1.id` is unchanged, so within one origin the rows are in the same
    # relative order as its single-origin query - byte-identical downstream.
    # Returns the level's deduped target ids, i.e. the next level's origins.
    store = mem.store;
    if store is None or not ids {
        return [];
    }
    mem.read_barrier();
    fast = _fast_adj_sql(store, key, epreds);
    if fast is not None {
        (sql, params) = fast;
    } else {
        q = GraphQuery(
            [],
            hops=[
                QHop(
                    dir=int(key[0]), `edge=key[1], nd=key[2],
                    epreds=list(epreds or [])
                )
            ]
        );
        cq = compile_query(
            q, 1, promotions=getattr(store, 'promotions', {}), with_origin=True
        );
        if cq.residual {
            # a partially-pushed hop re-checks predicates on materialized
            # results; the memo stores raw pairs, so never memoize one
            if PREFETCH_DEBUG {
                _pf_dbg('fill skip: residual predicates');
            }
            return [];
        }
        (sql, params) = (cq.sql, cq.params);
    }
    params['origin'] = [str(i) for i in ids];
    # Staged in a local dict and published in one update: a half-filled memo
    # would answer `[]` for origins whose rows had not arrived yet.
    acc: dict = {};
    for i in ids {
        # an origin with NO neighbours is a HIT with [], not a miss
        acc[(i, key)] = [];
    }
    if fast is not None {
        # D3's spelling drops the endpoint-node JOIN (its declared ceiling
        # above), so these pairs can name a node whose anchor is gone. Mark
        # the KEY - `_fast_adj_sql` is a pure function of it, so a key is
        # either always fast or never - and let a caller that reports the
        # EDGE rather than the node (resolve_query_edges) refuse the memo.
        # `(None, key)` cannot collide: a real entry's first element is the
        # origin's UUID.
        acc[(None, key)] = True;
    }
    nids: list[UUID] = [];
    for r in store.rows(sql, params) {
        nid = UUID(str(r[0])) if r[0] is not None else None;
        eid = UUID(str(r[1])) if r[1] is not None else None;
        acc[(UUID(str(r[2])), key)].append((nid, eid));
        if nid is not None {
            nids.append(nid);
        }
    }
    memo.update(acc);
    if PREFETCH_DEBUG {
        _pf_dbg(
            'fill ok: level=' + str(level) + ' key=' + str(key) + ' origins='
            + str(len(ids)) + ' rows=' + str(len(nids)) + ' fast='
            + str(fast is not None)
        );
    }
    out = list(dict.fromkeys(nids));
    if out and not ids_only {
        # ONE load_full over the level's neighbours, so the loop body's field
        # reads are L1 hits instead of a fetch per node
        mem.batch_get(out);
    }
    # D5: `ids_only` is the compiler's claim that this level's consumer is
    # D4's `refs(..., ids=True)` - it reads nothing above the hex id, so the
    # blobs would be decoded and thrown away (SNB ic5: ~2.5k Forum anchors a
    # request). Skipping is a PERF choice only. The memo still holds the same
    # (origin -> target, edge) pairs, and every object consumer of the same
    # key re-hydrates on its own: `_materialize_ids` batch_gets whatever is
    # not in `local` (and `local` only ever holds ORIGINS), `_try_stream`
    # loads its `need` list, `_materialize_projected` re-asks the session.
    # So a level stamped ids-only that some other loop reads as objects costs
    # one fetch, never a wrong answer. The next chain level needs ids only
    # too (`params['origin']`), so skipping here cannot starve it.
    return out;
}


impl resolve_query(
    mem: Session, q: GraphQuery, proj: (tuple | None) = None
) -> list[Anchor] {
    if not q.origin {
        return [];
    }
    # T3: the memo is consulted BEFORE the fused stream fast path, which
    # would otherwise issue its own statement. On a miss nothing above
    # changes - same fused check, same _resolve_pairs.
    if (mp := _memo_pairs(mem, q)) is not None {
        (pairs, local) = mp;
    } else {
        if (fused := _try_stream_fused(mem, q)) is not None {
            return fused;
        }
        (pairs, local) = _resolve_pairs(mem, q, len(q.hops));
    }
    ids = _unique_nodes(pairs);
    if (streamed := _try_stream(mem, q, ids, local)) is not None {
        return streamed;
    }
    if proj is not None
        and (projected := _materialize_projected(mem, ids, proj)) is not None {
        # the read verdict is already final - see _materialize_projected
        return projected[q.slc] if q.slc is not None else projected;
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


impl resolve_query_ids(mem: Session, q: GraphQuery) -> list {
    # D4: the ids-only materialization level for an UNRANGED chain, the
    # sibling of closure_refs' `_ids` arm (T7b). The compiler proved the
    # walker stages these elements as ids and reads no field off them here,
    # so nothing above the id is owed - and nothing above the id is built.
    #
    # The verdict is _materialize_ids' own, unchanged: an id the walk cannot
    # populate drops out (a dangling edge row, a deleted node), and the ACL
    # filter is the same `_acl_read_ok` the object path runs. That is
    # deliberately NOT acl_filter_ids: this path is served from the loop
    # prefetch's memo, whose `_fill_adj_level` already batch_get the level's
    # anchors, so the existence + read verdict costs a dict lookup here and
    # a mirror statement there. What D4 actually saves is the hydration one
    # rung up - _materialize_projected's per-call mirror SELECT and its Phi
    # projected stand-ins - not this check.
    #
    # The fused stream fast path is skipped for the same reason it would be
    # wasted: it exists to build objects.
    if not q.origin {
        return [];
    }
    if (mp := _memo_pairs(mem, q)) is not None {
        (pairs, local) = mp;
    } else {
        (pairs, local) = _resolve_pairs(mem, q, len(q.hops));
    }
    out = _materialize_ids(mem, _unique_nodes(pairs), local);
    if _acl_gated() {
        _prefetch_acl_roots(mem, out);
        out = [
            a
            for a in out
            if _acl_read_ok(a)
        ];
    }
    # .hex, no dashes: the spelling object_ref()/jid() answer with, so the
    # walker's own `jid(x)` over these strings is the identity (T7b)
    hexes = [
        a.id.hex
        for a in out
    ];
    return hexes[q.slc] if q.slc is not None else hexes;
}


impl resolve_query_edges(mem: Session, q: GraphQuery) -> list[Anchor] {
    if not q.origin or not q.hops {
        return [];
    }
    # memo pairs carry the edge id too, so `[x ->:E:-> :e]` is served as well.
    # allow_fast=False: unlike resolve_query, this path reports the EDGE, and
    # _materialize_ids only drops the dangling NODE - so a D3 fast-filled
    # level (no endpoint-node join) would surface an edge the generic path
    # suppresses. Those keys fall through to _resolve_pairs.
    mp = _memo_pairs(mem, q, False);
    (pairs, local) = mp if mp is not None else _resolve_pairs(mem, q, len(q.hops));
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
