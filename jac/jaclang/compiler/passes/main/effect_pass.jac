"""EffectPass: prove a walker performs no persistent-store effect.

For each walker archetype, audits every ability body (impl-file bodies
resolved through the decl's `body` link, since they are not in the decl's
subtree) plus the archetype's own subtree. If NO construct that can write
the store is found - topology ops (connect/disconnect/delete), spawn,
grant/revoke, an attribute store whose target is anything but the walker's
own `self`, an index store into anything but a provably walker-local
container, or a call that cannot be resolved to a provably effect-free
callee - the walker is stamped `effect_readonly`, which PyastGenPass emits
as a `__jac_readonly__` class attribute. The server consults the stamp at
spawn (OR'd with the JAC_RO_WALKERS env override list for one release) and
runs the request in SNAPSHOT READ ONLY isolation, skipping the commit
funnel.

Unlike StreamProofPass (which is stricter: it also forbids `visit`, since
it must prove chain elements are only trivially observed), a read-only
walker MAY traverse: `visit` moves the walker, it writes nothing. When a
walker visits, every node/edge entry-ability in the module must itself
audit effect-free, because visiting fires them.

Distinct from EndpointEffectPass (jac0core/passes), which classifies
endpoints for the interop manifest and IGNORES what it cannot resolve:
this pass must PROVE, so anything unresolvable declines the stamp.

Soundness stance: REFUSAL OVER WRONGNESS. Any construct the audit does
not understand - a dynamic call, an unresolvable symbol, a method on a
receiver whose provenance is not a fresh walker-local container -
withholds the stamp and the walker keeps today's read-write path (the
status quo). The enforcement layer is fail-loud (a field write inside a
read-only request raises ReadOnlyWalkerError, and Postgres rejects writes
in a READ ONLY transaction), so even a wrong approval degrades to a loud
error, never to a silent lost write.
"""
import jaclang.jac0core.unitree as uni;
import from jaclang.jac0core.constant { SymbolType }
import from jaclang.jac0core.passes { UniPass }

# Tokens whose presence anywhere in an audited body is a walker-wide kill.
# 'visit' is deliberately absent (walker scopes may traverse; callee scopes
# still refuse it via the VisitStmt check).
glob _KILL_TOKENS: tuple = ('spawn', 'disconnect', 'del', 'grant', 'revoke', 'destroy');

# Calls provably free of store effects: object loads (jobj/jclosure/jtopk
# read through the same access-checked runtime path), identity, and pure
# python builtins over already-loaded values.
glob _PURE_CALLS: tuple = (
    'jobj', 'jobj_many', 'jclosure', 'jtopk', 'jadj_pairs',
    'jroot', 'jroot_many',
    'jid', 'isinstance', 'len',
    'range', 'list', 'set', 'dict', 'tuple', 'int', 'str', 'float', 'bool',
    'sorted', 'min', 'max', 'abs', 'sum', 'round', 'enumerate', 'zip',
    'cast', 'repr'
);

# module.attr calls that read the clock only
glob _PURE_MODULE_ATTRS: tuple = (
    ('time', 'perf_counter'), ('time', 'time'), ('time', 'monotonic')
);

# Methods that mutate (or read) only the container they are called on. Safe
# ONLY when the receiver is provably a walker-local container (see
# _recv_safe); a node stored inside such a container defines none of these,
# and a hypothetical collision still lands on the fail-loud read-only
# enforcement, never on a silent write.
glob _CONTAINER_METHODS: tuple = (
    'append', 'add', 'extend', 'insert', 'sort', 'reverse', 'clear', 'pop',
    'popitem', 'update', 'setdefault', 'remove', 'discard', 'get', 'keys',
    'values', 'items', 'count', 'index', 'copy'
);

# constructors of fresh (walker-local) containers
glob _FRESH_CTORS: tuple = ('list', 'set', 'dict', 'tuple', 'sorted');

# special vars that alias graph state: never a safe mutation receiver
glob _GRAPH_VARS: tuple = ('here', 'visitor', 'root', 'entry', 'exit');


def _ancestor(n: object, kinds: tuple) -> (object | None) {
    p = getattr(n, 'parent', None);
    while p is not None {
        if isinstance(p, kinds) {
            return p;
        }
        p = getattr(p, 'parent', None);
    }
    return None;
}


def _enclosing_ability(d: object) -> (object | None) {
    if d is None {
        return None;
    }
    if isinstance(d, uni.Ability) {
        return d;
    }
    return _ancestor(d, (uni.Ability, ));
}


