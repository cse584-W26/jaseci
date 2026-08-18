def _ident_ok(name: str) -> bool {
    if not name {
        return False;
    }
    for ch in name {
        if not (ch.isalnum() or ch == '_') {
            return False;
        }
    }
    return not name[0].isdigit();
}


def _scalar(v: any) -> any {
    return str(v) if isinstance(v, UUID) else v;
}


def _pushable_value(v: any) -> bool {
    if isinstance(v, (str, int, float, bool, UUID)) or v is None {
        return True;
    }
    if isinstance(v, (list, tuple, set)) {
        for x in v {
            if not isinstance(x, (str, int, float, bool, UUID)) {
                return False;
            }
        }
        return True;
    }
    return False;
}


def _type_cond_col(col: str, tname: str, params: dict, pfx: str) -> str {
    key = f"{pfx}t";
    params[key] = tname;
    return (
        f"({col} = :{key} OR {col} IN "
        f"(SELECT type_name FROM graph_types WHERE ancestor = :{key}))"
    );
}


def _type_cond(alias: str, tname: str, params: dict, pfx: str) -> str {
    return _type_cond_col(f"{alias}.arch_type", tname, params, pfx);
}


# The same polymorphic test the node join applies, but against the endpoint
# type denormalised onto the edge row (src_type / dst_type). Emitting it inside
# the edge condition lets a typed hop prune at idx_anchors_{src,dst}_typed
# instead of fetching every incident target and discarding the misses.
def _endpoint_type_cond(
    alias: str, col: str, names: list[str], params: dict, pfx: str
) -> (str | None) {
    parts: list[str] = [];
    for (k, tname) in enumerate(names) {
        if tname {
            parts.append(
                _type_cond_col(f"{alias}.{col}", tname, params, f"{pfx}x{k}")
            );
        }
    }
    if not parts {
        return None;
    }
    inner = parts[0] if len(parts) == 1 else f"({' OR '.join(parts)})";
    # NULL-tolerant by construction. The backfill fills legacy rows, but an
    # edge written while an endpoint was an unpopulated stub can still carry
    # NULL, and silently dropping such an edge from a traversal would be a
    # correctness bug. Letting NULL through only costs a probe: the node join
    # downstream applies the authoritative type test anyway.
    return f"({alias}.{col} IS NULL OR {inner})";
}


def _sql_type_of(v: any) -> str {
    if isinstance(v, bool) {
        return 'boolean';
    }
    if isinstance(v, int) {
        return 'bigint';
    }
    if isinstance(v, float) {
        return 'float8';
    }
    return 'text';
}


# JAC_PROMOTED_PREDICATES=1: when a queried field is generated-column
# promoted (see PgStore._apply_promotions), emit the predicate against that
# real typed+indexed column instead of the jsonb path so postgres can use
# the promotion index. Default off - see _pred_cond for the scope this is
# limited to and why.
def _promoted_predicates_enabled -> bool {
    import os;
    return os.environ.get('JAC_PROMOTED_PREDICATES', '').strip().lower()
        in ('1', 'true', 'yes', 'on');
}


glob PROMOTED_PREDICATES: bool = _promoted_predicates_enabled();


# JAC_STREAM_LATERAL=1: emit the final mirror hop as a per-source LATERAL
# top-K instead of a flat join (see compile_query). Default off.
def _stream_lateral_enabled -> bool {
    import os;
    return os.environ.get('JAC_STREAM_LATERAL', '').strip().lower()
        in ('1', 'true', 'yes', 'on');
}


glob STREAM_LATERAL: bool = _stream_lateral_enabled();


