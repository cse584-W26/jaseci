"""StreamProofPass: prove chain results are only trivially observed.

For each walker archetype, audits every use of every chain-expression
(EdgeRefTrailer) result across the walker's abilities. If ALL uses fall
inside a closed whitelist - element flow into local lists, len/subscript,
jid(), reads of a recorded field set, sort with a single-field key, use as
the origin of another chain, and final `report` - the walker is stamped
with `stream_fields`, which PyastGenPass emits as a
`__jac_stream_fields__` class attribute for the runtime's zero-
materialization path.

Soundness stance: the audit is a flow-INSENSITIVE taint walk over the
compiler's symbol def-use links. Flow-insensitivity can only OVER-taint
(audit uses no real execution reaches), so approval is conservative: any
context outside the whitelist - mutation, escape to a call, visit/spawn/
connect/disconnect anywhere in the walker, identity-sensitive membership,
dynamic attribute access - withholds the annotation and the runtime keeps
today's full-materialization path. The runtime additionally re-guards
every dynamic assumption and hydrates on any surprise, so even a bug here
degrades to slow-correct, never to wrong.
"""
import jaclang.jac0core.unitree as uni;
import from jaclang.jac0core.passes.uni_pass { UniPass }

glob _JID_NAMES: tuple = ('jid', );
glob _KILL_TOKENS: tuple = ('visit', 'spawn', 'disconnect', 'del');


def _ancestor(n: object, kinds: tuple, stop: object = None) -> (object | None) {
    p = getattr(n, 'parent', None);
    while p is not None and p is not stop {
        if isinstance(p, kinds) {
            return p;
        }
        p = getattr(p, 'parent', None);
    }
    return None;
}


def _is_stream_list_expr(e: object) -> bool {
    # EdgeRefTrailer, or `+`-concat of stream list exprs
    if isinstance(e, uni.EdgeRefTrailer) {
        return True;
    }
    if isinstance(e, uni.BinaryExpr) {
        opv = getattr(getattr(e, 'op', None), 'value', None);
        if opv == '+' {
            return _is_stream_list_expr(e.left) and _is_stream_list_expr(e.right);
        }
    }
    return False;
}


def _single_field_key(fn_node: object) -> (str | None) {
    # A key callable is admissible iff its body is exactly `return x.<field>`.
    body = getattr(fn_node, 'body', None);
    if hasattr(body, 'body') {
        body = body.body;
    }
    stmts = list(body) if body is not None and not isinstance(body, uni.Expr) else [];
    if len(stmts) != 1 or not isinstance(stmts[0], uni.ReturnStmt) {
        return None;
    }
    expr = stmts[0].expr;
    if isinstance(expr, uni.AtomTrailer) and isinstance(expr.right, uni.Name)
        and isinstance(expr.target, uni.Name) {
        return str(expr.right.value);
    }
    return None;
}


def _slice_upper(sl: object) -> (int | None) {
    # [:K] with literal integer K and no start/step
    try {
        slices = getattr(sl, 'slices', None) or [];
        if len(slices) != 1 {
            return None;
        }
        one = slices[0];
        if getattr(one, 'start', None) is not None
            or getattr(one, 'step', None) is not None {
            return None;
        }
        stop = getattr(one, 'stop', None);
        v = getattr(stop, 'value', None);
        return int(v) if v is not None else None;
    } except Exception {
        return None;
    }
}


def _lambda_field(lam: object) -> (str | None) {
    body = getattr(lam, 'body', None);
    if isinstance(body, uni.AtomTrailer) and isinstance(body.right, uni.Name)
        and isinstance(body.target, uni.Name) {
        return str(body.right.value);
    }
    return None;
}


class StreamProofPass(UniPass) {
    def enter_archetype(self: StreamProofPass, nd: uni.Archetype) -> None {
        if nd.arch_type.name != 'KW_WALKER' {
            return;
        }
        fields = self._audit_walker(nd);
        if fields is not None {
            nd.stream_fields = tuple(sorted(fields));
        }
    }