def _subscript_lit(at: object) -> (int | None) {
    # AtomTrailer plain single-index subscript -> the literal int index
    right = getattr(at, 'right', None);
    if not isinstance(right, uni.IndexSlice) or getattr(right, 'is_range', False) {
        return None;
    }
    slices = list(getattr(right, 'slices', []) or []);
    if len(slices) != 1 {
        return None;
    }
    v = getattr(getattr(slices[0], 'start', None), 'lit_value', None);
    return v if isinstance(v, int) else None;
}


def _subscript_lit_str(at: object) -> (str | None) {
    # AtomTrailer plain single-index subscript -> the literal str key
    right = getattr(at, 'right', None);
    if not isinstance(right, uni.IndexSlice) or getattr(right, 'is_range', False) {
        return None;
    }
    slices = list(getattr(right, 'slices', []) or []);
    if len(slices) != 1 {
        return None;
    }
    v = getattr(getattr(slices[0], 'start', None), 'lit_value', None);
    return v if isinstance(v, str) else None;
}


def _truth_only_use(n: object) -> bool {
    # the reference is consumed ONLY as a boolean: `if h`, `if not h`,
    # `... if h else ...`. Such a use cannot pick an element out of h.
    # `not` chains and the CfgExpr wrapper the parser puts around a ternary's
    # condition are both transparent here: neither can select an element.
    cur = n;
    p = getattr(cur, 'parent', None);
    while p is not None {
        if isinstance(p, uni.CfgExpr) and getattr(p, 'expr', None) is cur {
            cur = p;
            p = getattr(cur, 'parent', None);
            continue;
        }
        if isinstance(p, uni.UnaryExpr) and getattr(p, 'operand', None) is cur
            and str(getattr(getattr(p, 'op', None), 'value', '')) == 'not' {
            cur = p;
            p = getattr(cur, 'parent', None);
            continue;
        }
        break;
    }
    return isinstance(p, (uni.IfStmt, uni.IfElseExpr))
        and getattr(p, 'condition', None) is cur;
}


def _single_element_use(w: uni.Archetype, hsym: object, tgt: object) -> bool {
    # Item #24, second inference shape: the walker reads the closure result
    # as ONE element. Every reference to the result symbol is either `h[0]`
    # or a bare emptiness test, so at most the first row is ever consumed and
    # limit=1 is sound by the same containment argument as the sort+slice
    # rule - the builtin's sufficiency contract is "the `limit` NEAREST
    # matches", so under the stamp `h[0]` is the nearest match rather than an
    # arbitrary one (a refinement of the unordered full closure, which is the
    # only reading of "first" a distance-carrying builtin can support).
    # ANY other use - a loop, a slice, len(), passing it to a call, an index
    # that is not 0 - withholds the stamp: refusal over wrongness.
    saw_elem = False;
    for nm in UniPass.get_all_sub_nodes(nd=w, typ=uni.Name) {
        if getattr(nm, 'sym', None) is not hsym or nm is tgt {
            continue;
        }
        p = getattr(nm, 'parent', None);
        if isinstance(p, uni.AtomTrailer) and getattr(p, 'target', None) is nm {
            if _subscript_lit(p) != 0 {
                return False;
            }
            saw_elem = True;
            continue;
        }
        if not _truth_only_use(nm) {
            return False;
        }
    }
    return saw_elem;
}


def _resolved_bodies(owner: object) -> list {
    # audit roots for an archetype/ability: impl-file bodies are linked, not
    # nested, so the decl subtree alone is NOT sufficient
    resolver = getattr(owner, '_get_impl_resolved_body', None);
    if resolver is not None {
        try {
            resolved = resolver();
            if isinstance(resolved, list) {
                return resolved;
            }
        } except Exception {
        }
    }
    body = getattr(owner, 'body', None);
    if isinstance(body, list) {
        return list(body);
    }
    if isinstance(body, uni.ImplDef) {
        return [body];
    }
    return [];
}


# --- T6: field-usage projection for jobj / jobj_many hydration --------------
# Calls whose result the walker observes ONLY through attribute reads,
# jid(), isinstance() and truth tests can be hydrated from the archetype's
# mirror columns instead of the full anchor blob. The proof is over NAMES,
# not symbols: Jac's if/for blocks are symbol scopes but compile to one flat
# Python frame, so a same-named use anywhere in the walker may observe the
# binding. Uses in a SIBLING branch of an if/elif/else that no loop encloses
# can never see it (exactly one branch runs per frame) and are excluded;
# every other use must be one of the admissible shapes or the site is
# declined - refusal over wrongness, per site.

# calls whose ONLY observation of an argument is its identity
glob _IDENTITY_CALLS: tuple = ('jid', );


def _walk(nd: object, typ: type, out: list) -> list {
    # brute-force subtree collection over .kid: the per-node _sub_node_tab
    # is not guaranteed complete for every module shape, and a missed Name
    # would be a missed USE - unsound for this audit
    if isinstance(nd, typ) {
        out.append(nd);
    }
    for k in list(getattr(nd, 'kid', []) or []) {
        _walk(k, typ, out);
    }
    return out;
}


