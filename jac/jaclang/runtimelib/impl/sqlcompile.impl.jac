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


def _pred_cond(alias: str, p: QPred, params: dict, pfx: str) -> (str | None) {
    if not _ident_ok(p.field) or not _pushable_value(p.value) {
        return None;
    }
    expr = f"{alias}.props->'archetype'->'{p.field}'";
    if p.op == 'in' {
        vals = list(p.value) if isinstance(p.value, (list, tuple, set)) else [p.value];
        parts: list[str] = [];
        for (i, v) in enumerate(vals) {
            key = f"{pfx}v{i}";
            params[key] = _scalar(v);
            parts.append(f"to_jsonb(CAST(:{key} AS {_sql_type_of(v)}))");
        }
        if not parts {
            return 'FALSE';
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


def _nd_types(hop: QHop) -> list {
    nd = hop.nd;
    if nd is None {
        return [];
    }
    return list(nd) if isinstance(nd, tuple) else [nd];
}


impl compile_query(
    q: GraphQuery, upto: int, mirror: (dict | None) = None
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
    joins: list[str] = [];
    order: list[str] = [];
    fid = 'f0.id';
    n = 0;
    for (i, hop) in enumerate(q.hops[:upto]) {
        n = i + 1;
        e = f"e{n}";
        nd_alias = f"n{n}";
        pfx_e = f"h{n}e";
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
        if hop.`edge is not None {
            econds.append(_type_cond(e, hop.`edge.__name__, params, pfx_e));
        }
        for (j, p) in enumerate(hop.epreds) {
            cond = _pred_cond(e, p, params, f"{pfx_e}p{j}");
            if cond is None {
                out.residual.setdefault(i, []).append(p);
            } else {
                econds.append(cond);
            }
        }
        joins.append(f"JOIN anchors {e} ON {' AND '.join(econds)}");
        nconds = [
            f"{nd_alias}.id = {_other_expr(e, fid)}",
            f"{nd_alias}.kind = 'NodeAnchor'"
        ];
        for (k, nt) in enumerate(_nd_types(hop)) {
            tname = str(getattr(nt, '__name__', ''));
            if tname {
                nconds.append(_type_cond(nd_alias, tname, params, f"h{n}n{k}"));
            }
        }
        for (j, p) in enumerate(hop.preds) {
            cond = _pred_cond(nd_alias, p, params, f"h{n}np{j}");
            if cond is None {
                out.residual.setdefault(i, []).append(p);
            } else {
                nconds.append(cond);
            }
        }
        want = hop.only_ids();
        if want is not None {
            key = f"h{n}only";
            params[key] = [str(x) for x in want];
            nconds.append(f"{nd_alias}.id = ANY(CAST(:{key} AS uuid[]))");
        }
        is_final = (i == len(q.hops[:upto]) - 1);
        if mirror is not None and is_final {
            mconds = [f"{nd_alias}.id = {_other_expr(e, fid)}"];
            want_m = hop.only_ids();
            if want_m is not None {
                key_m = f"h{n}only";
                params[key_m] = [str(x) for x in want_m];
                mconds.append(f"{nd_alias}.id = ANY(CAST(:{key_m} AS uuid[]))");
            }
            joins.append(
                'JOIN ' + mirror['table'] + f" {nd_alias} ON "
                    + ' AND '.join(mconds)
            );
        } else {
            joins.append(f"JOIN anchors {nd_alias} ON {' AND '.join(nconds)}");
        }
        order.append(f"{e}.seq");
        order.append(f"{e}.id");
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
        sel_parts.append(f"n{n}.id");
        sel_parts.append(f"n{n}.root_id");
        sel_parts.append(f"n{n}.acl_all");
        sel_parts.append(f"n{n}.acl_spec");
        sel_parts.append(f"n{n}.frag");
        for c in mirror['fcols'] {
            sel_parts.append(f"n{n}." + c);
        }
        sel = ', '.join(sel_parts);
    } else {
        sel = f"n{n}.id, e{n}.id";
    }
    out.sql = (
        'SELECT ' + sel + ' '
        f"FROM unnest(CAST(:origin AS uuid[])) WITH ORDINALITY AS f0(id, ord) "
        f"LEFT JOIN anchors s1 ON s1.id = f0.id "
        + ' '.join(joins)
        + ' ORDER BY f0.ord, '
        + ', '.join(order)
    );
    out.params = params;
    return out;
}