# JAC_FUSED_FEED=1: for a MULTI-hop stream query whose final hop is a
# top-K mirror fetch off the endpoint column, drive the whole statement from
# ONE ordered index scan on the sort column and demote the traversal to an
# `= ANY(ARRAY(...))` InitPlan membership filter, instead of a per-source
# LATERAL top-K (JAC_STREAM_LATERAL).
#
# Why (W3 feed_page census, snb0818): the LATERAL fetches cap rows per SOURCE
# and throws away all but the global cap - 54 followees x 28 = 1512 wide rows
# materialised to return 28, i.e. 2700 heap rows / 413 buffers per request.
# The global form reads the sort index in order and stops at the cap: 53 rows
# examined, 28 returned. EXPLAIN ANALYZE on the t50 fixture: 3.127ms -> 0.141ms.
# This is the shape the hand-tuned pg arm uses (`WHERE author_id IN (...)
# ORDER BY created_at DESC LIMIT 20`).
#
# ponytail: trades per-source bounded work for membership SELECTIVITY. The
# scan walks the sort index until it has found cap admitted rows, so a caller
# whose traversal reaches a vanishing fraction of the mirror walks
# proportionally further (worst case, the whole index) where the LATERAL was
# bounded by sources x cap. Fine at feed shapes (a follow set is a sizeable
# slice of the corpus) and the flag is the guard; the principled fix is a
# planner cost estimate off the mirror's row count vs the traversal's
# cardinality, which needs statistics the planner does not carry yet.
def _fused_feed_enabled -> bool {
    import os;
    return os.environ.get('JAC_FUSED_FEED', '').strip().lower()
        in ('1', 'true', 'yes', 'on');
}


glob FUSED_FEED: bool = _fused_feed_enabled();


# JAC_PROMOTED_DRIVE=1: when a hop's node carries a promoted-column EQUALITY
# predicate, emit the node join BEFORE the edge join and pin the edge's far
# endpoint to the node alias, instead of deriving the node id from the edge
# with _other_expr's CASE.
#
# Why this exists (TPC-C P6 turn 1 census). `n1.id = CASE WHEN e1.src = f0.id
# THEN e1.dst ELSE e1.src END` is opaque to the planner: it cannot be inverted,
# so the ONLY legal drive order is origin -> every edge -> one anchors_pkey
# probe per neighbour -> filter. The promotion index is then unreachable and
# the promoted column degrades from an access path into a post-materialisation
# filter. Measured on TPC-C Payment-by-c_last: 3000 Index Searches / 12000
# buffers to return 3 rows, 9.5ms per request, while the hand-tuned arm's
# equivalent index lookup is 0.06ms.
#
# The pinned form `(e.src = f0.id AND e.dst = n1.id) OR (e.undirected AND
# e.dst = f0.id AND e.src = n1.id)` is the SAME predicate written so both
# endpoints are plain equalities, which lets the planner start at the
# promotion index and confirm the edge through idx_anchors_{src,dst}. Row set
# and ORDER BY are unchanged (the ORDER is still the edge's seq/id), so the
# result is identical - it is purely a drive-order enabler.
#
# ponytail: gated on an EQUALITY promoted predicate only. Range/!= promoted
# predicates are not selective enough to be worth inverting the drive order,
# and an unfiltered hop would be strictly worse driven node-first (it would
# scan the whole archetype). Default off.
def _promoted_drive_enabled -> bool {
    import os;
    return os.environ.get('JAC_PROMOTED_DRIVE', '').strip().lower()
        in ('1', 'true', 'yes', 'on');
}


glob PROMOTED_DRIVE: bool = _promoted_drive_enabled();


# Mirrors PgStore._sanitize_ident (store.impl.jac) exactly - the promoted
# column name has to be derived identically here and at DDL time or the
# predicate references a column that was never created. Duplicated rather
# than imported: it's 6 lines and store.impl.jac doesn't export it.
def _sanitize_ident(name: str) -> str {
    out = '';
    for ch in name.lower() {
        out += ch if (ch.isalnum() or ch == '_') else '_';
    }
    return out;
}


def _promoted_column(
    promotions: dict[str, list[str]], arch: str, fld: str
) -> (str | None) {
    if not arch or fld not in promotions.get(arch, []) {
        return None;
    }
    return f"g_{_sanitize_ident(arch)}_{_sanitize_ident(fld)}";
}