def _branch_of(ifs: object, child: object) -> str {
    if child is getattr(ifs, 'else_body', None) {
        return 'else';
    }
    for st in list(getattr(ifs, 'body', []) or []) {
        if st is child {
            return 'body';
        }
    }
    return 'cond';
}


def _sibling_branch(use: object, bind: object) -> bool {
    # True iff `use` and `bind` sit in different arms (body vs else_body) of
    # the same if-statement and no loop encloses that statement - the only
    # case where a flat-frame variable bound in one arm is provably never
    # observed in the other.
    chain: dict = {};
    cur = bind;
    p = getattr(cur, 'parent', None);
    while p is not None {
        chain[id(p)] = cur;
        cur = p;
        p = getattr(cur, 'parent', None);
    }
    cur = use;
    p = getattr(cur, 'parent', None);
    while p is not None {
        if id(p) in chain {
            if not isinstance(p, uni.IfStmt) {
                return False;
            }
            if _ancestor(p, (uni.InForStmt, uni.WhileStmt)) is not None {
                return False;
            }
            a = _branch_of(p, cur);
            b = _branch_of(p, chain[id(p)]);
            return a != b and a != 'cond' and b != 'cond';
        }
        cur = p;
        p = getattr(cur, 'parent', None);
    }
    return False;
}


def _on_store_path(n: object) -> bool {
    # is `n` (or anything containing it) an assignment target?
    cur = n;
    p = getattr(cur, 'parent', None);
    while p is not None {
        if isinstance(p, uni.Assignment) {
            for t in list(getattr(p, 'target', []) or []) {
                if t is cur {
                    return True;
                }
            }
            return False;
        }
        if isinstance(p, (uni.CodeBlockStmt, uni.Ability, uni.Archetype)) {
            return False;
        }
        cur = p;
        p = getattr(cur, 'parent', None);
    }
    return False;
}


def _is_none_lit(e: object) -> bool {
    return isinstance(e, uni.Null) or str(getattr(e, 'value', '')) == 'None';
}


def _call_name(fc: object) -> str {
    t = getattr(fc, 'target', None);
    if isinstance(t, uni.Name) {
        return str(getattr(t, 'sym_name', '') or t.value);
    }
    return '';
}


def _projection_of(scopes: list, bind: object, tgt: object) -> (tuple | None) {
    # -> (type_name, (field, ...)) when EVERY use of the bound name in the
    # walker is admissible, else None
    vname = str(tgt.value);
    fields: set = set();
    types: set = set();
    for scope in scopes {
        if not isinstance(scope, uni.UniNode) {
            return None;
        }
        names = _walk(scope, uni.Name, []);
        for nm in names {
            if nm is tgt or str(nm.value) != vname {
                continue;
            }
            p = getattr(nm, 'parent', None);
            # attribute NAMES and keyword keys are not variable references
            if isinstance(p, uni.AtomTrailer) and p.right is nm {
                continue;
            }
            if isinstance(p, uni.KWPair) and getattr(p, 'key', None) is nm {
                continue;
            }
            # a plain rebind / loop target observes nothing (its own reads
            # are audited like every other read of the name)
            if isinstance(p, uni.Assignment) and nm in list(p.target or []) {
                continue;
            }
            if isinstance(p, uni.InForStmt) and p.target is nm {
                continue;
            }
            if _sibling_branch(nm, bind) {
                continue;
            }
            if _ancestor(nm, (uni.DeleteStmt, )) is not None {
                return None;
            }
            # 1. attribute read: x.f  (not a method call, not a store)
            if isinstance(p, uni.AtomTrailer) and p.target is nm
                and getattr(p, 'is_attr', False) and isinstance(p.right, uni.Name) {
                gp = getattr(p, 'parent', None);
                if isinstance(gp, uni.FuncCall) and gp.target is p {
                    return None;
                }
                if _on_store_path(p) {
                    return None;
                }
                fields.add(str(p.right.value));
                continue;
            }
            if isinstance(p, uni.FuncCall) and nm in list(p.params or []) {
                cname = _call_name(p);
                prms = list(p.params or []);
                # 2. identity only: jid(x)
                if cname in _IDENTITY_CALLS and len(prms) == 1 {
                    continue;
                }
                # 3. isinstance(x, T) with a bare type name
                if cname == 'isinstance' and len(prms) == 2 and prms[0] is nm
                    and isinstance(prms[1], uni.Name) {
                    types.add(str(prms[1].value));
                    continue;
                }
                return None;
            }
            # 4. truth test / `is None`
            if _truth_only_use(nm) {
                continue;
            }
            if isinstance(p, uni.CompareExpr) {
                ops = [str(getattr(o, 'value', '')) for o in list(p.ops or [])];
                rights = list(p.rights or []);
                if len(rights) == 1 and ops and ops[0] in ('is', 'is not')
                    and (_is_none_lit(rights[0]) if p.left is nm else _is_none_lit(p.left)) {
                    continue;
                }
            }
            return None;
        }
    }
    if len(types) != 1 {
        return None;
    }
    return (list(types)[0], tuple(sorted(fields)));
}