    def _audit_walker(
        self: StreamProofPass, w: uni.Archetype
    ) -> (set | None) {
        abilities = w.get_all_sub_nodes(uni.Ability);
        if not abilities {
            return None;
        }
        # cheap walker-wide kills first: any traversal/topology mutation
        # anywhere means chain elements can be arbitrarily observed
        for tok in w.get_all_sub_nodes(uni.Token) {
            if str(getattr(tok, 'value', '')) in _KILL_TOKENS {
                return None;
            }
        }
        if w.get_all_sub_nodes(uni.VisitStmt)
            or w.get_all_sub_nodes(uni.DisconnectOp)
            or w.get_all_sub_nodes(uni.ConnectOp) {
            return None;
        }
        fields: set = set();
        pipe: dict = {};
        found_chain = False;
        for ab in abilities {
            got = self._audit_ability(ab, fields, pipe);
            if got is None {
                return None;
            }
            found_chain = found_chain or got;
        }
        if not found_chain {
            return None;
        }
        # ordered-slice pipeline: exactly one single-field sort followed (in
        # source order) by exactly one constant-bound report slice of the
        # SAME tainted list family -> the runtime may bound each chain fetch
        # to the per-source top-K (distributed top-K containment; runtime
        # re-guards with drop-count refill, so this is advisory).
        sorts = pipe.get('sorts', []);
        slices = pipe.get('slices', []);
        if len(sorts) == 1 and len(slices) == 1 {
            (sf, srev, sline) = sorts[0];
            (upper, pline) = slices[0];
            if upper is not None and sline < pline {
                w.stream_pipeline = (str(sf), bool(srev), int(upper));
            }
        }
        return fields;
    }

    def _audit_ability(
        self: StreamProofPass, ab: uni.Ability, fields: set, pipe: dict
    ) -> (bool | None) {
        chains = ab.get_all_sub_nodes(uni.EdgeRefTrailer);
        if not chains {
            return False;
        }
        # taint seeding: sym -> 'list' | 'elem'
        taint: dict = {};
        pending: list = [];

        def taint_sym(nm: object, kind: str) -> None {
            s = getattr(nm, 'sym', None);
            if s is None {
                raise ValueError('unlinked symbol');
            }
            if taint.get(id(s)) != kind {
                taint[id(s)] = kind;
                pending.append((s, kind));
            }
        }

        try {
            for ch in chains {
                asg = _ancestor(ch, (uni.Assignment, ));
                fr = _ancestor(ch, (uni.InForStmt, ));
                rpt = _ancestor(ch, (uni.ReportStmt, ));
                if asg is not None and _is_stream_list_expr(asg.value) {
                    tgt = asg.target[0] if getattr(asg, 'target', None) else None;
                    if isinstance(tgt, uni.Name) {
                        taint_sym(tgt, 'list');
                        continue;
                    }
                    return None;
                }
                if fr is not None and _is_stream_list_expr(getattr(fr, 'collection', None)) {
                    tgt = fr.target;
                    if isinstance(tgt, uni.Name) {
                        taint_sym(tgt, 'elem');
                        continue;
                    }
                    return None;
                }
                if rpt is not None {
                    continue;   # chain reported directly: serialization sink
                }
                cmp = _ancestor(ch, (uni.CompareExpr, ));
                if cmp is not None and ch in getattr(cmp, 'rights', []) {
                    # in-place membership test lowers to chain_has (no
                    # materialized elements escape) - see exit_compare_expr
                    continue;
                }
                # chain used as a sub-expression of another chain (origin) is
                # covered by the outer chain's own audit
                if _ancestor(ch, (uni.EdgeRefTrailer, )) is not None {
                    continue;
                }
                return None;
            }
            # propagate + audit until stable
            while pending {
                (s, kind) = pending.pop();
                for use in list(getattr(s, 'uses', [])) + [
                    d
                    for d in list(getattr(s, 'defn', []))
                    if _ancestor(d, (uni.Assignment, )) is not None
                ] {
                    if not self._use_ok(use, kind, fields, taint_sym, pipe) {
                        return None;
                    }
                }
            }
        } except ValueError {
            return None;
        }
        return True;
    }

