impl _trace_enabled -> bool {
    val = os.environ.get('JAC_QUERY_TRACE', '');
    return val.lower() in ('1', 'true', 'yes', 'on', 'plan');
}


impl _build_view(mem: Memory, q: GraphQuery) -> _View {
    view = _View();
    # The scan exists to overlay THIS request's own uncommitted edge state
    # (fresh hash==0 edges, detached edges). Any such edge necessarily passed
    # through get/put/batch_get and is therefore in the request's touched
    # registry - scan that instead of the whole process-global L1. Fall back
    # to the full scan when there is no request context or when the planner
    # is driven against a memory that is not the context's own (tests, CLI).
    pool = None;
    try {
        import from jaclang { JacRuntimeInterface as Jac }
        ctx = Jac.get_context();
        if ctx.mem is mem {
            pool = ctx.touched;
        }
    } except Exception {
        pool = None;
    }
    if pool is None {
        pool = mem.get_mem();
    }
    for anchor in list(pool.values()) {
        if not isinstance(anchor, EdgeAnchor) or not anchor.is_populated() {
            continue;
        }
        if not _edge_alive(anchor) {
            view.detached.add(anchor.id);
        } elif anchor.hash == 0 {
            view.fresh.append(anchor);
            view.live_edges[anchor.id] = anchor;
        }
    }
    for arch in q.origin {
        vanch = arch?.__jac__;
        if isinstance(vanch, NodeAnchor) and vanch.is_populated() {
            view.live_nodes[vanch.id] = vanch;
        }
    }
    return view;
}


impl _edge_alive(ea: EdgeAnchor) -> bool {
    if _EDGE_ROWS_ONLY {
        # JAC_EDGE_ROWS_ONLY: node-doc edges arrays are stale by design, so
        # membership in src.edges proves nothing. Edge-doc existence (the
        # engine row that surfaced this anchor) is the liveness signal;
        # read-your-deletes for edges is lost while the flag is on.
        return True;
    }
    src = ea.source;
    if src is None or not src.is_populated() {
        return True;
    }
    for e in src.edges {
        if e.id == ea.id {
            return True;
        }
    }
    return False;
}


impl _live_row(
    ea: EdgeAnchor, cur: set[UUID], hop: QHop
) -> (tuple[UUID, UUID] | None) {
    src = ea.source;
    tgt = ea.target;
    if src is None or tgt is None {
        return None;
    }
    other: (NodeAnchor | None) = None;
    if hop.dir == 1 {
        if tgt.id in cur {
            other = src;
        } elif ea.is_undirected and src.id in cur {
            other = tgt;
        }
    } elif hop.dir == 3 {
        if src.id in cur {
            other = tgt;
        } elif tgt.id in cur {
            other = src;
        }
    } else {
        if src.id in cur {
            other = tgt;
        } elif ea.is_undirected and tgt.id in cur {
            other = src;
        }
    }
    if other is None {
        return None;
    }
    if hop.`edge is not None and not isinstance(ea.archetype, hop.`edge) {
        return None;
    }
    nd = hop.nd;
    if nd is not None {
        if not other.is_populated() or other.archetype is None {
            return None;
        }
        types = nd if isinstance(nd, tuple) else (nd, );
        for nt in types {
            if not isinstance(other.archetype, nt) {
                return None;
            }
        }
    }
    return (ea.id, other.id);
}


impl _node_pred_keep(
    mem: Memory, view: _View, ids: list[UUID], preds: list[QPred]
) -> list[UUID] {
    if not preds or not ids {
        return ids;
    }
    resident: dict[UUID, Anchor] = {};
    remote: list[UUID] = [];
    pool = mem.get_mem();
    for i in ids {
        a = pool.get(i) or view.live_nodes.get(i);
        if a is not None and a.is_populated() and a.archetype is not None {
            resident[i] = a;
        } else {
            remote.append(i);
        }
    }
    remote_keep: set[UUID] = set();
    if remote {
        engine_keep = mem.filter_ids(remote, preds);
        assert engine_keep is not None , (
            "non-resident ids require an engine filter_ids implementation"
        );
        remote_keep = engine_keep;
    }
    out: list[UUID] = [];
    for i in ids {
        if i in resident {
            arch = resident[i].archetype;
            if all(p.matches(getattr(arch, p.field, None)) for p in preds) {
                out.append(i);
            }
        } elif i in remote_keep {
            out.append(i);
        }
    }
    return out;
}