class EffectPass(UniPass) {

    def before_pass(self: EffectPass) -> None {
        self._callee_memo: dict = {};
        self._module_nodes_verdict: dict = {};
    }

    def enter_archetype(self: EffectPass, nd: uni.Archetype) -> None {
        if nd.arch_type.name != 'KW_WALKER' {
            return;
        }
        try {
            reason = self._audit_walker(nd);
        } except Exception as e {
            reason = 'internal: ' + str(e);
        }
        import os;
        import sys;
        if os.environ.get('JAC_EFFECT_DEBUG') {
            verdict = 'RO' if reason is None else ('decline: ' + reason);
            sys.stderr.write('EFFECTPASS ' + str(nd.name) + ' ' + verdict + chr(10));
        }
        if reason is None {
            nd.effect_readonly = True;
            try {
                self._stamp_closure_sufficiency(nd);
            } except Exception {
                ;   # advisory stamp only: any doubt leaves the call as-is
            }
            try {
                self._stamp_hydrate_projection(nd);
            } except Exception as e {
                # same stance: the T6 projection stamp is advisory
                if os.environ.get('JAC_EFFECT_DEBUG') {
                    sys.stderr.write(
                        'EFFECTPASS ' + str(nd.name)
                        + ' hydrate projection internal: ' + str(e) + chr(10)
                    );
                }
            }
        }
    }