    def _use_ok(
        self: StreamProofPass,
        use: object,
        kind: str,
        fields: set,
        taint_sym: object,
        pipe: dict
    ) -> bool {
        parent = getattr(use, 'parent', None);

        # -- assignment: seeding defn (RHS stream expr) or alias LHS<-RHS
        asg = _ancestor(use, (uni.Assignment, ));
        if asg is not None {
            tgt = asg.target[0] if getattr(asg, 'target', None) else None;
            if use is tgt {
                # this symbol being (re)defined: fine iff RHS is a stream
                # expr, a tainted name, or tainted-name subscript; the seeding
                # walk and the cases below cover those. Anything else means
                # the var is reused for foreign data - drop taint soundly by
                # keeping the annotation only if RHS is itself admissible.
                v = asg.value;
                if _is_stream_list_expr(v) or isinstance(v, uni.Name) {
                    return True;
                }
                if isinstance(v, uni.ListVal) and not getattr(v, 'values', None) {
                    # (re)binding to a fresh empty list: no elements to observe
                    return True;
                }
                if isinstance(v, uni.AtomTrailer)
                    and isinstance(v.target, uni.Name)
                    and isinstance(getattr(v, 'right', None), uni.IndexSlice) {
                    return True;
                }
                return False;
            }
            # symbol on the RHS of an assignment: alias the LHS
            if isinstance(asg.value, uni.Name) and asg.value is use {
                if isinstance(tgt, uni.Name) {
                    taint_sym(tgt, kind);
                    return True;
                }
                return False;
            }
        }

        # -- inside a report: serialization sink (dict/list literals included)
        if _ancestor(use, (uni.ReportStmt, )) is not None {
            if kind == 'list' and isinstance(parent, uni.AtomTrailer)
                and parent.target is use
                and isinstance(getattr(parent, 'right', None), uni.IndexSlice) {
                pipe.setdefault('slices', []).append(
                    (_slice_upper(parent.right), parent.loc.first_line)
                );
            }
            return True;
        }

        # -- for t in X: taints the loop target as element
        fr = _ancestor(use, (uni.InForStmt, ));
        if fr is not None and getattr(fr, 'collection', None) is not None {
            coll = fr.collection;
            if coll is use or (isinstance(coll, uni.Name) and coll is use) {
                tgt = fr.target;
                if isinstance(tgt, uni.Name) and kind == 'list' {
                    taint_sym(tgt, 'elem');
                    return True;
                }
                return False;
            }
        }

        # -- truthiness / conditions: bool(list) observes nothing per-element
        if kind == 'list' and isinstance(parent, (uni.IfStmt, uni.ElseIf)) {
            return True;
        }

        # -- atom trailer contexts
        if isinstance(parent, uni.AtomTrailer) and parent.target is use {
            right = getattr(parent, 'right', None);
            gp = getattr(parent, 'parent', None);
            # X[i] / X[a:b]
            if isinstance(right, uni.IndexSlice) {
                asg2 = _ancestor(parent, (uni.Assignment, ));
                if asg2 is not None and asg2.value is parent {
                    tgt2 = asg2.target[0] if getattr(asg2, 'target', None) else None;
                    if isinstance(tgt2, uni.Name) {
                        taint_sym(tgt2, 'elem' if kind == 'list' else 'elem');
                        return True;
                    }
                }
                if _ancestor(parent, (uni.ReportStmt, )) is not None {
                    if kind == 'list' {
                        pipe.setdefault('slices', []).append(
                            (_slice_upper(right), parent.loc.first_line)
                        );
                    }
                    return True;
                }
                return False;
            }
            # X.method(...) or t.field
            if isinstance(right, uni.Name) {
                mname = str(right.value);
                call = gp if isinstance(gp, uni.FuncCall)
                    and gp.target is parent else None;
                if kind == 'list' {
                    if call is None {
                        return False;
                    }
                    if mname == 'append' {
                        return True;
                    }
                    if mname == 'sort' {
                        return self._sort_ok(call, fields, pipe);
                    }
                    return False;
                }
                # element attribute access
                if call is not None {
                    return False;   # t.method() observes arbitrary behaviour
                }
                if _ancestor(parent, (uni.DeleteStmt, )) is not None {
                    return False;
                }
                asg3 = _ancestor(parent, (uni.Assignment, ));
                if asg3 is not None and parent in list(getattr(asg3, 'target', [])) {
                    return False;   # t.field = ... : mutation
                }
                fields.add(mname);
                return True;
            }
            return False;
        }

        # -- function calls with the symbol as an argument
        call = _ancestor(use, (uni.FuncCall, ));
        if call is not None {
            tgtc = getattr(call, 'target', None);
            cname = str(getattr(tgtc, 'value', '')) if isinstance(tgtc, uni.Name)
                else '';
            if cname == 'len' and kind == 'list' {
                return True;
            }
            if cname in _JID_NAMES and kind == 'elem' {
                return True;
            }
            # X.append(t): the ELEMENT as the argument of an append on any
            # local list - the list becomes a serialization-bound container
            if isinstance(tgtc, uni.AtomTrailer)
                and isinstance(getattr(tgtc, 'right', None), uni.Name)
                and str(tgtc.right.value) == 'append'
                and isinstance(tgtc.target, uni.Name)
                and kind == 'elem' {
                taint_sym(tgtc.target, 'list');
                return True;
            }
            return False;
        }

        # -- element used as the origin of another chain expression
        if kind == 'elem' and _ancestor(use, (uni.EdgeRefTrailer, )) is not None {
            return True;
        }

        # -- BinaryExpr `+` of tainted lists: handled at the seeding site
        if kind == 'list' and isinstance(parent, uni.BinaryExpr)
            and str(getattr(parent.op, 'value', '')) == '+' {
            fr2 = _ancestor(parent, (uni.InForStmt, uni.Assignment, uni.ReportStmt));
            return fr2 is not None;
        }

        return False;
    }