impl _edge_pred_keep(
    mem: Memory, view: _View, rows: list[tuple[UUID, UUID]], epreds: list[QPred]
) -> list[tuple[UUID, UUID]] {
    if not epreds or not rows {
        return rows;
    }
    pool = mem.get_mem();
    resident: dict[UUID, Anchor] = {};
    remote: list[UUID] = [];
    for (eid, _) in rows {
        a = pool.get(eid) or view.live_edges.get(eid);
        if a is not None and a.is_populated() and a.archetype is not None {
            resident[eid] = a;
        } else {
            remote.append(eid);
        }
    }
    remote_keep: set[UUID] = set();
    if remote {
        engine_keep = mem.filter_ids(remote, epreds);
        assert engine_keep is not None , (
            "non-resident edge ids require an engine filter_ids implementation"
        );
        remote_keep = engine_keep;
    }
    out: list[tuple[UUID, UUID]] = [];
    for (eid, nid) in rows {
        if eid in resident {
            arch = resident[eid].archetype;
            if all(p.matches(getattr(arch, p.field, None)) for p in epreds) {
                out.append((eid, nid));
            }
        } elif eid in remote_keep {
            out.append((eid, nid));
        }
    }
    return out;
}


# --- JAC_HEAL_CACHE ---------------------------------------------------------
# Process-global set of edge-stub ids whose EXISTENCE has been fully verified
# by a _heal_sweep pass (edge doc present AND its other endpoint present).
# view.probed only dedups within one query, so without this the same healthy
# stubs pay existing_ids + edge_endpoints + existing_ids on every request.
#
# No per-write invalidation by design: a committed edge delete rewrites the
# owning node's edges list in the same transaction, so the deleted edge's stub
# stops being consulted at all - a stale _HEAL_OK entry is dead weight, never a
# wrong answer. The ONE path that removes docs without updating referrers is
# quarantine, so quarantine clears this cache (see _mongo_quarantine).
# ponytail: single-process only, same grade as the L1 object cache.
glob _HEAL_OK: set = set();


def _edge_rows_only_env -> bool {
    import os;
    return os.environ.get('JAC_EDGE_ROWS_ONLY', '').strip().lower()
        in ('1', 'true', 'yes', 'on');
}


glob _EDGE_ROWS_ONLY: bool = _edge_rows_only_env();


def _heal_cache_env -> bool {
    import os;
    return os.environ.get('JAC_HEAL_CACHE', '').strip().lower()
        in ('1', 'true', 'yes', 'on');
}


glob HEAL_CACHE_ON: bool = _heal_cache_env();


def _heal_cache_max -> int {
    import os;
    try {
        return int(os.environ.get('JAC_HEAL_CACHE_MAX', '1000000'));
    } except ValueError {
        return 1000000;
    }
}


glob HEAL_CACHE_MAX: int = _heal_cache_max();


def heal_cache_clear {
    _HEAL_OK.clear();
}


def _heal_cache_add(alive: list[EdgeAnchor], bad: set[UUID]) -> None {
    # Only called from points where verification for `alive` actually
    # completed; `bad` are the ones this pass quarantined.
    if not HEAL_CACHE_ON {
        return;
    }
    for st in alive {
        if st.id not in bad {
            _HEAL_OK.add(st.id);
        }
    }
    if len(_HEAL_OK) > HEAL_CACHE_MAX {
        _HEAL_OK.clear();
    }
}