    def _stamp_closure_sufficiency(self: EffectPass, w: uni.Archetype) -> None {
        # Item #24 (minimal form): the trailing sufficiency threshold on a
        # jclosure call restates the walker's own sort+slice for the engine.
        # When the walker PROVES that restatement - result rows flow into a
        # list of dicts carrying "distance" from the row's depth (h[1]), the
        # list is sorted with distance as the DOMINANT key, and the report
        # slices it to a literal K - the compiler stamps the call and
        # PyastGenPass appends limit=K itself; the app stops spelling it.
        # Two consumption shapes are proved: (A) sort+slice as above, and
        # (B) the result read as a SINGLE element - `h[0]` behind a bare
        # emptiness test - which is K=1 (see _single_element_use).
        # Sound per PHASE_D lever 2: after level d completes, >=K matches at
        # depth <= d determine the top-K under a distance-first order; the
        # stamp is withheld for ANY other consumption shape and the builtin
        # then runs the plain full-depth closure (correct, just unbounded).
        import os;
        import sys;
        calls: list = [];
        for fc in UniPass.get_all_sub_nodes(nd=w, typ=uni.FuncCall) {
            t = getattr(fc, 'target', None);
            if isinstance(t, uni.Name)
                and str(getattr(t, 'sym_name', '') or t.value) == 'jclosure' {
                calls.append(fc);
            }
        }
        if len(calls) != 1 {
            return;
        }
        fc = calls[0];
        params = list(getattr(fc, 'params', []) or []);
        if len(params) != 6 {
            return;   # limit already spelled (7), or not the plain shape
        }
        for prm in params {
            if isinstance(prm, uni.KWPair) {
                return;
            }
        }
        asg = _ancestor(fc, (uni.Assignment, ));
        if asg is None or getattr(asg, 'value', None) is not fc {
            return;
        }
        tgts = list(getattr(asg, 'target', []) or []);
        if len(tgts) != 1 or not isinstance(tgts[0], uni.Name) {
            return;
        }
        hsym = getattr(tgts[0], 'sym', None);
        if hsym is None {
            return;
        }
        # shape B: the result is consumed as a SINGLE element (`h[0]`, guarded
        # by a bare emptiness test) -> one nearest match is enough
        if _single_element_use(w, hsym, tgts[0]) {
            fc.closure_limit = 1;
            if os.environ.get('JAC_EFFECT_DEBUG') {
                sys.stderr.write(
                    'EFFECTPASS ' + str(w.name)
                    + ' closure sufficiency limit=1 (single-element)' + chr(10)
                );
            }
            return;
        }
        # shape A: the ONE loop over the closure result
        loops: list = [];
        for fr in UniPass.get_all_sub_nodes(nd=w, typ=uni.InForStmt) {
            coll = getattr(fr, 'collection', None);
            if isinstance(coll, uni.Name) and getattr(coll, 'sym', None) is hsym {
                loops.append(fr);
            }
        }
        if len(loops) != 1 or not isinstance(loops[0].target, uni.Name) {
            return;
        }
        hvar_sym = getattr(loops[0].target, 'sym', None);
        if hvar_sym is None {
            return;
        }
        # rows land as {..., "distance": h[1]} appended to ONE local list
        fsym = None;
        for call in UniPass.get_all_sub_nodes(nd=loops[0], typ=uni.FuncCall) {
            ct = getattr(call, 'target', None);
            if not (isinstance(ct, uni.AtomTrailer)
                    and isinstance(getattr(ct, 'right', None), uni.Name)
                    and str(ct.right.value) == 'append'
                    and isinstance(ct.target, uni.Name)) {
                continue;
            }
            args = list(getattr(call, 'params', []) or []);
            if len(args) != 1 or not isinstance(args[0], uni.DictVal) {
                continue;
            }
            for kv in list(getattr(args[0], 'kv_pairs', []) or []) {
                k = getattr(kv, 'key', None);
                if str(getattr(k, 'lit_value', '')) != 'distance' {
                    continue;
                }
                v = getattr(kv, 'value', None);
                if isinstance(v, uni.AtomTrailer)
                    and isinstance(v.target, uni.Name)
                    and getattr(v.target, 'sym', None) is hvar_sym
                    and _subscript_lit(v) == 1 {
                    fsym = getattr(ct.target, 'sym', None);
                }
            }
        }
        if fsym is None {
            return;
        }
        # distance is the DOMINANT sort key of that list
        sort_ok = False;
        klim = None;
        for call in UniPass.get_all_sub_nodes(nd=w, typ=uni.FuncCall) {
            ct = getattr(call, 'target', None);
            if (isinstance(ct, uni.AtomTrailer)
                    and isinstance(getattr(ct, 'right', None), uni.Name)
                    and str(ct.right.value) == 'sort'
                    and isinstance(ct.target, uni.Name)
                    and getattr(ct.target, 'sym', None) is fsym) {
                for prm in list(getattr(call, 'params', []) or []) {
                    if isinstance(prm, uni.KWPair)
                        and str(getattr(prm.key, 'value', '')) == 'key'
                        and isinstance(prm.value, uni.LambdaExpr) {
                        body = prm.value.tail_return_expr();
                        if isinstance(body, uni.TupleVal) {
                            vals = list(getattr(body, 'values', []) or []);
                            if vals and isinstance(vals[0], uni.AtomTrailer)
                                and _subscript_lit_str(vals[0]) == 'distance' {
                                sort_ok = True;
                            }
                        }
                    } elif isinstance(prm, uni.KWPair)
                        and str(getattr(prm.key, 'value', '')) == 'reverse' {
                        sort_ok = False;   # distance DESC: containment breaks
                        break;
                    }
                }
            }
        }
        if not sort_ok {
            return;
        }
        # the report keeps the K nearest: F[:K] with literal K
        for at in UniPass.get_all_sub_nodes(nd=w, typ=uni.AtomTrailer) {
            if isinstance(at.target, uni.Name)
                and getattr(at.target, 'sym', None) is fsym
                and isinstance(getattr(at, 'right', None), uni.IndexSlice)
                and getattr(at.right, 'is_range', False)
                and _ancestor(at, (uni.ReportStmt, )) is not None {
                slices = list(getattr(at.right, 'slices', []) or []);
                if len(slices) == 1 and getattr(slices[0], 'start', None) is None
                    and getattr(slices[0], 'step', None) is None {
                    kv2 = getattr(getattr(slices[0], 'stop', None), 'lit_value', None);
                    if isinstance(kv2, int) and kv2 > 0 {
                        klim = kv2;
                    }
                }
            }
        }
        if klim is None {
            return;
        }
        fc.closure_limit = int(klim);
        if os.environ.get('JAC_EFFECT_DEBUG') {
            sys.stderr.write(
                'EFFECTPASS ' + str(w.name) + ' closure sufficiency limit='
                + str(klim) + chr(10)
            );
        }
    }