def _pred_cond(
    alias: str, p: QPred, params: dict, pfx: str, promoted_col: (str | None) = None
) -> (str | None) {
    if not _ident_ok(p.field) or not _pushable_value(p.value) {
        return None;
    }
    if promoted_col is not None and p.op in ('==', '!=', 'in') {
        # Promoted columns are TEXT, generated as props->archetype->>fld
        # (note ->>, not ->): a JSON-null value AND a missing key both
        # collapse to SQL NULL there, whereas the jsonb-path expression
        # below distinguishes them ('null'::jsonb vs SQL NULL). So this
        # only fires for concrete non-None text-typed values/lists - a
        # None-valued predicate or a non-str value falls through to the
        # unaccelerated jsonb path, which stays byte-identical to today.
        # ponytail: numeric/bool promoted-column comparisons and ordered
        # (<,<=,>,>=) ops aren't accelerated either - the generated column
        # is always TEXT (store.impl.jac), so a numeric predicate would
        # need a cast that defeats the plain-btree index anyway. Extend
        # _apply_promotions to type the column per-field if that ever
        # shows up hot.
        if p.op == 'in' {
            vals = list(p.value) if isinstance(p.value, (list, tuple, set)) else [p.value];
            if vals and all(isinstance(v, str) for v in vals) {
                # fixed-shape: one array param regardless of len(vals), so
                # the SQL text (and psycopg's prepared-statement cache key)
                # doesn't change with list length.
                key = f"{pfx}v";
                params[key] = vals;
                return f"{alias}.{promoted_col} = ANY(CAST(:{key} AS text[]))";
            }
        } elif isinstance(p.value, str) {
            key = f"{pfx}v";
            params[key] = p.value;
            if p.op == '==' {
                return f"{alias}.{promoted_col} = :{key}";
            }
            # '!=': missing-key/JSON-null rows read back as SQL NULL on the
            # promoted column, and IS NULL must satisfy != here - same as
            # the jsonb branch's "expr IS NULL OR expr <> rhs" below.
            return f"({alias}.{promoted_col} IS NULL OR {alias}.{promoted_col} <> :{key})";
        }
    }
    expr = f"{alias}.props->'archetype'->'{p.field}'";
    if p.op == 'in' {
        vals = list(p.value) if isinstance(p.value, (list, tuple, set)) else [p.value];
        if not vals {
            return 'FALSE';
        }
        scalars = [_scalar(v) for v in vals];
        sql_types = {_sql_type_of(v) for v in scalars};
        if len(sql_types) == 1 {
            # fixed-shape: one array param regardless of len(vals) - only
            # possible when every value shares a SQL type (the common case).
            sql_type = sql_types.pop();
            key = f"{pfx}v";
            params[key] = scalars;
            return (
                f"{expr} = ANY(SELECT to_jsonb(x) FROM "
                f"unnest(CAST(:{key} AS {sql_type}[])) AS x)"
            );
        }
        # ponytail: mixed-type IN list - rare (predicate values normally
        # share a type). Falls back to one literal per value, same as
        # before; not on the prepared-statement-reuse hot path.
        parts: list[str] = [];
        for (i, v) in enumerate(scalars) {
            key = f"{pfx}v{i}";
            params[key] = v;
            parts.append(f"to_jsonb(CAST(:{key} AS {_sql_type_of(v)}))");
        }
        return f"{expr} IN ({', '.join(parts)})";
    }
    if p.value is None {
        if p.op == '==' {
            return f"{expr} = 'null'::jsonb";
        }
        if p.op == '!=' {
            return f"({expr} IS NULL OR {expr} <> 'null'::jsonb)";
        }
        return 'FALSE';
    }
    key = f"{pfx}v";
    params[key] = _scalar(p.value);
    rhs = f"to_jsonb(CAST(:{key} AS {_sql_type_of(p.value)}))";
    if p.op == '==' {
        return f"{expr} = {rhs}";
    }
    if p.op == '!=' {
        return f"({expr} IS NULL OR {expr} <> {rhs})";
    }
    op = {'<': '<', '<=': '<=', '>': '>', '>=': '>='}.get(p.op);
    if op is None {
        return None;
    }
    return f"{expr} {op} {rhs}";
}