impl _heal_sweep(
    mem: Memory, view: _View, nanch: NodeAnchor, engine_eids: set[UUID]
) -> None {
    suspects: list[EdgeAnchor] = [];
    for stub in list(nanch.edges) {
        if stub.id in engine_eids
            or stub.id in view.probed
            or stub.is_populated()
            or (HEAL_CACHE_ON and stub.id in _HEAL_OK) {
            continue;
        }
        view.probed.add(stub.id);
        suspects.append(stub);
    }
    if not suspects {
        return;
    }
    present = mem.existing_ids([st.id for st in suspects]);
    if present is None {
        return;
    }
    alive: list[EdgeAnchor] = [];
    for st in suspects {
        if st.id in present {
            alive.append(st);
        } else {
            mem.quarantine_ref(nanch, st);
        }
    }
    if not alive {
        return;
    }
    endpoints = mem.edge_endpoints([st.id for st in alive]);
    if endpoints is None {
        return;
    }
    pool = mem.get_mem();
    other_of: dict[UUID, UUID] = {};
    to_check: list[UUID] = [];
    for st in alive {
        ends = endpoints.get(st.id);
        if ends is None {
            continue;
        }
        (src_id, dst_id) = ends;
        other_id = dst_id if src_id == nanch.id else src_id;
        resident = pool.get(other_id) or view.live_nodes.get(other_id);
        if resident is not None and resident.is_populated() {
            continue;
        }
        other_of[st.id] = other_id;
        to_check.append(other_id);
    }
    if not to_check {
        # Every alive stub's other endpoint was resident (or the engine gave no
        # endpoints for it) - nothing left to check, verification completed.
        _heal_cache_add(alive, set());
        return;
    }
    ok_nodes = mem.existing_ids(to_check);
    if ok_nodes is None {
        return;
    }
    bad: set[UUID] = set();
    for st in alive {
        oid = other_of.get(st.id);
        if oid is None {
            continue;
        }
        other_id: UUID = oid;
        if other_id in ok_nodes {
            continue;
        }
        mem.quarantine_ref(nanch, st);
        bad.add(st.id);
        try {
            import from jaclang.runtimelib.memory { TieredMemory }
            if isinstance(mem, TieredMemory) and mem.l3 is not None {
                mem.l3.quarantine_dangling(other_id, st.id, 'node');
            }
        } except Exception {
            ;
        }
        view.detached.add(st.id);
    }
    _heal_cache_add(alive, bad);
}


impl _hop_once(
    mem: Memory, view: _View, cur: list[UUID], hop: QHop, hop_idx: int
) -> list[UUID] {
    cur_set = set(cur);
    engine_rows = mem.hop_rows(cur, hop, ordered=True);
    rows: list[tuple[UUID, UUID]] = [];
    n_engine = 0;
    seen_eids: set[UUID] = set();
    if engine_rows is not None {
        for (eid, nid) in engine_rows {
            if eid in view.detached or eid in view.live_edges {
                continue;
            }
            seen_eids.add(eid);
            rows.append((eid, nid));
            n_engine += 1;
        }
    }
    live_edges: list[EdgeAnchor] = [];
    for ea in view.fresh {
        if ea.id not in seen_eids {
            seen_eids.add(ea.id);
            live_edges.append(ea);
        }
    }
    pool = mem.get_mem();
    all_eids: set[UUID] = set(seen_eids);
    for nid in cur {
        nanch = pool.get(nid) or view.live_nodes.get(nid);
        if not isinstance(nanch, NodeAnchor) or not nanch.is_populated() {
            continue;
        }
        if engine_rows is not None {
            _heal_sweep(mem, view, nanch, all_eids);
        }
        for stub in nanch.edges {
            if stub.id in seen_eids
                or not stub.is_populated()
                or stub.id in view.detached
                or stub.hash != 0 {
                continue;
            }
            seen_eids.add(stub.id);
            live_edges.append(stub);
        }
    }
    n_live = 0;
    for ea in live_edges {
        r = _live_row(ea, cur_set, hop);
        if r is not None {
            rows.append(r);
            n_live += 1;
            view.live_edges[ea.id] = ea;
            src = ea.source;
            tgt = ea.target;
            if src is not None and src.is_populated() {
                view.live_nodes[src.id] = src;
            }
            if tgt is not None and tgt.is_populated() {
                view.live_nodes[tgt.id] = tgt;
            }
        }
    }
    rows = _edge_pred_keep(mem, view, rows, hop.epreds);
    seen: set[UUID] = set();
    ids: list[UUID] = [];
    for (_, nid) in rows {
        if nid not in seen {
            seen.add(nid);
            ids.append(nid);
        }
    }
    ids = _node_pred_keep(mem, view, ids, hop.preds);
    want = hop.only_ids();
    if want is not None {
        ids = [
            i
            for i in ids
            if i in want
        ];
    }
    if _trace_enabled() {
        logger.info(
            f"[gquery] hop[{hop_idx}] {hop.repr()} in={len(cur)} "
            f"engine_rows={n_engine} live_rows={n_live} out={len(ids)}"
        );
    }
    return ids;
}