    def _stamp_hydrate_projection(self: EffectPass, w: uni.Archetype) -> None {
        # T6: per-site projection stamp for jobj()/jobj_many() in a walker
        # that just proved read-only. PyastGenPass turns the stamp into a
        # `_proj=(T, (fields...))` keyword; the runtime then hydrates from
        # T's mirror columns (no anchor blob decode) when it can, and falls
        # back to the full load otherwise. Two binding shapes: `x = jobj(id)`
        # and `for x in jobj_many(ids)`.
        import os;
        import sys;
        scopes = self._scopes_of(w);
        calls: list = [];
        seen: set = set();
        for scope in scopes {
            if scope is not None {
                for c in _walk(scope, uni.FuncCall, []) {
                    if id(c) not in seen {
                        seen.add(id(c));
                        calls.append(c);
                    }
                }
            }
        }
        for fc in calls {
            fname = _call_name(fc);
            if fname not in ('jobj', 'jobj_many') {
                continue;
            }
            params = list(getattr(fc, 'params', []) or []);
            if len(params) != 1 or isinstance(params[0], uni.KWPair) {
                continue;
            }
            bind = None;
            tgt = None;
            p = getattr(fc, 'parent', None);
            if fname == 'jobj' and isinstance(p, uni.Assignment)
                and getattr(p, 'value', None) is fc {
                tgts = list(getattr(p, 'target', []) or []);
                if len(tgts) == 1 and isinstance(tgts[0], uni.Name) {
                    bind = p;
                    tgt = tgts[0];
                }
            } elif fname == 'jobj_many' and isinstance(p, uni.InForStmt)
                and getattr(p, 'collection', None) is fc
                and isinstance(p.target, uni.Name) {
                bind = p;
                tgt = p.target;
            }
            if bind is None {
                continue;
            }
            proj = _projection_of(scopes, bind, tgt);
            if os.environ.get('JAC_EFFECT_DEBUG') {
                sys.stderr.write(
                    'EFFECTPASS ' + str(w.name) + ' hydrate projection '
                    + fname + '@' + str(getattr(fc.loc, 'first_line', '?'))
                    + ' ' + (str(proj) if proj is not None else 'declined') + chr(10)
                );
            }
            if proj is not None {
                fc.hydrate_proj = proj;
            }
        }
    }

    def _audit_walker(self: EffectPass, w: uni.Archetype) -> (str | None) {
        saw_visit = False;
        for scope in self._scopes_of(w) {
            if scope is None {
                return 'unresolved ability body';
            }
            reason = self._audit_scope(scope, False, True);
            if reason is not None {
                return reason;
            }
            if isinstance(scope, uni.VisitStmt)
                or UniPass.get_all_sub_nodes(nd=scope, typ=uni.VisitStmt) {
                saw_visit = True;
            }
        }
        if saw_visit {
            # visiting fires node/edge entry abilities: they must all be
            # effect-free too, or the walker's traversal writes by proxy
            return self._module_nodes_clean(w);
        }
        return None;
    }

    def _scopes_of(self: EffectPass, arch: uni.Archetype) -> list {
        # the archetype subtree covers inline bodies and has-defaults;
        # impl-file bodies hang off each ability's `body` link instead
        scopes: list = [arch];
        for ab in UniPass.get_all_sub_nodes(nd=arch, typ=uni.Ability) {
            if getattr(ab, 'is_abstract', False) {
                continue;
            }
            stmts = _resolved_bodies(ab);
            if not stmts and getattr(ab, 'body', None) is None {
                scopes.append(None);   # declared, never implemented: refuse
                continue;
            }
            for st in stmts {
                if isinstance(st, uni.UniNode) and st is not ab {
                    scopes.append(st);
                }
            }
        }
        return scopes;
    }

    def _audit_scope(
        self: EffectPass, nd_root: uni.UniNode, graph_self: bool, allow_visit: bool
    ) -> (str | None) {
        if isinstance(nd_root, (uni.ConnectOp, uni.DisconnectOp, uni.DeleteStmt))
            or UniPass.get_all_sub_nodes(nd=nd_root, typ=uni.ConnectOp)
            or UniPass.get_all_sub_nodes(nd=nd_root, typ=uni.DisconnectOp)
            or UniPass.get_all_sub_nodes(nd=nd_root, typ=uni.DeleteStmt) {
            return 'topology write';
        }
        if not allow_visit
            and (isinstance(nd_root, uni.VisitStmt)
                 or UniPass.get_all_sub_nodes(nd=nd_root, typ=uni.VisitStmt)) {
            return 'visit outside walker scope';
        }
        for tok in UniPass.get_all_sub_nodes(nd=nd_root, typ=uni.Token) {
            if str(getattr(tok, 'value', '')) in _KILL_TOKENS {
                return 'token ' + str(tok.value);
            }
        }
        asgs = UniPass.get_all_sub_nodes(nd=nd_root, typ=uni.Assignment);
        if isinstance(nd_root, uni.Assignment) {
            asgs = [nd_root] + asgs;
        }
        for asg in asgs {
            for t in list(getattr(asg, 'target', []) or []) {
                reason = self._target_ok(t, graph_self);
                if reason is not None {
                    return reason;
                }
            }
        }
        calls = UniPass.get_all_sub_nodes(nd=nd_root, typ=uni.FuncCall);
        if isinstance(nd_root, uni.FuncCall) {
            calls = [nd_root] + calls;
        }
        for fc in calls {
            reason = self._call_ok(fc, graph_self);
            if reason is not None {
                return reason;
            }
        }
        return None;
    }

