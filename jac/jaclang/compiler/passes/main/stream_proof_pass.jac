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
# Item #25: a walker EffectPass has already PROVED read-only may keep its
# visits - each eligible VisitStmt is lowered by PyastGenPass to a plain
# for-loop that dispatches the walker's own entry abilities by isinstance,
# which makes the visit form exactly the chain form this pass already
# audits. 'visit' therefore stops being a kill token for those walkers;
# spawn/disconnect/del still kill (they cannot appear in an RO walker
# anyway, but the belt stays).
glob _KILL_TOKENS_VISIT_OK: tuple = ('spawn', 'disconnect', 'del');


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
    if not isinstance(body, uni.Expr) {
        # Braced lambda body - `lambda (t: Tweet) { t.created_at; }`, the
        # idiomatic jac spelling used by the littleX walkers. body is then a
        # statement list, not an Expr. LambdaExpr.tail_return_expr is the
        # implicit return and already refuses anything but a single
        # expression statement, which is exactly this rule's admissibility
        # condition - so no soundness is given up by accepting it.
        body = lam.tail_return_expr();
    }
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
        self._pending_visit_stamps: list = [];
        try {
            fields = self._audit_walker(nd);
        } except Exception {
            fields = None;
        }
        import os;
        if os.environ.get('JAC_STREAM_DEBUG') {
            print('STREAMPROOF', str(nd.name), fields);
        }
        if fields is not None {
            nd.stream_fields = tuple(sorted(fields));
            # visit lowering only on a fully approved walker: the loop form
            # is what the audit vouched for, so stamp the visits together
            # with the fields, never separately
            for (vs, dispatch) in self._pending_visit_stamps {
                vs.stream_lower = tuple(dispatch);
            }
        }
        self._pending_visit_stamps = [];
    }

    def _audit_walker(
        self: StreamProofPass, w: uni.Archetype
    ) -> (set | None) {
        abilities = w.get_all_sub_nodes(uni.Ability);
        if not abilities {
            return None;
        }
        # Item #25: visits are admissible ONLY under EffectPass's read-only
        # proof (schedule runs it first); everything the loop form could
        # observe is then audited below exactly like chain elements.
        visit_mode = bool(getattr(w, 'effect_readonly', False));
        visits = w.get_all_sub_nodes(uni.VisitStmt);
        # cheap walker-wide kills first: any traversal/topology mutation
        # anywhere means chain elements can be arbitrarily observed
        kill_toks = _KILL_TOKENS_VISIT_OK if (visit_mode and visits) else _KILL_TOKENS;
        for tok in w.get_all_sub_nodes(uni.Token) {
            if str(getattr(tok, 'value', '')) in kill_toks {
                return None;
            }
        }
        if w.get_all_sub_nodes(uni.DisconnectOp)
            or w.get_all_sub_nodes(uni.ConnectOp) {
            return None;
        }
        elem_abilities: set = set();
        if visits {
            if not visit_mode {
                return None;
            }
            dispatch = self._visit_dispatch(w, abilities, elem_abilities);
            if dispatch is None {
                return None;
            }
            for vs in visits {
                if not self._visit_ok(vs) {
                    return None;
                }
            }
            for vs in visits {
                self._pending_visit_stamps.append((vs, dispatch));
            }
        }
        # item #25: `self.<field>` references have no linked symbol on the
        # attribute Name, so build the walker-wide use index by shape once;
        # _audit_field_uses audits a field's every reference on first taint.
        self._field_refs = {};
        self._field_ok = set();
        for at in w.get_all_sub_nodes(uni.AtomTrailer) {
            if getattr(at, 'is_attr', False)
                and isinstance(getattr(at, 'right', None), uni.Name)
                and isinstance(at.target, uni.SpecialVarRef)
                and str(getattr(at.target, 'sym_name', '')) == 'self' {
                self._field_refs.setdefault(str(at.right.value), []).append(at);
            }
        }
        fields: set = set();
        pipe: dict = {};
        found_chain = bool(visits);
        for ab in abilities {
            got = self._audit_ability(
                ab, fields, pipe,
                bool(visits), id(ab) in elem_abilities
            );
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

    def _visit_dispatch(
        self: StreamProofPass, w: uni.Archetype, abilities: list, elem_abilities: set
    ) -> (list | None) {
        # The loop form dispatches the walker's own entry abilities by
        # isinstance, in declaration order - the same per-node dispatch the
        # engine performs. Provable only for the simple shape: every entry
        # ability tagged with ONE plain type name, one ability per type, no
        # non-Root exit abilities (they would fire per visited node), and
        # nested visits only inside Root-tagged abilities (a visit inside a
        # per-node ability would turn the engine's BFS into this form's DFS
        # and reorder tie-broken results).
        dispatch: list = [];
        seen_types: set = set();
        for ab in abilities {
            sig = getattr(ab, 'signature', None);
            if not isinstance(sig, uni.EventSignature) {
                continue;   # plain method: never engine-dispatched
            }
            ev = str(getattr(getattr(sig, 'event', None), 'name', ''));
            tag = getattr(sig, 'arch_tag_info', None);
            tname = '';
            if isinstance(tag, uni.Name) {
                tname = str(getattr(tag, 'sym_name', '') or tag.value);
            }
            nr = getattr(ab, 'name_ref', None);
            aname = str(getattr(nr, 'sym_name', '')) if nr is not None else '';
            if not tname or not aname {
                return None;
            }
            if ev == 'KW_EXIT' {
                if tname != 'Root' {
                    return None;
                }
                continue;   # Root exit stays engine-driven at spawn end
            }
            if ev != 'KW_ENTRY' {
                return None;
            }
            if tname in seen_types {
                return None;
            }
            seen_types.add(tname);
            if tname != 'Root' {
                if ab.get_all_sub_nodes(uni.VisitStmt) {
                    return None;
                }
                elem_abilities.add(id(ab));
            }
            dispatch.append((tname, aname));
        }
        if not dispatch {
            return None;
        }
        return dispatch;
    }

    def _visit_ok(self: StreamProofPass, vs: uni.VisitStmt) -> bool {
        # Only the plain tail-position `visit [expr];` form: inline loop
        # execution is observationally identical to the engine's queue
        # exactly when nothing runs after the visit but other visits -
        # queued entry abilities would otherwise fire LATER than the loop.
        if not getattr(vs, 'from_walker', False) {
            return False;
        }
        if getattr(vs, 'insert_loc', None) is not None
            or getattr(vs, 'else_body', None) is not None {
            return False;
        }
        c: object = vs;
        while True {
            p = getattr(c, 'parent', None);
            if p is None {
                return False;
            }
            stmts: list = [];
            terminal = False;
            if isinstance(p, uni.Ability) or isinstance(p, uni.ImplDef) {
                body = getattr(p, 'body', None);
                stmts = list(body) if isinstance(body, (list, tuple)) else [];
                terminal = True;
            } elif isinstance(p, (uni.IfStmt, uni.ElseStmt)) {
                stmts = list(getattr(p, 'body', []) or []);
            } else {
                return False;
            }
            seen_c = False;
            in_list = False;
            for s in stmts {
                if s is c {
                    seen_c = True;
                    in_list = True;
                    continue;
                }
                if seen_c and not isinstance(s, uni.VisitStmt) {
                    return False;
                }
            }
            if not in_list {
                return False;   # inside a condition / else branch / unknown slot
            }
            if terminal {
                return True;
            }
            c = p;
        }
    }

    def _audit_ability(
        self: StreamProofPass, ab: uni.Ability, fields: set, pipe: dict,
        visit_mode: bool = False, here_elem: bool = False
    ) -> (bool | None) {
        chains = ab.get_all_sub_nodes(uni.EdgeRefTrailer);
        if not chains and not here_elem {
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
                if visit_mode and _ancestor(ch, (uni.VisitStmt, )) is not None {
                    # the visit target itself: becomes the lowered loop's
                    # iterable; its ELEMENTS are audited through the entry
                    # ability's `here` taint below
                    continue;
                }
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
            if here_elem {
                # item #25: in the lowered loop this ability's `here` IS a
                # chain element. Special vars carry no linked symbol, so the
                # refs themselves ARE the use list - audit each directly
                # with the ordinary elem rules (reads recorded, escapes and
                # mutations decline).
                for sv in ab.get_all_sub_nodes(uni.SpecialVarRef) {
                    if str(getattr(sv, 'sym_name', '')) == 'here' {
                        if not self._use_ok(sv, 'elem', fields, taint_sym, pipe) {
                            return None;
                        }
                    }
                }
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

    def _audit_field_uses(
        self: StreamProofPass, fname: str, fields: set,
        taint_sym: object, pipe: dict
    ) -> bool {
        # A walker field became a serialization-bound container (item #25:
        # `self.feed.append(here)` in a lowered visit walker). Audit EVERY
        # `self.<fname>` reference in the walker as a 'list' use - the
        # trailer node plays the role a local Name plays for chain walkers.
        if fname in self._field_ok {
            return True;
        }
        self._field_ok.add(fname);   # pre-mark: the refs include the append
        for tr in self._field_refs.get(fname, []) {
            if not self._use_ok(tr, 'list', fields, taint_sym, pipe) {
                return False;
            }
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
        # Item #25: a WALKER FIELD reference (`self.feed`) plays the role a
        # local name plays for chain walkers - visit walkers accumulate into
        # `has` state instead of locals. Promote the use to the whole
        # `self.<field>` trailer and audit THAT in its context; every branch
        # below then applies unchanged (append/sort/report/slice/loop...).
        if isinstance(parent, uni.AtomTrailer)
            and getattr(parent, 'right', None) is use
            and getattr(parent, 'is_attr', False)
            and isinstance(parent.target, uni.SpecialVarRef)
            and str(getattr(parent.target, 'sym_name', '')) == 'self' {
            use = parent;
            parent = getattr(use, 'parent', None);
        }

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
                if _ancestor(parent, (uni.EdgeRefTrailer, )) is not None {
                    # X[i] as the ORIGIN of a chain (`visit [mine[0]-->...]`):
                    # the element is consumed by the chain's own audit, same
                    # rule as a bare elem used as a chain origin
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
            # self.<field>.append(t): same thing into WALKER state (item #25
            # visit walkers) - taint the field's symbol; its other uses are
            # promoted to the full trailer by the normalization above
            if isinstance(tgtc, uni.AtomTrailer)
                and isinstance(getattr(tgtc, 'right', None), uni.Name)
                and str(tgtc.right.value) == 'append'
                and isinstance(tgtc.target, uni.AtomTrailer)
                and getattr(tgtc.target, 'is_attr', False)
                and isinstance(tgtc.target.right, uni.Name)
                and isinstance(tgtc.target.target, uni.SpecialVarRef)
                and str(getattr(tgtc.target.target, 'sym_name', '')) == 'self'
                and kind == 'elem' {
                return self._audit_field_uses(
                    str(tgtc.target.right.value), fields, taint_sym, pipe
                );
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