impl _resolve_ids(mem: Memory, view: _View, q: GraphQuery, upto: int) -> list[UUID] {
    seen: set[UUID] = set();
    cur: list[UUID] = [];
    for arch in q.origin {
        oanch = arch?.__jac__;
        if not isinstance(oanch, Anchor) {
            continue;
        }
        aid = oanch.id;
        if aid not in seen {
            seen.add(aid);
            cur.append(aid);
        }
    }
    if upto <= 0 or not cur {
        return cur;
    }
    for (i, hop) in enumerate(q.hops[:upto]) {
        cur = _hop_once(mem, view, cur, hop, i);
        if not cur {
            break;
        }
    }
    return cur;
}


impl _last_hop_projection(q: GraphQuery) -> (tuple | None) {
    # JAC_PROJECTION_FIELDS: when the final hop targets exactly one node type
    # with a configured field allowlist, materialize only those archetype
    # fields (plus any predicate fields the verifier reads). Returns
    # (wanted frozenset, excluded tuple) or None for full materialization.
    import from jaclang.runtimelib.utils { PROJECTION_FIELDS }
    if not PROJECTION_FIELDS or not q.hops {
        return None;
    }
    last = q.hops[-1];
    nd = last.nd;
    if nd is None or isinstance(nd, tuple) {
        return None;
    }
    wanted = PROJECTION_FIELDS.get(nd.__name__);
    if not wanted {
        return None;
    }
    import from jaclang.runtimelib.typecache { get_field_types }
    need = set(wanted) | {p.field for p in last.preds};
    excl = tuple(f for f in get_field_types(nd).keys() if f not in need);
    if not excl {
        return None;
    }
    return (frozenset(need), excl);
}


impl _materialize(
    mem: Memory,
    view: _View,
    ids: list[UUID],
    projection: (tuple | None) = None
) -> list[Anchor] {
    if not ids {
        return [];
    }
    import from jaclang.runtimelib.memory { TieredMemory }
    loaded: dict[UUID, Anchor] = {};
    missing: list[UUID] = [];
    for i in ids {
        live = view.live_nodes.get(i);
        if live is not None and live.is_populated() and live.archetype is not None {
            loaded[i] = live;
        } else {
            missing.append(i);
        }
    }
    if missing {
        if isinstance(mem, TieredMemory) {
            loaded.update(mem.batch_get(missing, projection));
        } else {
            for i in missing {
                if (a := mem.get(i)) is not None {
                    loaded[i] = a;
                }
            }
        }
    }
    return [
        loaded[i]
        for i in ids
        if i in loaded
    ];
}


impl _verify_last_hop(anchor: Anchor, hop: QHop) -> bool {
    arch = anchor.archetype;
    if arch is None {
        return False;
    }
    nd = hop.nd;
    if nd is not None {
        types = nd if isinstance(nd, tuple) else (nd, );
        for nt in types {
            if not isinstance(arch, nt) {
                return False;
            }
        }
    }
    if not all(p.matches(getattr(arch, p.field, None)) for p in hop.preds) {
        return False;
    }
    want = hop.only_ids();
    return want is None or anchor.id in want;
}