    def _target_ok(self: EffectPass, t: object, graph_self: bool) -> (str | None) {
        if isinstance(t, uni.Name) {
            return None;   # plain local rebind
        }
        if isinstance(t, uni.TupleVal) {
            for v in list(getattr(t, 'values', []) or []) {
                reason = self._target_ok(v, graph_self);
                if reason is not None {
                    return reason;
                }
            }
            return None;
        }
        if isinstance(t, uni.AtomTrailer) {
            tright = getattr(t, 'right', None);
            if isinstance(tright, uni.IndexSlice) {
                # X[k] = v: only into a provably walker-local container
                if self._recv_safe(t.target, graph_self) {
                    return None;
                }
                return 'index store into unproven container';
            }
            if isinstance(tright, uni.Name) {
                # X.field = v: walker state only - in a node/edge method
                # `self` IS the graph, so no attribute store is admissible
                if not graph_self and isinstance(t.target, uni.Name)
                    and str(getattr(t.target, 'sym_name', '')) == 'self' {
                    return None;
                }
                return 'attribute store to ' + str(tright.value);
            }
        }
        return 'unrecognized store target';
    }

    def _call_ok(self: EffectPass, fc: uni.FuncCall, graph_self: bool) -> (str | None) {
        tgt = getattr(fc, 'target', None);
        if isinstance(tgt, uni.Name) {
            nm = str(getattr(tgt, 'sym_name', '') or tgt.value);
            if nm in _PURE_CALLS {
                return None;
            }
            decl = getattr(fc, 'callee_decl', None);
            if isinstance(decl, uni.Ability) {
                return self._audit_callee(decl);
            }
            s = getattr(tgt, 'sym', None);
            if s is not None and getattr(s, 'sym_type', None) is not None {
                if s.sym_type == SymbolType.OBJECT_ARCH {
                    # plain data constructor: binds fields, touches no store
                    return None;
                }
                if s.sym_type in (SymbolType.NODE_ARCH, SymbolType.EDGE_ARCH,
                                  SymbolType.WALKER_ARCH) {
                    return 'constructor of ' + nm;
                }
            }
            ab = _enclosing_ability(getattr(s, 'decl', None) if s is not None else None);
            if isinstance(ab, uni.Ability) {
                return self._audit_callee(ab);
            }
            return 'unresolved call ' + nm;
        }
        if isinstance(tgt, uni.AtomTrailer) {
            tright = getattr(tgt, 'right', None);
            if isinstance(tright, uni.Name) {
                m = str(tright.value);
                base = getattr(tgt, 'target', None);
                if isinstance(base, uni.Name)
                    and (str(base.value), m) in _PURE_MODULE_ATTRS {
                    return None;
                }
                if m in _CONTAINER_METHODS and self._recv_safe(base, graph_self) {
                    return None;
                }
                decl = getattr(fc, 'callee_decl', None);
                if isinstance(decl, uni.Ability) {
                    return self._audit_callee(decl);
                }
                s = getattr(tright, 'sym', None);
                ab = _enclosing_ability(getattr(s, 'decl', None) if s is not None else None);
                if isinstance(ab, uni.Ability) {
                    return self._audit_callee(ab);
                }
                # last resort: name-directed over the module's archetypes -
                # sound because EVERY same-named method must audit clean
                return self._audit_methods_named(fc, m);
            }
        }
        return 'dynamic call';
    }

    def _audit_methods_named(self: EffectPass, fc: uni.FuncCall, m: str) -> (str | None) {
        mod = _ancestor(fc, (uni.Module, ));
        if mod is None {
            return 'unresolved method ' + m;
        }
        found = 0;
        for arch in UniPass.get_all_sub_nodes(nd=mod, typ=uni.Archetype) {
            for ab in UniPass.get_all_sub_nodes(nd=arch, typ=uni.Ability) {
                nr = getattr(ab, 'name_ref', None);
                if nr is None or str(getattr(nr, 'sym_name', '')) != m {
                    continue;
                }
                found += 1;
                reason = self._audit_callee(ab);
                if reason is not None {
                    return 'method ' + m + ': ' + reason;
                }
            }
        }
        if found == 0 {
            return 'unresolved method ' + m;
        }
        return None;
    }