def _dir_cond(
    alias: str,
    fid: str,
    dir: int,
    to_dst: (str | None) = None,
    to_src: (str | None) = None
) -> str {
    # to_dst / to_src are the target-node type tests to apply on the branch
    # where the hop lands on e.dst / e.src respectively.
    def arm(side: str, cond: (str | None)) -> str {
        base = f"{alias}.{side} = {fid}";
        return base if cond is None else f"({base} AND {cond})";
    }

    if dir == 1 {
        return (
            f"({arm('dst', to_src)} OR ({alias}.undirected "
            f"AND {arm('src', to_dst)}))"
        );
    }
    if dir == 3 {
        return f"({arm('src', to_dst)} OR {arm('dst', to_src)})";
    }
    return (
        f"({arm('src', to_dst)} OR ({alias}.undirected AND {arm('dst', to_src)}))"
    );
}


def _other_expr(alias: str, fid: str) -> str {
    return f"CASE WHEN {alias}.src = {fid} THEN {alias}.dst ELSE {alias}.src END";
}


def _dir_cond_pinned(
    alias: str,
    fid: str,
    other: str,
    dir: int,
    to_dst: (str | None) = None,
    to_src: (str | None) = None
) -> str {
    # _dir_cond, but each arm also pins the far endpoint to `other` (the node
    # alias) rather than leaving it to _other_expr's CASE. Same row set: on the
    # arm where the near endpoint is `src`, _other_expr yields `dst`, so
    # `dst = other` is exactly the join the CASE encodes - and vice versa.
    # See PROMOTED_DRIVE above.
    def arm(near: str, far: str, cond: (str | None)) -> str {
        base = f"{alias}.{near} = {fid} AND {alias}.{far} = {other}";
        return f"({base})" if cond is None else f"({base} AND {cond})";
    }

    if dir == 1 {
        return (
            f"({arm('dst', 'src', to_src)} OR ({alias}.undirected "
            f"AND {arm('src', 'dst', to_dst)}))"
        );
    }
    if dir == 3 {
        return f"({arm('src', 'dst', to_dst)} OR {arm('dst', 'src', to_src)})";
    }
    return (
        f"({arm('src', 'dst', to_dst)} OR "
        f"({alias}.undirected AND {arm('dst', 'src', to_src)}))"
    );
}


def _nd_types(hop: QHop) -> list {
    nd = hop.nd;
    if nd is None {
        return [];
    }
    return list(nd) if isinstance(nd, tuple) else [nd];
}