# --- JAC_ORDER_PUSHDOWN -----------------------------------------------------
# "Type:field:asc|desc" (sort only) or "Type:field:asc|desc:N" (sort + per-
# stream limit). Parsed once at import; default off.
#
# SOUNDNESS (per-stream limit): each refs expression is one planner query =
# one "stream". A per-stream limit N is only correct when the downstream
# consumer merges its streams, sorts on the SAME field/direction, and slices
# to K <= N: global top-K is then a subset of the union of per-stream top-Ns.
# CONSEQUENCE: a boot with the :N spec serves ONLY capped-consumer walkers
# correctly for the named type - an uncapped reader of that type (e.g. plain
# load_feed) receives a truncated stream. Curated bench boots only; do NOT
# run the cross-arm feed oracle with :N set.
#
# Also: the sort field does not have to survive JAC_PROJECTION_FIELDS (keys come
# from order_keys / resident getattr, never from the materialized doc), but if
# the projection allowlist excludes it the CONSUMER's own re-sort sees class
# defaults. Naming a sort field the projection drops is an operator error.
def _parse_order_pushdown -> (tuple | None) {
    import os;
    raw = os.environ.get('JAC_ORDER_PUSHDOWN', '').strip();
    if not raw {
        return None;
    }
    parts = raw.split(':');
    if len(parts) not in (3, 4) {
        raise ValueError(
            f"JAC_ORDER_PUSHDOWN must be 'Type:field:asc|desc[:N]', got {raw!r}"
        );
    }
    (tname, field, direction) = (
        parts[0].strip(), parts[1].strip(), parts[2].strip().lower()
    );
    if not tname or not field or direction not in ('asc', 'desc') {
        raise ValueError(
            f"JAC_ORDER_PUSHDOWN must be 'Type:field:asc|desc[:N]', got {raw!r}"
        );
    }
    n: (int | None) = None;
    if len(parts) == 4 {
        try {
            n = int(parts[3]);
        } except ValueError as e {
            raise ValueError(
                f"JAC_ORDER_PUSHDOWN limit must be an int, got {parts[3]!r}"
            ) from e;
        }
        if n <= 0 {
            raise ValueError(f"JAC_ORDER_PUSHDOWN limit must be > 0, got {n}");
        }
    }
    return (tname, field, direction == 'desc', n);
}


glob ORDER_PUSHDOWN: (tuple | None) = _parse_order_pushdown();


def _order_spec(q: GraphQuery) -> (tuple | None) {
    # The spec applies only when the last hop targets exactly ONE node type
    # whose name matches it - same single-type gate shape as
    # _last_hop_projection. Anything else takes the stock path untouched.
    spec = ORDER_PUSHDOWN;
    if spec is None or not q.hops {
        return None;
    }
    nd = q.hops[-1].nd;
    if nd is None or isinstance(nd, tuple) {
        return None;
    }
    return spec if nd.__name__ == spec[0] else None;
}


def _order_pairs(pairs: list[tuple], desc: bool) -> list[tuple] {
    # (x, value) pairs sorted by value, NULLS LAST IN BOTH DIRECTIONS. Split
    # first rather than sorting on a (value is None, value) key: reverse=True
    # would flip the null group to the front. Python's sort is stable, so ties
    # keep input order - which makes the slice boundary depend on candidate
    # order when values are not unique.
    vals = [
        p
        for p in pairs
        if p[1] is not None
    ];
    nulls = [
        p
        for p in pairs
        if p[1] is None
    ];
    vals.sort(key=lambda (p: tuple) { p[1]; }, reverse=desc);
    return vals + nulls;
}


def _storage_order_keys(
    mem: Memory, ids: list[UUID], field: str, desc: bool, n: int
) -> (list[tuple] | None) {
    # None = "this backend cannot sort for us" -> caller falls back to
    # materialize-all. Duck-typed on the method rather than isinstance'd on
    # MongoBackend so runtimelib keeps not importing jaclang.scale.
    import from jaclang.runtimelib.memory { TieredMemory }
    if not isinstance(mem, TieredMemory) {
        return None;
    }
    fn = getattr(mem.l3, 'order_keys', None);
    return None if fn is None else fn(ids, field, desc, n);
}