    def _audit_callee(self: EffectPass, ab: uni.Ability) -> (str | None) {
        key = id(ab);
        cached = self._callee_memo.get(key, None);
        if cached == 'ok' {
            return None;
        }
        if cached == 'pending' {
            return 'recursive callee';
        }
        if cached is not None {
            return cached;
        }
        self._callee_memo[key] = 'pending';
        owner = getattr(ab, 'method_owner', None);
        g_self = isinstance(owner, uni.Archetype)
            and owner.arch_type.name in ('KW_NODE', 'KW_EDGE');
        stmts = _resolved_bodies(ab);
        reason = None;
        if not stmts {
            reason = 'callee without body';
        } else {
            for st in stmts {
                if not isinstance(st, uni.UniNode) {
                    continue;
                }
                reason = self._audit_scope(st, g_self, False);
                if reason is not None {
                    break;
                }
            }
        }
        self._callee_memo[key] = 'ok' if reason is None else reason;
        return reason;
    }

    def _module_nodes_clean(self: EffectPass, w: uni.Archetype) -> (str | None) {
        mod = _ancestor(w, (uni.Module, ));
        if mod is None {
            return 'no module';
        }
        key = id(mod);
        cached = self._module_nodes_verdict.get(key, None);
        if cached is not None {
            return None if cached == 'ok' else cached;
        }
        verdict = None;
        for arch in UniPass.get_all_sub_nodes(nd=mod, typ=uni.Archetype) {
            if arch.arch_type.name not in ('KW_NODE', 'KW_EDGE') {
                continue;
            }
            for ab in UniPass.get_all_sub_nodes(nd=arch, typ=uni.Ability) {
                if not isinstance(getattr(ab, 'signature', None), uni.EventSignature) {
                    continue;
                }
                reason = self._audit_callee(ab);
                if reason is not None {
                    verdict = 'node ability ' + str(ab.name_ref) + ': ' + reason;
                    break;
                }
            }
            if verdict is not None {
                break;
            }
        }
        self._module_nodes_verdict[key] = 'ok' if verdict is None else verdict;
        return verdict;
    }

    def _recv_safe(self: EffectPass, e: object, graph_self: bool) -> bool {
        return self._recv_safe_g(e, graph_self, set());
    }

    def _recv_safe_g(self: EffectPass, e: object, graph_self: bool, seen: set) -> bool {
        if isinstance(e, uni.Name) {
            nm = str(getattr(e, 'sym_name', '') or e.value);
            if nm == 'self' or nm in _GRAPH_VARS {
                return False;
            }
            return self._local_fresh(e, seen);
        }
        if isinstance(e, uni.AtomTrailer) {
            eright = getattr(e, 'right', None);
            # self.<field> in a walker: walker state, not graph state
            if isinstance(eright, uni.Name) and not graph_self
                and isinstance(e.target, uni.Name)
                and str(getattr(e.target, 'sym_name', '')) == 'self' {
                return True;
            }
            # element of a safe container (X[k].add(...))
            if isinstance(eright, uni.IndexSlice) {
                return self._recv_safe_g(e.target, graph_self, seen);
            }
        }
        # chained container method: X.setdefault(k, []).append(v)
        if isinstance(e, uni.FuncCall) {
            t2 = getattr(e, 'target', None);
            if isinstance(t2, uni.AtomTrailer)
                and isinstance(getattr(t2, 'right', None), uni.Name)
                and str(t2.right.value) in _CONTAINER_METHODS {
                return self._recv_safe_g(t2.target, graph_self, seen);
            }
        }
        return False;
    }

    def _local_fresh(self: EffectPass, name_node: uni.Name, seen: set) -> bool {
        s = getattr(name_node, 'sym', None);
        if s is None {
            return False;
        }
        if id(s) in seen {
            return True;   # cycle: every other def already being verified
        }
        seen.add(id(s));
        defs = list(getattr(s, 'defn', []) or []);
        if not defs {
            return False;
        }
        for d in defs {
            asg = _ancestor(d, (uni.Assignment, ));
            if asg is None
                or not any((t is d) for t in list(getattr(asg, 'target', []) or [])) {
                return False;   # for-target / param / unknown def form
            }
            v = getattr(asg, 'value', None);
            if isinstance(v, uni.Name) {
                if not self._local_fresh(v, seen) {
                    return False;
                }
                continue;
            }
            if not self._fresh_expr(v) {
                return False;
            }
        }
        return True;
    }

    def _fresh_expr(self: EffectPass, v: object) -> bool {
        if isinstance(v, (
            uni.ListVal, uni.SetVal, uni.DictVal, uni.TupleVal,
            uni.ListCompr, uni.DictCompr, uni.EdgeRefTrailer
        )) {
            return True;
        }
        if isinstance(v, uni.BinaryExpr)
            and str(getattr(getattr(v, 'op', None), 'value', '')) == '+' {
            return self._fresh_expr(v.left) and self._fresh_expr(v.right);
        }
        if isinstance(v, uni.FuncCall) and isinstance(v.target, uni.Name)
            and str(v.target.value) in _FRESH_CTORS {
            return True;
        }
        return False;
    }
}