impl compile_query(
    q: GraphQuery,
    upto: int,
    mirror: (dict | None) = None,
    promotions: dict[str, list[str]] = {}
) -> CompiledQuery {
    # mirror (R3): {'table': str, 'fcols': [column, ...]} - the FINAL hop's
    # node join targets the slim per-archetype mirror table instead of fat
    # `anchors`, and the SELECT returns the mirror's fragment/ACL columns so
    # traversal + fetch collapse into ONE statement. The caller has already
    # proven mirror membership == the hop's type test (single class, no
    # registered subtypes) and that the final hop carries no node predicates.
    out = CompiledQuery();
    params: dict = {};
    params['origin'] = [];
    # mirror['acl'] (JAC_SQL_ACL, built by query_planner._acl_sql_ctx): the
    # read decision as a predicate on the mirror row, `%M%` standing in for
    # whichever alias the final hop ends up with. It is appended to the mirror
    # join's ON list - inside the LATERAL when there is one - so it is applied
    # BEFORE that subquery's LIMIT and before the _topk wrapper. All-bound
    # params, so the statement text stays fixed-shape for prepared-statement
    # reuse.
    acl_sql = mirror.get('acl') if mirror is not None else None;
    if acl_sql is not None {
        params.update(mirror.get('acl_params', {}));
    }
    joins: list[str] = [];
    order: list[str] = [];
    fid = 'f0.id';
    n = 0;
    # R4/R5: distributed top-K pushdown. When the final hop is a mirror fetch
    # with a pipeline sort column AND the store maintains the endpoint column
    # (PgStore.ensure_mirror_endpoint), that hop is emitted as a LATERAL
    # correlated to the previous hop's id, keyed on the mirror's src_endpoint
    # and ordered by the sort column - a per-source index range scan that
    # stops after cap rows, with no `anchors` join inside it at all. Safe: any
    # row inside the global top-cap (still cut by the unchanged _topk wrapper
    # below) is necessarily inside its own source's top-cap too.
    #
    # BOTH conditions are required. The endpoint column is what makes this
    # cheaper; the same LATERAL over an edge join does the SAME number of
    # mirror lookups plus a sort per source, and measured 30% SLOWER at t200
    # (PROGRESS.log PHASE9/PHASE10 A/Bs) - so without it the flat join wins
    # and stays the fallback.
    # JAC_FUSED_FEED (see the flag): same preconditions as the LATERAL plus a
    # traversal to demote (>=2 hops) and the global sort index the planner
    # asked the store for. Wins the tie - it subsumes the LATERAL's shape,
    # hence lateral_used stands down when it is on.
    global_used = mirror is not None and bool(mirror.get('global_topk'));
    lateral_used = (
        STREAM_LATERAL
        and not global_used
        and mirror is not None
        and mirror.get('order_col') is not None
        and mirror.get('endpoint_col') is not None
    );
    src_fid = 'f0.id';
    for (i, hop) in enumerate(q.hops[:upto]) {
        n = i + 1;
        e = f"e{n}";
        nd_alias = f"n{n}";
        pfx_e = f"h{n}e";
        is_final = (i == len(q.hops[:upto]) - 1);
        if is_final and global_used {
            # The final hop IS the driving scan, emitted below off the
            # endpoint column - it joins nothing here, exactly as the LATERAL
            # branch replaces its edge join. `src_fid` is the id the traversal
            # subquery hands it (mirror membership == the hop's type test is
            # the caller's precondition, same as the LATERAL).
            src_fid = fid;
            fid = f"{nd_alias}.id";
            continue;
        }
        lateral_final = is_final and mirror is not None and lateral_used;
        nd_names = [
            str(getattr(nt, '__name__', ''))
            for nt in _nd_types(hop)
        ];
        to_dst = _endpoint_type_cond(e, 'dst_type', nd_names, params, f"{pfx_e}d");
        to_src = _endpoint_type_cond(e, 'src_type', nd_names, params, f"{pfx_e}s");
        econds = [
            f"{e}.kind = 'EdgeAnchor'",
            _dir_cond(e, fid, hop.dir, to_dst, to_src)
        ];
        epred_arch = '';
        if hop.`edge is not None {
            epred_arch = str(getattr(hop.`edge, '__name__', ''));
            econds.append(_type_cond(e, epred_arch, params, pfx_e));
        }
        for (j, p) in enumerate(hop.epreds) {
            pcol = (
                _promoted_column(promotions, epred_arch, p.field)
                    if PROMOTED_PREDICATES else None
            );
            cond = _pred_cond(e, p, params, f"{pfx_e}p{j}", pcol);
            if cond is None {
                out.residual.setdefault(i, []).append(p);
            } else {
                econds.append(cond);
            }
        }
        # The edge join's slot is reserved now but filled after the node
        # predicates are known: PROMOTED_DRIVE may want the node join to come
        # first (see the flag's comment). With the flag off the slot is filled
        # with exactly the string this used to append, in the same position,
        # so the SQL text is byte-identical.
        edge_slot = -1;
        if not lateral_final {
            # The lateral_final case replaces this edge join entirely with the
            # mirror's endpoint column (the whole point of R5), so emitting it
            # here would put back exactly the work being removed.
            edge_slot = len(joins);
            joins.append('');
        }
        nconds = [
            f"{nd_alias}.id = {_other_expr(e, fid)}",
            f"{nd_alias}.kind = 'NodeAnchor'"
        ];
        nd_types_l = _nd_types(hop);
        for (k, nt) in enumerate(nd_types_l) {
            tname = str(getattr(nt, '__name__', ''));
            if tname {
                nconds.append(_type_cond(nd_alias, tname, params, f"h{n}n{k}"));
            }
        }
        # Promotion is keyed by a single archetype name; only substitute
        # when the hop pins the node to exactly one candidate type
        # (`[?:Tweet]`), never for an untyped or multi-type hop
        # (`[?:Tweet|Channel]`) where the same field name could mean two
        # different promoted columns.
        pred_arch = (
            str(getattr(nd_types_l[0], '__name__', ''))
                if len(nd_types_l) == 1 else ''
        );
        drive_node = False;
        for (j, p) in enumerate(hop.preds) {
            pcol = (
                _promoted_column(promotions, pred_arch, p.field)
                    if PROMOTED_PREDICATES else None
            );
            cond = _pred_cond(nd_alias, p, params, f"h{n}np{j}", pcol);
            if cond is None {
                out.residual.setdefault(i, []).append(p);
            } else {
                nconds.append(cond);
                if pcol is not None and p.op in ('==', 'in') {
                    drive_node = True;
                }
            }
        }
        want = hop.only_ids();
        if want is not None {
            key = f"h{n}only";
            params[key] = [str(x) for x in want];
            nconds.append(f"{nd_alias}.id = ANY(CAST(:{key} AS uuid[]))");
        }
        if lateral_final {
            lat_sel_parts: list = [
                f"{nd_alias}.id", f"{nd_alias}.root_id", f"{nd_alias}.acl_all",
                f"{nd_alias}.acl_spec", f"{nd_alias}.frag"
            ];
            for c in mirror['fcols'] {
                # ::text here (not at the outer SELECT) - same wire-format
                # pin as the flat-mirror branch below; the outer sel just
                # forwards the already-text column through t{n}.
                lat_sel_parts.append(f"{nd_alias}." + c + '::text');
            }
            lat_sel_parts.append(f"{nd_alias}." + mirror['order_col'] + ' AS _ordcol');
            # ponytail: the edge row is gone, so its (seq, id) can no longer
            # break ties between two rows of the SAME source - the mirror's own
            # id stands in. Only observable when one source has two rows with
            # an identical sort value; the page-parity oracle gates it.
            lat_sel_parts.append(f"{nd_alias}.id AS _eid");
            lat_mconds = [f"{nd_alias}.{mirror['endpoint_col']} = {fid}"];
            want_m = hop.only_ids();
            if want_m is not None {
                key_m = f"h{n}only";
                params[key_m] = [str(x) for x in want_m];
                lat_mconds.append(f"{nd_alias}.id = ANY(CAST(:{key_m} AS uuid[]))");
            }
            if acl_sql is not None {
                lat_mconds.append(acl_sql.replace('%M%', nd_alias));
            }
            lat_dirn = 'DESC' if mirror.get('desc') else 'ASC';
            lat_cap_key = f"h{n}lcap";
            # bound param, not an inlined literal: the cap can vary per call
            # (page-size pipelines) - a literal would make the SQL text (and
            # psycopg's prepared-statement cache key) different every time.
            params[lat_cap_key] = int(mirror.get('limit', 0)) + int(mirror.get('slack', 0));
            joins.append(
                'JOIN LATERAL (SELECT ' + ', '.join(lat_sel_parts)
                + ' FROM ' + mirror['table'] + ' ' + nd_alias
                + ' WHERE ' + ' AND '.join(lat_mconds)
                + ' ORDER BY ' + nd_alias + '.' + mirror['order_col'] + ' ' + lat_dirn
                + f' LIMIT :{lat_cap_key}'
                + ') t' + str(n) + ' ON true'
            );
            order.append('t' + str(n) + '._eid');
        } elif mirror is not None and is_final {
            mconds = [f"{nd_alias}.id = {_other_expr(e, fid)}"];
            want_m = hop.only_ids();
            if want_m is not None {
                key_m = f"h{n}only";
                params[key_m] = [str(x) for x in want_m];
                mconds.append(f"{nd_alias}.id = ANY(CAST(:{key_m} AS uuid[]))");
            }
            if acl_sql is not None {
                mconds.append(acl_sql.replace('%M%', nd_alias));
            }
            joins.append(
                'JOIN ' + mirror['table'] + f" {nd_alias} ON "
                    + ' AND '.join(mconds)
            );
            order.append(f"{e}.seq");
            order.append(f"{e}.id");
        } else {
            if PROMOTED_DRIVE and drive_node {
                # Node join FIRST (drivable from the promotion index), edge
                # join second with both endpoints pinned. nconds[0] is the
                # _other_expr CASE equality - the pinned edge condition
                # replaces it, so it is dropped here rather than duplicated.
                #
                # The exact-type conjunct is what actually unlocks the index:
                # PgStore._apply_promotions builds the promotion index PARTIAL
                # on `arch_type = '<Arch>'`, and postgres will only use a
                # partial index when it can PROVE the predicate. _type_cond's
                # polymorphic `(= :t OR IN (SELECT ... ancestor = :t))` is not
                # provable, so without this line the node join degrades to a
                # Parallel Seq Scan over every anchor - measured 110ms vs
                # 18.8ms unflagged, i.e. WORSE than doing nothing. Reuses
                # _type_cond's own param key (:h{n}n0t) so no new bind is
                # added and the statement stays fixed-shape.
                #
                # ponytail: this narrows the hop to the EXACT promoted
                # archetype - a registered SUBTYPE of it would be matched by
                # the flag-off polymorphic test but missed here. That is the
                # same exactness the promotion index itself already assumes,
                # and no bench declares a subtype of a promoted archetype.
                # Ceiling declared, not solved: if a promoted archetype ever
                # gains subtypes, either widen the index predicate to
                # `g_<col> IS NOT NULL` (provable from the equality) or drop
                # this branch for that archetype.
                nconds.append(f"{nd_alias}.arch_type = :h{n}n0t");
                joins[edge_slot] = (
                    f"JOIN anchors {nd_alias} ON {' AND '.join(nconds[1:])}"
                );
                econds[1] = _dir_cond_pinned(
                    e, fid, f"{nd_alias}.id", hop.dir, to_dst, to_src
                );
                joins.append(f"JOIN anchors {e} ON {' AND '.join(econds)}");
            } else {
                joins.append(f"JOIN anchors {nd_alias} ON {' AND '.join(nconds)}");
            }
            order.append(f"{e}.seq");
            order.append(f"{e}.id");
        }
        if edge_slot >= 0 and joins[edge_slot] == '' {
            joins[edge_slot] = f"JOIN anchors {e} ON {' AND '.join(econds)}";
        }
        fid = f"{nd_alias}.id";
    }
    if n == 0 {
        out.sql = (
            'SELECT f0.id, NULL FROM ' 'unnest(CAST(:origin AS uuid[])) AS f0(id)'
        );
        out.params = params;
        return out;
    }
    if mirror is not None {
        sel_parts: list = [];
        # lateral_used: the final hop's mirror row lives inside the t{n}
        # LATERAL alias (built above), already ::text-cast there. Otherwise
        # (no order_col - flat mirror join, unchanged) it's the plain n{n}.
        src_alias = ('t' + str(n)) if lateral_used else f"n{n}";
        sel_parts.append(f"{src_alias}.id");
        sel_parts.append(f"{src_alias}.root_id");
        sel_parts.append(f"{src_alias}.acl_all");
        sel_parts.append(f"{src_alias}.acl_spec");
        sel_parts.append(f"{src_alias}.frag");
        for c in mirror['fcols'] {
            # ::text: same wire-format pin as store.load_mirror_rows - both
            # paths feed query_planner._stream_from_mirror, which decodes.
            # (The ORDER BY below still sorts on the raw jsonb column.)
            if lateral_used {
                sel_parts.append(f"{src_alias}." + c);
            } else {
                sel_parts.append(f"{src_alias}." + c + '::text');
            }
        }
        sel = ', '.join(sel_parts);
    } else {
        sel = f"n{n}.id, e{n}.id";
    }
    trav_order = 'f0.ord, ' + ', '.join(order);
    if global_used {
        # ARRAY(subquery), not IN (subquery), deliberately: IN lets the planner
        # hash-join the traversal to the mirror, which throws the sort index
        # away and re-sorts every candidate row (measured 1.72ms vs 0.14ms).
        # ARRAY() is an InitPlan - evaluated once, then a plain
        # `= ANY(<const array>)` FILTER on top of an ordered index scan that
        # stops at the cap.
        cap_key = 'topk_cap';
        params[cap_key] = int(mirror.get('limit', 0)) + int(mirror.get('slack', 0));
        gconds = [
            f"n{n}." + mirror['endpoint_col'] + ' = ANY(ARRAY(SELECT ' + src_fid
                + ' FROM unnest(CAST(:origin AS uuid[])) WITH ORDINALITY AS '
                + 'f0(id, ord) LEFT JOIN anchors s1 ON s1.id = f0.id '
                + ' '.join(joins) + '))'
        ];
        if acl_sql is not None {
            gconds.append(acl_sql.replace('%M%', f"n{n}"));
        }
        # No traversal-order tie-break to restore: the edge rows are not in
        # this statement at all. Rows come back in sort-column order, which is
        # the order the caller's pipeline wants anyway; ties between two rows
        # with the SAME sort value now break on nothing in particular where
        # they used to break on (edge seq, edge id). Same class of change the
        # LATERAL branch already declares, and gated by the page-parity oracle.
        out.sql = (
            'SELECT ' + sel + ' FROM ' + mirror['table'] + f" n{n} WHERE "
            + ' AND '.join(gconds)
            + ' ORDER BY ' + f"n{n}." + mirror['order_col'] + ' '
            + ('DESC' if mirror.get('desc') else 'ASC')
            + f' LIMIT :{cap_key}'
        );
        out.params = params;
        return out;
    }
    base_sql = (
        'FROM unnest(CAST(:origin AS uuid[])) WITH ORDINALITY AS f0(id, ord) '
        + 'LEFT JOIN anchors s1 ON s1.id = f0.id '
        + ' '.join(joins)
    );
    if mirror is not None and mirror.get('order_col') is not None {
        # Distributed top-K: keep only this source's top-(limit+slack) by the
        # pipeline's sort column, tie-broken by traversal order (matching the
        # walker's stable sort), then restore traversal order for the caller.
        dirn = 'DESC' if mirror.get('desc') else 'ASC';
        cap_key = 'topk_cap';
        params[cap_key] = int(mirror.get('limit', 0)) + int(mirror.get('slack', 0));
        ord_alias_parts: list = [];
        ord_inner_parts: list = [];
        ord_names = trav_order.split(', ');
        k = 0;
        for oc in ord_names {
            k += 1;
            ord_alias_parts.append(oc + ' AS _tk' + str(k));
            ord_inner_parts.append('_tk' + str(k));
        }
        inner_sel = sel + ', ' + ', '.join(ord_alias_parts);
        # With the LATERAL the sort column is only reachable through the
        # t{n} alias it exposes; the flat join sorts on the mirror column
        # directly.
        sort_col = (
            ('t' + str(n) + '._ordcol')
                if lateral_used
                else ('n' + str(n) + '.' + mirror['order_col'])
        );
        out.sql = (
            'SELECT * FROM ('
            + 'SELECT ' + inner_sel + ' ' + base_sql
            + ' ORDER BY ' + sort_col + ' ' + dirn
            + ', ' + trav_order
            + f' LIMIT :{cap_key}'
            + ') _topk ORDER BY ' + ', '.join(ord_inner_parts)
        );
        out.params = params;
        return out;
    }
    out.sql = (
        'SELECT ' + sel + ' '
        + base_sql
        + ' ORDER BY '
        + trav_order
    );
    out.params = params;
    return out;
}