def _order_limit_ids(
    mem: Memory, view: _View, ids: list[UUID], spec: tuple
) -> (list[UUID] | None) {
    # Top-n candidate ids in sorted order, or None when the storage tier can't
    # sort (caller then materializes everything and sorts in-process).
    (_, field, desc, n) = spec;
    pool = mem.get_mem();
    pairs: list[tuple] = [];
    missing: list[UUID] = [];
    for i in ids {
        # READ ONLY: no inserts, no ctx.touched note here - the survivors go
        # through the normal _materialize call, which does all bookkeeping.
        a = view.live_nodes.get(i) or pool.get(i);
        if a is not None and a.is_populated() and a.archetype is not None {
            pairs.append((i, getattr(a.archetype, field, None)));
        } else {
            missing.append(i);
        }
    }
    if missing {
        keys = _storage_order_keys(mem, missing, field, desc, n);
        if keys is None {
            return None;
        }
        pairs.extend(keys);
    }
    return [
        p[0]
        for p in _order_pairs(pairs, desc)[:n]
    ];
}


def _order_anchors(anchors: list[Anchor], spec: tuple) -> list[Anchor] {
    (_, field, desc, n) = spec;
    ordered = [
        p[0]
        for p in _order_pairs(
            [(a, getattr(a.archetype, field, None)) for a in anchors], desc
        )
    ];
    return ordered if n is None else ordered[:n];
}


# --- JAC_LEAF_MATERIALIZE ---------------------------------------------------
# "Tweet" / "Tweet,Comment": an EXPRESSION read whose final hop targets exactly
# one listed node type returns projected plain dicts (_jac_id hex + every
# declared has-field) instead of constructed archetypes. Parsed once at import;
# empty/unset = feature off (stock).
#
# SAFETY - the read-only stamp is the PRECONDITION, not an optimization on top:
# a leaf row is not an anchor. It has no identity in L1, no touched-set entry,
# no dirty bit, no version. That is provably harmless only because the request
# was stamped read-only (walker on JAC_RO_WALKERS), which skips the end-of-
# request commit entirely and asserts nothing was written - so there is no
# commit for a leaf row to be missing from. Hence three gates, not one:
#   1. request_read_only() here, per query;
#   2. from_visit queries excluded - visit-loaded nodes are handed to walker
#      abilities and can be written (like_tweet), so they stay full-hydration;
#   3. a fail-loud re-check at the refs passthrough (JacGraph.refs), because a
#      leaf dict reaching a write path is a runtime invariant violation.
def _parse_leaf_types -> frozenset {
    import os;
    raw = os.environ.get('JAC_LEAF_MATERIALIZE', '');
    return frozenset(t.strip() for t in raw.split(',') if t.strip());
}


glob LEAF_TYPES: frozenset = _parse_leaf_types();


def _leaf_cls(q: GraphQuery) -> (type | None) {
    # Same single-type last-hop gate shape as _last_hop_projection/_order_spec.
    if not LEAF_TYPES or not q.hops or q.from_visit {
        return None;
    }
    nd = q.hops[-1].nd;
    if nd is None or isinstance(nd, tuple) or nd.__name__ not in LEAF_TYPES {
        return None;
    }
    import from jaclang.runtimelib.utils { request_read_only }
    return nd if request_read_only() else None;
}


def _leaf_row(arch: object, id: UUID, names: tuple) -> dict {
    return {'_jac_id': id.hex}
        | {
            f: getattr(arch, f, None)
            for f in names
        };
}


def _leaf_fetch(mem: Memory, ids: list[UUID], names: tuple) -> (dict | None) {
    # None = "this backend cannot project rows" -> caller falls back to stock
    # materialization. Duck-typed on the method like _storage_order_keys.
    import from jaclang.runtimelib.memory { TieredMemory }
    if not isinstance(mem, TieredMemory) {
        return None;
    }
    fn = getattr(mem.l3, 'leaf_rows', None);
    return None if fn is None else fn(ids, names);
}