    def _sort_ok(
        self: StreamProofPass, call: uni.FuncCall, fields: set, pipe: dict
    ) -> bool {
        key_field: (str | None) = None;
        for p in list(getattr(call, 'params', []) or []) {
            if isinstance(p, uni.KWPair) {
                pname = str(getattr(p.key, 'value', '')) if p.key is not None else '';
                if pname == 'reverse' {
                    continue;
                }
                if pname == 'key' {
                    v = p.value;
                    if isinstance(v, uni.LambdaExpr) {
                        key_field = _lambda_field(v);
                    } elif isinstance(v, uni.Name) {
                        s = getattr(v, 'sym', None);
                        decl = getattr(s, 'decl', None) if s is not None else None;
                        fn = getattr(decl, 'parent', None);
                        target = fn if isinstance(fn, uni.Ability) else (
                            decl if isinstance(decl, uni.Ability) else None
                        );
                        key_field = _single_field_key(target)
                            if target is not None else None;
                    }
                    if key_field is None {
                        return False;
                    }
                    fields.add(key_field);
                    reverse = False;
                    for p2 in list(getattr(call, 'params', []) or []) {
                        if isinstance(p2, uni.KWPair)
                            and str(getattr(p2.key, 'value', '')) == 'reverse' {
                            rv = getattr(p2, 'value', None);
                            reverse = bool(getattr(rv, 'value', None) == 'True');
                        }
                    }
                    pipe.setdefault('sorts', []).append(
                        (key_field, reverse, call.loc.first_line)
                    );
                    continue;
                }
                return False;
            }
            return False;   # positional args to sort: not admissible
        }
        return True;
    }
}