def _leaf_rows(mem: Memory, view: _View, ids: list[UUID], cls: type) -> list[dict] {
    import from jaclang.runtimelib.typecache { field_names }
    names = field_names(cls);
    pool = mem.get_mem();
    rows: dict[UUID, dict] = {};
    missing: list[UUID] = [];
    for i in ids {
        # READ ONLY: resident anchors are read, never inserted or noted.
        a = view.live_nodes.get(i) or pool.get(i);
        if a is not None and a.is_populated() and a.archetype is not None {
            rows[i] = _leaf_row(a.archetype, i, names);
        } else {
            missing.append(i);
        }
    }
    if missing {
        fetched = _leaf_fetch(mem, missing, names);
        if fetched {
            rows.update(fetched);
        }
        rest = [
            i
            for i in missing
            if i not in rows
        ];
        if rest {
            # Backend without leaf_rows (sqlite/plain memory), a doc the engine
            # could not project, or a genuinely absent id: stock materialize and
            # flatten. Output-identical - class defaults included - just no win.
            for a in _materialize(mem, view, rest) {
                if a.archetype is not None {
                    rows[a.id] = _leaf_row(a.archetype, a.id, names);
                }
            }
        }
    }
    return [
        rows[i]
        for i in ids
        if i in rows
    ];
}


def _leaf_finish(
    mem: Memory,
    view: _View,
    ids: list[UUID],
    last: QHop,
    cls: type,
    sort_after: (tuple | None)
) -> list {
    rows = _leaf_rows(mem, view, ids, cls);
    want = last.only_ids();
    # No isinstance check on a row: _hop_once already type-narrowed the final
    # hop (_live_row rejects targets that are not hop.nd) and the single-type
    # gate proved hop.nd IS cls - the same reasoning _verify_last_hop's
    # isinstance re-checks defensively. Predicates and only-ids remain, read
    # dict-aware off the projected row.
    verified = [
        r
        for r in rows
        if all(p.matches(r.get(p.field)) for p in last.preds)
            and (want is None or UUID(r['_jac_id']) in want)
    ];
    if sort_after is not None {
        (_, field, desc, n) = sort_after;
        ordered = [
            p[0]
            for p in _order_pairs([(r, r.get(field)) for r in verified], desc)
        ];
        verified = ordered if n is None else ordered[:n];
    }
    if _trace_enabled() {
        logger.info(
            f"[gquery] leaf {cls.__name__} ids={len(ids)} rows={len(rows)} "
            f"verified={len(verified)}"
        );
    }
    return verified;
}


impl resolve_query_prefix(mem: Memory, q: GraphQuery, upto: int) -> list[UUID] {
    view = _build_view(mem, q);
    return _resolve_ids(mem, view, q, upto);
}


impl resolve_query(mem: Memory, q: GraphQuery) -> list[Anchor] {
    if not q.origin {
        return [];
    }
    view = _build_view(mem, q);
    ids = _resolve_ids(mem, view, q, len(q.hops));
    if q.slc is not None {
        ids = ids[q.slc];
    }
    spec = _order_spec(q) if ORDER_PUSHDOWN is not None else None;
    sort_after: (tuple | None) = spec;
    if spec is not None and spec[3] is not None {
        final = _order_limit_ids(mem, view, ids, spec);
        if final is not None {
            # _materialize returns in ids order, so the winners come back
            # already sorted and capped; nothing left to do after verify.
            ids = final;
            sort_after = None;
        }
    }
    leaf = _leaf_cls(q);
    if leaf is not None {
        # Leaf composes AFTER id selection: hop caches, slc and the pushdown's
        # _order_limit_ids all ran above untouched. Declared return type says
        # list[Anchor]; leaf rows are dicts (checker noise, accepted) and the
        # refs passthrough re-gates them fail-loud.
        return _leaf_finish(mem, view, ids, q.hops[-1], leaf, sort_after);
    }
    winners = _materialize(mem, view, ids, _last_hop_projection(q));
    if not q.hops {
        return winners;
    }
    last = q.hops[-1];
    # Last-hop predicates can drop the verified count below the limit (the
    # pushdown picks the top-n candidates, the verifier then filters them).
    # Documented edge; feed workloads carry no last-hop preds.
    verified = [
        w
        for w in winners
        if _verify_last_hop(w, last)
    ];
    if sort_after is not None {
        # Sort-only spec, or the no-storage-sort fallback: same order, same
        # cap, computed in-process off the materialized archetypes.
        verified = _order_anchors(verified, sort_after);
    }
    if _trace_enabled() {
        logger.info(
            f"[gquery] final materialized={len(winners)} "
            f"verified={len(verified)} slc={q.slc}"
        );
    }
    return verified;
}


impl resolve_query_edges(mem: Memory, q: GraphQuery) -> list[Anchor] {
    if not q.origin or not q.hops {
        return [];
    }
    view = _build_view(mem, q);
    prefix_ids = _resolve_ids(mem, view, q, len(q.hops) - 1);
    if not prefix_ids {
        return [];
    }
    hop = q.hops[-1];
    frontier = _materialize(mem, view, prefix_ids);
    cur_set = {a.id for a in frontier};
    pool = mem.get_mem();
    candidates: list[EdgeAnchor] = [];
    seen: set[UUID] = set();
    pending: list[UUID] = [];
    for n in frontier {
        if not isinstance(n, NodeAnchor) or not n.is_populated() {
            continue;
        }
        for stub in n.edges {
            if stub.id in seen {
                continue;
            }
            seen.add(stub.id);
            found = pool.get(stub.id) or view.live_edges.get(stub.id);
            if found is None and stub.is_populated() {
                found = stub;
            }
            if isinstance(found, EdgeAnchor) and found.is_populated() {
                candidates.append(found);
            } else {
                pending.append(stub.id);
            }
        }
    }
    if pending {
        import from jaclang.runtimelib.memory { TieredMemory }
        fetched: dict[UUID, Anchor];
        if isinstance(mem, TieredMemory) {
            fetched = mem.batch_get(pending);
        } else {
            fetched = {
                i: a
                for i in pending
                if (a := mem.get(i)) is not None
            };
        }
        for i in pending {
            fa = fetched.get(i);
            if isinstance(fa, EdgeAnchor) and fa.is_populated() {
                candidates.append(fa);
            }
        }
    }
    out: list[Anchor] = [];
    seen_nodes: set[UUID] = set();
    ewant = hop.only_ids();
    for ea in candidates {
        if ea.archetype is None or ea.id in view.detached {
            continue;
        }
        src = ea.source;
        tgt = ea.target;
        if src is None or tgt is None {
            continue;
        }
        hit = False;
        if hop.dir == 1 {
            hit = tgt.id in cur_set or (ea.is_undirected and src.id in cur_set);
        } elif hop.dir == 3 {
            hit = src.id in cur_set or tgt.id in cur_set;
        } else {
            hit = src.id in cur_set or (ea.is_undirected and tgt.id in cur_set);
        }
        if not hit {
            continue;
        }
        if hop.`edge is not None and not isinstance(ea.archetype, hop.`edge) {
            continue;
        }
        if hop.epreds
            and not all(
                p.matches(getattr(ea.archetype, p.field, None)) for p in hop.epreds
            ) {
            continue;
        }
        other = tgt if src.id in cur_set else src;
        if ewant is not None and other.id not in ewant {
            continue;
        }
        if hop.nd is not None or hop.preds or q.from_visit {
            other_l = _materialize(mem, view, [other.id]);
            if not other_l {
                continue;
            }
            if not _verify_last_hop(other_l[0], hop) {
                continue;
            }
            out.append(ea);
            if q.from_visit and other.id not in seen_nodes {
                seen_nodes.add(other.id);
                out.append(other_l[0]);
            }
        } else {
            out.append(ea);
        }
    }
    if q.slc is not None {
        out = out[q.slc];
    }
    return out;
}
