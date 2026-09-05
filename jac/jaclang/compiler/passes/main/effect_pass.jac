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


def _is_ranged(e: object) -> bool {
    # T7: an EdgeRefTrailer carrying a variable-length hop
    if not isinstance(e, uni.EdgeRefTrailer) {
        return False;
    }
    for c in list(getattr(e, 'chain', []) or []) {
        if isinstance(c, uni.EdgeOpRef) and getattr(c, 'max_hops', None) is not None {
            return True;
        }
    }
    return False;
}


def _ranged_filter_type(e: object) -> (str | None) {
    # the node archetype the ranged chain itself names ([?:T])
    ch = list(getattr(e, 'chain', []) or []);
    if len(ch) == 3 and isinstance(ch[2], uni.FilterCompr) {
        ft = getattr(ch[2], 'f_type', None);
        if isinstance(ft, uni.Name) {
            return str(ft.value);
        }
    }
    return None;
}


def _loop_pair(loop: object) -> tuple {
    # (elem_sym, depth_sym) for `for x in ..` (depth None) or `for (x, d) in ..`
    tgt = getattr(loop, 'target', None);
    if isinstance(tgt, uni.Name) {
        return (getattr(tgt, 'sym', None), None, tgt);
    }
    if isinstance(tgt, uni.TupleVal) {
        vals = list(getattr(tgt, 'values', []) or []);
        if len(vals) == 2 and isinstance(vals[0], uni.Name)
            and isinstance(vals[1], uni.Name) {
            return (
                getattr(vals[0], 'sym', None), getattr(vals[1], 'sym', None), vals[0]
            );
        }
    }
    return (None, None, None);
}


def _shape_a_limit(
    w: uni.Archetype, loop: object, hvar_sym: object, dsym: object
) -> (int | None) {
    # Item #24 shape A: the ONE loop over the closure result appends
    # {..., "distance": <depth>} to a local list, that list is sorted with
    # distance as the DOMINANT key, and the report slices it to a literal K.
    # `dsym` is the loop's own depth name (T7 `for (x, d) in ..`); when it is
    # None the depth is read as `hvar[1]` (T1's jclosure tuple rows).
    fsym = None;
    for call in UniPass.get_all_sub_nodes(nd=loop, typ=uni.FuncCall) {
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
            ok = False;
            if dsym is not None {
                ok = isinstance(v, uni.Name) and getattr(v, 'sym', None) is dsym;
            } else {
                ok = (isinstance(v, uni.AtomTrailer)
                      and isinstance(v.target, uni.Name)
                      and getattr(v.target, 'sym', None) is hvar_sym
                      and _subscript_lit(v) == 1);
            }
            if ok {
                fsym = getattr(ct.target, 'sym', None);
                # review fix (T7): the sufficiency limit promises the K
                # NEAREST rows of the ENGINE's predicate. A row the walker
                # drops in Python (guarded append) or a loop it leaves early
                # would make it keep fewer than K although more exist, so
                # the append must sit unguarded in the loop body and the
                # loop must run out.
                q = getattr(call, 'parent', None);
                while q is not None and q is not loop {
                    if isinstance(q, (uni.IfStmt, uni.TryStmt, uni.WhileStmt,
                                      uni.InForStmt, uni.IterForStmt,
                                      uni.ForeverStmt)) {
                        return None;
                    }
                    q = getattr(q, 'parent', None);
                }
            }
        }
    }
    if fsym is None {
        return None;
    }
    for ex in UniPass.get_all_sub_nodes(nd=loop, typ=uni.CtrlStmt) {
        return None;   # break / continue inside the closure loop
    }
    for ex in UniPass.get_all_sub_nodes(nd=loop, typ=uni.ReturnStmt) {
        return None;
    }
    sort_ok = False;
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
        return None;
    }
    klim = None;
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
    return klim;
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
            if _ancestor(p, (uni.InForStmt, uni.IterForStmt, uni.WhileStmt, uni.ForeverStmt)) is not None {
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


def _in_dead(n: object, dead: set) -> bool {
    # C2: the use sits inside a subtree another lowering DELETES (rung B's
    # hopcount nest), so the emitted program never performs it
    cur = n;
    while cur is not None {
        if id(cur) in dead {
            return True;
        }
        cur = getattr(cur, 'parent', None);
    }
    return False;
}


def _dict_store_base(nm: object) -> (str | None) {
    # `<D>[<k>] = <nm>` with `<D>` a bare Name and `nm` the assigned VALUE
    # -> 'D'. The key expression is NOT excused here: every Name in it is
    # swept like any other use, so `D[x] = x` still declines.
    p = getattr(nm, 'parent', None);
    if not isinstance(p, uni.Assignment) or getattr(p, 'aug_op', None) is not None
        or getattr(p, 'value', None) is not nm {
        return None;
    }
    tgts = list(getattr(p, 'target', []) or []);
    if len(tgts) != 1 or not isinstance(tgts[0], uni.AtomTrailer) {
        return None;
    }
    at = tgts[0];
    base = getattr(at, 'target', None);
    right = getattr(at, 'right', None);
    if not isinstance(base, uni.Name) or not isinstance(right, uni.IndexSlice)
        or getattr(right, 'is_range', False) {
        return None;
    }
    slices = list(getattr(right, 'slices', []) or []);
    if len(slices) != 1 or getattr(slices[0], 'stop', None) is not None
        or getattr(slices[0], 'step', None) is not None {
        return None;
    }
    return str(base.value);
}


def _projection_of(
    scopes: list,
    bind: object,
    tgt: object,
    dflt_type: (str | None) = None,
    alias: (str | None) = None,
    dead: (set | None) = None
) -> (tuple | None) {
    # -> (type_name, (field, ...)) when EVERY use of the bound name in the
    # walker is admissible, else None. `alias` (C2) excuses the ONE escape
    # shape `<alias>[<k>] = x` - only ever passed after _dict_alias_fields
    # has audited every use of `<alias>` itself; `dead` (C2) is the set of
    # subtrees another stamp deletes from the emitted program.
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
            if isinstance(p, (uni.InForStmt, uni.InnerCompr))
                and getattr(p, 'target', None) is nm {
                continue;
            }
            if isinstance(p, uni.TupleVal)
                and isinstance(
                    getattr(p, 'parent', None), (uni.InForStmt, uni.InnerCompr)
                )
                and getattr(getattr(p, 'parent', None), 'target', None) is p {
                continue;   # the `(x, d)` unpack target of a loop/comprehension
            }
            if _sibling_branch(nm, bind) {
                continue;
            }
            if dead is not None and _in_dead(nm, dead) {
                continue;
            }
            if alias is not None and _dict_store_base(nm) == alias {
                continue;   # C2: the audited dict-alias escape
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
    if dflt_type is not None {
        # review fix (T7): the ranged chain / typed jobj PROVES the archetype;
        # an isinstance on the same name that says otherwise is a walker bug
        # or an always-false branch, never a reason to project another mirror
        if types and types != {dflt_type} {
            return None;
        }
        types = {dflt_type};
    }
    if len(types) != 1 {
        return None;
    }
    return (list(types)[0], tuple(sorted(fields)));
}


def _ids_only_of(
    scopes: list,
    bind: object,
    tgt: object,
    alias: (str | None) = None,
    dead: (set | None) = None
) -> bool {
    # T7b: True iff EVERY reference to the bound name is the SOLE argument of
    # a `jid(...)` call - i.e. the walker observes nothing but the element's
    # identity, so the id IS the value it wants. Same non-reference skips as
    # _projection_of (attribute name, KWPair key, assignment / loop target
    # incl. the `(x, d)` unpack, sibling if-branch); every other shape - an
    # attribute read, isinstance, a truth test, `is None`, another call,
    # report, return, subscript, delete - returns False. Unresolved scope:
    # False. Refusal over wrongness, per site, exactly like _projection_of.
    # `alias` / `dead` (D4) are _projection_of's two excuses, spelled the same
    # way: the ONE audited `<alias>[<k>] = x` store, and subtrees another
    # lowering deletes or rebinds the name in. Both default None -> every
    # existing caller is byte-identical.
    vname = str(getattr(tgt, 'value', ''));
    for scope in scopes {
        if not isinstance(scope, uni.UniNode) {
            return False;
        }
        for nm in _walk(scope, uni.Name, []) {
            if nm is tgt or str(nm.value) != vname {
                continue;
            }
            p = getattr(nm, 'parent', None);
            if isinstance(p, uni.AtomTrailer) and p.right is nm {
                continue;
            }
            if isinstance(p, uni.KWPair) and getattr(p, 'key', None) is nm {
                continue;
            }
            if isinstance(p, uni.Assignment) and nm in list(p.target or []) {
                continue;
            }
            if isinstance(p, (uni.InForStmt, uni.InnerCompr))
                and getattr(p, 'target', None) is nm {
                continue;
            }
            if isinstance(p, uni.TupleVal)
                and isinstance(
                    getattr(p, 'parent', None), (uni.InForStmt, uni.InnerCompr)
                )
                and getattr(getattr(p, 'parent', None), 'target', None) is p {
                continue;
            }
            if _sibling_branch(nm, bind) {
                continue;
            }
            if dead is not None and _in_dead(nm, dead) {
                continue;
            }
            if alias is not None and _dict_store_base(nm) == alias {
                continue;   # D4: the audited dict-alias escape
            }
            if _ancestor(nm, (uni.DeleteStmt, )) is not None {
                return False;
            }
            if isinstance(p, uni.FuncCall) and _call_name(p) in _IDENTITY_CALLS {
                prms = list(p.params or []);
                if len(prms) == 1 and prms[0] is nm {
                    continue;
                }
            }
            return False;
        }
    }
    return True;
}


def _dict_alias_fields(
    scopes: list, dname: str, vname: str, dflt_type: (str | None), dead: set
) -> (set | None) {
    # C2: `<D>` is a LOCAL dict the loop element escapes into
    # (`<D>[<k>] = x`). -> the extra fields read off the element through
    # `<D>`, or None if `<D>` itself is not provably a private staging dict.
    # Admissible uses of `<D>`, and nothing else: the one `= {}` init, a
    # `<D>[<k>] = <vname>` store, a membership test `<k> in <D>`, and
    # `for (k2, v2) in <D>.items()` whose element is audited by
    # _projection_of like any other binding (its fields union into ours).
    # A read `<D>[<k>]`, `len(<D>)`, a call argument, a return or a report
    # all decline: each hands the element to something this audit cannot
    # see. Refusal over wrongness, exactly like _projection_of.
    fields: set = set();
    inits: set = set();   # by node id: _scopes_of can hand the same body twice
    for scope in scopes {
        if not isinstance(scope, uni.UniNode) {
            return None;
        }
        for nm in _walk(scope, uni.Name, []) {
            if str(nm.value) != dname {
                continue;
            }
            p = getattr(nm, 'parent', None);
            if isinstance(p, uni.AtomTrailer) and p.right is nm {
                continue;   # an attribute NAME that happens to match
            }
            if isinstance(p, uni.KWPair) and getattr(p, 'key', None) is nm {
                continue;
            }
            if dead is not None and _in_dead(nm, dead) {
                continue;
            }
            # 1. the local init: `<D> = {}` / `<D>: dict = {}`
            if isinstance(p, uni.Assignment) and nm in list(p.target or []) {
                dv = getattr(p, 'value', None);
                if isinstance(dv, uni.DictVal)
                    and not list(getattr(dv, 'kv_pairs', []) or []) {
                    inits.add(id(p));
                    continue;
                }
                return None;   # bound to something this audit cannot see
            }
            if isinstance(p, uni.AtomTrailer) and p.target is nm {
                right = getattr(p, 'right', None);
                # 2. the store `<D>[<k>] = <vname>` (a READ `<D>[<k>]` is not
                # admissible: it hands the element to an unaudited name)
                if isinstance(right, uni.IndexSlice) {
                    if not _on_store_path(p) {
                        return None;
                    }
                    asg = _ancestor(p, (uni.Assignment, ));
                    val = getattr(asg, 'value', None) if asg is not None else None;
                    if not isinstance(val, uni.Name) or str(val.value) != vname {
                        return None;   # some OTHER value in the same dict
                    }
                    continue;
                }
                # 3. `for (k2, v2) in <D>.items()`
                if isinstance(right, uni.Name) and str(right.value) == 'items'
                    and getattr(p, 'is_attr', False) {
                    fc = getattr(p, 'parent', None);
                    if not isinstance(fc, uni.FuncCall) or fc.target is not p
                        or list(getattr(fc, 'params', []) or []) {
                        return None;
                    }
                    lp = getattr(fc, 'parent', None);
                    if not isinstance(lp, (uni.InForStmt, uni.InnerCompr))
                        or getattr(lp, 'collection', None) is not fc {
                        return None;
                    }
                    pair = _loop_pair(lp);
                    ltgt = getattr(lp, 'target', None);
                    if not isinstance(ltgt, uni.TupleVal) or pair[2] is None {
                        return None;
                    }
                    v2 = list(getattr(ltgt, 'values', []) or [])[1];
                    if not isinstance(v2, uni.Name) {
                        return None;
                    }
                    if str(v2.value) == vname {
                        continue;   # same name: the outer sweep already has it
                    }
                    sub = _projection_of(scopes, lp, v2, dflt_type, None, dead);
                    if sub is None {
                        return None;
                    }
                    fields.update(sub[1]);
                    continue;
                }
                return None;
            }
            # 4. membership only: `<k> in <D>` / `<k> not in <D>`
            if isinstance(p, uni.CompareExpr) and nm in list(p.rights or []) {
                ops = [str(getattr(o, 'value', '')) for o in list(p.ops or [])];
                if ops and all([o in ('in', 'not in') for o in ops]) {
                    continue;
                }
            }
            return None;
        }
    }
    return fields if len(inits) == 1 else None;
}


def _topk_items_loop(scopes: list, dname: str) -> (object | None) {
    # D4: the ONE `for (k2, v2) in <D>.items()` reader of the staging dict,
    # and only when rung D stamped THAT loop as the top-K tail. Anything else
    # -> None: a second `.items()` reader (a comprehension counts) would see
    # the dict's values, and without the rung-D stamp the tail still hydrates
    # them itself. Combined with _dict_alias_fields (which declines every
    # other way to read `<D>`) this is the spec's "the dict's values are read
    # ONLY inside the top-K tail".
    found: list = [];
    seen: set = set();
    for scope in scopes {
        if not isinstance(scope, uni.UniNode) {
            return None;
        }
        readers: list = _walk(scope, uni.InForStmt, []);
        readers.extend(_walk(scope, uni.InnerCompr, []));
        for lp in readers {
            if id(lp) in seen {
                continue;
            }
            seen.add(id(lp));
            if _items_dict_name(getattr(lp, 'collection', None)) == dname {
                found.append(lp);
            }
        }
    }
    if len(found) != 1 {
        return None;
    }
    tp = getattr(found[0], 'hopcount_topk', None);
    if tp is None or str(tp[0]) != dname {
        return None;
    }
    return found[0];
}


# --- Rung B: the ic5 counting nest -----------------------------------------
# `for (k, v) in <D>.items() { cnt = 0;
#     for x in [v ->:E2:-> [?:T2]] { c = [x ->:E3:-> [?:T3]];
#         if c and jid(c[0]) in <S>[k] { cnt += 1; } }
#   <trailing statements> }`
# is a relational aggregation written as a nest of edge-reference loops: per
# key, count the E2-neighbours of `v` that have an E3 edge into that key's
# member set. Proving THAT shape lets PyastGenPass replace the whole inner
# nest with one `jhopcount(...)` statement (COMPILER_PLAN.md rung B.2). The
# proof is structural and total: every helper below returns None/False for
# anything it does not recognise EXACTLY, because a lowering that is a
# superset of the walker's own loop would silently change the answer.


def _walk_list(nodes: list, typ: type) -> list {
    out: list = [];
    for n in nodes {
        _walk(n, typ, out);
    }
    return out;
}


def _unwrap_cfg(e: object) -> object {
    cur = e;
    while isinstance(cur, uni.CfgExpr) {
        cur = getattr(cur, 'expr', None);
    }
    return cur;
}


def _int_lit(e: object, want: int) -> bool {
    v = getattr(e, 'lit_value', None);
    return isinstance(v, int) and not isinstance(v, bool) and v == want;
}


def _plain_hop(e: object, origin: str) -> (tuple | None) {
    # `[<origin> ->:E:-> [?:T]]` and nothing else -> (E, T).
    # Declines: inbound / ANY direction, a ranged hop, a second hop, an edge
    # or node predicate, `edges_only`, a non-Name origin or type. Each of
    # those changes what the emitted SQL would have to say, and the SQL says
    # only this one thing.
    if not isinstance(e, uni.EdgeRefTrailer) or getattr(e, 'edges_only', False) {
        return None;
    }
    ch = list(getattr(e, 'chain', []) or []);
    if len(ch) != 3 {
        return None;
    }
    org = ch[0];
    op = ch[1];
    nfilt = ch[2];
    if not isinstance(org, uni.Name) or str(org.value) != origin {
        return None;
    }
    if not isinstance(op, uni.EdgeOpRef)
        or getattr(op, 'max_hops', None) is not None
        or str(getattr(getattr(op, 'edge_dir', None), 'name', '')) != 'OUT' {
        return None;
    }
    ecompr = getattr(op, 'filter_cond', None);
    if not isinstance(ecompr, uni.FilterCompr)
        or list(getattr(ecompr, 'compares', []) or []) {
        return None;
    }
    if not isinstance(nfilt, uni.FilterCompr)
        or list(getattr(nfilt, 'compares', []) or []) {
        return None;
    }
    et = getattr(ecompr, 'f_type', None);
    nt = getattr(nfilt, 'f_type', None);
    if not isinstance(et, uni.Name) or not isinstance(nt, uni.Name) {
        return None;
    }
    return (str(et.value), str(nt.value));
}


def _items_dict_name(coll: object) -> (str | None) {
    # `<D>.items()` with `<D>` a bare Name -> 'D'
    if not isinstance(coll, uni.FuncCall) or list(getattr(coll, 'params', []) or []) {
        return None;
    }
    t = getattr(coll, 'target', None);
    if not isinstance(t, uni.AtomTrailer) or not getattr(t, 'is_attr', False) {
        return None;
    }
    r = getattr(t, 'right', None);
    d = getattr(t, 'target', None);
    if not isinstance(r, uni.Name) or str(r.value) != 'items'
        or not isinstance(d, uni.Name) {
        return None;
    }
    return str(d.value);
}


def _name_subscript(at: object, key: str) -> (object | None) {
    # `<S>[<key>]` with both parts bare Names -> the `<S>` Name node
    if not isinstance(at, uni.AtomTrailer) {
        return None;
    }
    base = getattr(at, 'target', None);
    right = getattr(at, 'right', None);
    if not isinstance(base, uni.Name) or not isinstance(right, uni.IndexSlice)
        or getattr(right, 'is_range', False) {
        return None;
    }
    slices = list(getattr(right, 'slices', []) or []);
    if len(slices) != 1 or getattr(slices[0], 'stop', None) is not None
        or getattr(slices[0], 'step', None) is not None {
        return None;
    }
    s = getattr(slices[0], 'start', None);
    if not isinstance(s, uni.Name) or str(s.value) != key {
        return None;
    }
    return base;
}


def _zero_init_name(st: object) -> (str | None) {
    # `<cnt> = 0;` -> 'cnt'
    if not isinstance(st, uni.Assignment) or getattr(st, 'aug_op', None) is not None {
        return None;
    }
    tgts = list(getattr(st, 'target', []) or []);
    if len(tgts) != 1 or not isinstance(tgts[0], uni.Name) {
        return None;
    }
    if not _int_lit(getattr(st, 'value', None), 0) {
        return None;
    }
    return str(tgts[0].value);
}


def _is_increment(st: object, cname: str) -> bool {
    # `<cnt> += 1;` or `<cnt> = <cnt> + 1;`
    if not isinstance(st, uni.Assignment) {
        return False;
    }
    tgts = list(getattr(st, 'target', []) or []);
    if len(tgts) != 1 or not isinstance(tgts[0], uni.Name)
        or str(tgts[0].value) != cname {
        return False;
    }
    v = getattr(st, 'value', None);
    aug = getattr(st, 'aug_op', None);
    if aug is not None {
        return str(getattr(aug, 'value', '')) == '+=' and _int_lit(v, 1);
    }
    if not isinstance(v, uni.BinaryExpr)
        or str(getattr(getattr(v, 'op', None), 'value', '')) != '+' {
        return False;
    }
    lf = getattr(v, 'left', None);
    return isinstance(lf, uni.Name) and str(lf.value) == cname
        and _int_lit(getattr(v, 'right', None), 1);
}


def _membership_base(cond: object, cname: str, kname: str) -> (object | None) {
    # `<c> and jid(<c>[0]) in <S>[<k>]` -> the `<S>` Name node.
    # The truth test on `c` is what makes the SQL's inner join equivalent:
    # without it the walker would index an empty list, so the shape that
    # counts is exactly "has an E3 neighbour AND that neighbour is a member".
    if not isinstance(cond, uni.BoolExpr)
        or str(getattr(getattr(cond, 'op', None), 'value', '')) != 'and' {
        return None;
    }
    vals = [_unwrap_cfg(v) for v in list(getattr(cond, 'values', []) or [])];
    if len(vals) != 2 or not isinstance(vals[0], uni.Name)
        or str(vals[0].value) != cname {
        return None;
    }
    cmpe = vals[1];
    if not isinstance(cmpe, uni.CompareExpr) {
        return None;
    }
    ops = [str(getattr(o, 'value', '')) for o in list(getattr(cmpe, 'ops', []) or [])];
    rights = list(getattr(cmpe, 'rights', []) or []);
    if len(ops) != 1 or ops[0] != 'in' or len(rights) != 1 {
        return None;
    }
    lhs = getattr(cmpe, 'left', None);
    if not isinstance(lhs, uni.FuncCall) or _call_name(lhs) != 'jid' {
        return None;
    }
    prms = list(getattr(lhs, 'params', []) or []);
    if len(prms) != 1 {
        return None;
    }
    at = prms[0];
    if not isinstance(at, uni.AtomTrailer) or _subscript_lit(at) != 0 {
        return None;
    }
    ct = getattr(at, 'target', None);
    if not isinstance(ct, uni.Name) or str(ct.value) != cname {
        return None;
    }
    return _name_subscript(rights[0], kname);
}


def _hopcount_plan(scopes: list, l2: object) -> tuple {
    # -> (plan | None, reason). reason '' means "not a candidate" (silent);
    # any other reason is a DECLINE of a loop that did look like the nest.
    tgt = getattr(l2, 'target', None);
    if not isinstance(tgt, uni.TupleVal) {
        return (None, '');
    }
    tv = list(getattr(tgt, 'values', []) or []);
    if len(tv) != 2 or not isinstance(tv[0], uni.Name)
        or not isinstance(tv[1], uni.Name) {
        return (None, '');
    }
    dname = _items_dict_name(getattr(l2, 'collection', None));
    if dname is None {
        return (None, '');
    }
    kname = str(tv[0].value);
    vname = str(tv[1].value);
    body = list(getattr(l2, 'body', []) or []);
    if len(body) < 2 {
        return (None, 'body has no `cnt = 0` + inner loop');
    }
    cname = _zero_init_name(body[0]);
    if cname is None {
        return (None, 'first statement is not `<cnt> = 0`');
    }
    l3 = body[1];
    if not isinstance(l3, uni.InForStmt) {
        return (None, 'second statement is not the inner loop');
    }
    xt = getattr(l3, 'target', None);
    if not isinstance(xt, uni.Name) {
        return (None, 'inner loop target is not a bare name');
    }
    xname = str(xt.value);
    hop2 = _plain_hop(getattr(l3, 'collection', None), vname);
    if hop2 is None {
        return (None, 'inner loop is not a plain outbound hop from the value');
    }
    l3b = list(getattr(l3, 'body', []) or []);
    if len(l3b) != 2 {
        return (None, 'inner loop body is not exactly assign + if');
    }
    asg = l3b[0];
    if not isinstance(asg, uni.Assignment)
        or getattr(asg, 'aug_op', None) is not None {
        return (None, 'inner loop body does not start with an assignment');
    }
    atg = list(getattr(asg, 'target', []) or []);
    if len(atg) != 1 or not isinstance(atg[0], uni.Name) {
        return (None, 'inner assignment target is not a bare name');
    }
    lname = str(atg[0].value);
    hop3 = _plain_hop(getattr(asg, 'value', None), xname);
    if hop3 is None {
        return (None, 'inner assignment is not a plain outbound hop from the element');
    }
    ifs = l3b[1];
    if not isinstance(ifs, uni.IfStmt)
        or getattr(ifs, 'else_body', None) is not None {
        return (None, 'inner loop body does not end with an else-less if');
    }
    ifb = list(getattr(ifs, 'body', []) or []);
    if len(ifb) != 1 or not _is_increment(ifb[0], cname) {
        return (None, 'if body is not exactly `<cnt> += 1`');
    }
    sbase = _membership_base(getattr(ifs, 'condition', None), lname, kname);
    if sbase is None {
        return (None, 'condition is not `<c> and jid(<c>[0]) in <S>[<k>]`');
    }
    sname = str(getattr(sbase, 'value', ''));
    if sname == dname {
        return (None, 'the member map and the iterated dict are the same name');
    }
    # (1) `x` / `c` must not escape the inner loop: the lowering never
    #     materialises a Post or a Person, so any later use of either would
    #     read a name the emitted code no longer binds.
    inner: set = {id(n) for n in _walk(l3, uni.Name, [])};
    for scope in scopes {
        if scope is None {
            return (None, 'unresolved scope');
        }
        for nm in _walk(scope, uni.Name, []) {
            if str(nm.value) in (xname, lname) and id(nm) not in inner {
                return (None, 'the inner element or its hop escapes the inner loop');
            }
        }
    }
    # (2) `cnt` must be read nowhere inside the inner loop but the increment
    #     itself - the counter is replaced by a precomputed total, so a
    #     mid-loop read of it would observe a value that no longer exists.
    incr: set = {id(n) for n in _walk(ifb[0], uni.Name, [])};
    for nm in _walk(l3, uni.Name, []) {
        if str(nm.value) == cname and id(nm) not in incr {
            return (None, 'the counter is read inside the inner loop');
        }
    }
    # (3) the iterated dict and the member map must be untouched by the outer
    #     body: the hoisted call reads `<S>` ONCE, before the loop runs.
    outer_names = _walk_list(body, uni.Name);
    if any((str(n.value) == dname) for n in outer_names) {
        return (None, 'the iterated dict is referenced inside the loop');
    }
    smentions = [n for n in outer_names if str(n.value) == sname];
    if len(smentions) != 1 or smentions[0] is not sbase {
        return (None, 'the member map is referenced outside the membership test');
    }
    return (
        (sname, hop2[0], hop2[1], hop3[0], hop3[1], kname, cname, l3), ''
    );
}

# --- Rung D: the sort+slice that FOLLOWS the counting nest -------------------
# The ic5 tail is `rows.append({...})` per key, then `rows.sort(key=lambda d {
# (-d[<count>], d[<field>]) })`, then `rows[:K]` in a report: a top-K written
# as "materialise every key, order in python, keep K". Proving THAT shape lets
# the aggregation carry the ordering and the LIMIT, so the python loop runs K
# times instead of once per key (COMPILER_PLAN.md rung D).
#
# The lowering deliberately LEAVES the sort and the slice where they are (see
# _hopcount_topk_stmts): they are O(K) once the loop yields K rows, and keeping
# them makes the whole rung degradable - any SUPERSET of the top K in ANY order
# still sorts and slices to the same answer, which is what lets the runtime
# skip its ORDER BY when the key type's mirror is not available.


def _append_call(st: object) -> (tuple | None) {
    # `<rows>.append(<DictVal>);` as a statement -> (rows_name, the DictVal)
    e = getattr(st, 'expr', None) if isinstance(st, uni.ExprStmt) else st;
    if not isinstance(e, uni.FuncCall) {
        return None;
    }
    t = getattr(e, 'target', None);
    if not isinstance(t, uni.AtomTrailer) or not getattr(t, 'is_attr', False) {
        return None;
    }
    r = getattr(t, 'right', None);
    b = getattr(t, 'target', None);
    if not isinstance(r, uni.Name) or str(r.value) != 'append'
        or not isinstance(b, uni.Name) {
        return None;
    }
    prms = list(getattr(e, 'params', []) or []);
    if len(prms) != 1 or not isinstance(prms[0], uni.DictVal) {
        return None;
    }
    return (str(b.value), prms[0]);
}


def _row_dict_keys(dv: object, vname: str, cname: str, kname: str) -> (tuple | None) {
    # Every value of the appended dict must be a field read of the loop
    # element (`<v>.<f>`), the counter, or the key, and every key a string
    # literal -> (the count's dict key, {dict key: field name}). Anything
    # else - a call, an arithmetic expression, a nested literal - declines:
    # the emitted loop keeps this dict verbatim, so every name in it has to
    # still be bound in the rewritten frame.
    ckey = '';
    fmap: dict = {};
    for kv in list(getattr(dv, 'kv_pairs', []) or []) {
        ks = getattr(getattr(kv, 'key', None), 'lit_value', None);
        val = getattr(kv, 'value', None);
        if not isinstance(ks, str) {
            return None;
        }
        if isinstance(val, uni.Name) {
            nv = str(val.value);
            if nv == cname and not ckey {
                ckey = ks;
                continue;
            }
            if nv == kname {
                continue;
            }
            return None;
        }
        if isinstance(val, uni.AtomTrailer) and getattr(val, 'is_attr', False) {
            b = getattr(val, 'target', None);
            r = getattr(val, 'right', None);
            if isinstance(b, uni.Name) and str(b.value) == vname
                and isinstance(r, uni.Name) {
                fmap[ks] = str(r.value);
                continue;
            }
        }
        return None;
    }
    return (ckey, fmap) if ckey else None;
}


def _sort_keys(call: object) -> (tuple | None) {
    # `sort(key=lambda (d: dict) { (-d['<ck>'], d['<fk>']); })` -> (ck, fk).
    # DESCENDING count then ASCENDING field and nothing else: an ascending
    # count, a `reverse=`, a third component or a key that touches anything
    # but the element all decline, because the SQL orders one way only.
    prms = list(getattr(call, 'params', []) or []);
    if len(prms) != 1 {
        return None;
    }
    prm = prms[0];
    if not isinstance(prm, uni.KWPair)
        or str(getattr(getattr(prm, 'key', None), 'value', '')) != 'key'
        or not isinstance(getattr(prm, 'value', None), uni.LambdaExpr) {
        return None;
    }
    # getattr, not `prm.value.tail_return_expr()`: `KWPair.value` types as
    # `Expr`, which has no such member -> an extra E1030 on this file
    # (T7b deviation 1). getattr reads the same and holds the error count.
    tre = getattr(getattr(prm, 'value', None), 'tail_return_expr', None);
    if tre is None {
        return None;
    }
    body = _unwrap_cfg(tre());
    if not isinstance(body, uni.TupleVal) {
        return None;
    }
    vals = [_unwrap_cfg(v) for v in list(getattr(body, 'values', []) or [])];
    if len(vals) != 2 {
        return None;
    }
    neg = vals[0];
    if not isinstance(neg, uni.UnaryExpr)
        or str(getattr(getattr(neg, 'op', None), 'value', '')) != '-' {
        return None;   # ascending count: not this ordering
    }
    ck = _subscript_lit_str(getattr(neg, 'operand', None));
    fk = _subscript_lit_str(vals[1]);
    if ck is None or fk is None {
        return None;
    }
    b0 = getattr(getattr(neg, 'operand', None), 'target', None);
    b1 = getattr(vals[1], 'target', None);
    if not isinstance(b0, uni.Name) or not isinstance(b1, uni.Name)
        or str(b0.value) != str(b1.value) {
        return None;
    }
    nms = _walk(body, uni.Name, []);
    if len(nms) != 2 or any((str(n.value) != str(b0.value)) for n in nms) {
        return None;   # the key reads something other than the row
    }
    return (ck, fk);
}


def _rows_tail(scopes: list, rname: str, app: object) -> tuple {
    # `<rows>` must be a PRIVATE staging list: exactly one `= []` init, the
    # one append `app`, one `.sort(key=...)` and one `<rows>[:K]` with a
    # literal K inside a report. A read of `rows` after the sort, a second
    # append, a call taking it, a return - all decline, because the lowering
    # fills it with K rows instead of one per key. -> (result | None, reason).
    init = 0;
    srt = None;
    klim = None;
    seen: set = set();
    for scope in scopes {
        if not isinstance(scope, uni.UniNode) {
            return (None, 'unresolved scope');
        }
        for nm in _walk(scope, uni.Name, []) {
            if str(nm.value) != rname or id(nm) in seen {
                continue;
            }
            seen.add(id(nm));
            p = getattr(nm, 'parent', None);
            if isinstance(p, uni.AtomTrailer) and p.right is nm {
                continue;   # an attribute NAME that happens to match
            }
            if isinstance(p, uni.KWPair) and getattr(p, 'key', None) is nm {
                continue;
            }
            if isinstance(p, uni.Assignment) and nm in list(p.target or []) {
                lv = getattr(p, 'value', None);
                if isinstance(lv, uni.ListVal)
                    and not list(getattr(lv, 'values', []) or []) {
                    init += 1;
                    continue;
                }
                return (None, 'the row list is bound to something other than `[]`');
            }
            if not isinstance(p, uni.AtomTrailer) or p.target is not nm {
                return (None, 'the row list is read outside its append/sort/slice');
            }
            right = getattr(p, 'right', None);
            rv = str(getattr(right, 'value', '')) if isinstance(right, uni.Name)
                else '';
            if rv == 'append' {
                if getattr(p, 'parent', None) is app {
                    continue;
                }
                return (None, 'a second `<rows>.append(...)`');
            }
            if rv == 'sort' {
                fc = getattr(p, 'parent', None);
                if not isinstance(fc, uni.FuncCall) or fc.target is not p
                    or srt is not None {
                    return (None, 'more than one `<rows>.sort(...)`');
                }
                srt = _sort_keys(fc);
                if srt is None {
                    return (
                        None,
                        'the sort key is not `(-<row>[<count>], <row>[<field>])`'
                    );
                }
                continue;
            }
            if isinstance(right, uni.IndexSlice)
                and getattr(right, 'is_range', False) {
                if klim is not None or _ancestor(p, (uni.ReportStmt, )) is None {
                    return (None, 'the `[:K]` slice is not a single one inside a report');
                }
                slices = list(getattr(right, 'slices', []) or []);
                if len(slices) != 1
                    or getattr(slices[0], 'start', None) is not None
                    or getattr(slices[0], 'step', None) is not None {
                    return (None, 'the slice is not a bare `[:K]`');
                }
                kv = getattr(getattr(slices[0], 'stop', None), 'lit_value', None);
                if not isinstance(kv, int) or isinstance(kv, bool) or kv <= 0 {
                    return (None, 'K is not a positive int literal');
                }
                klim = kv;
                continue;
            }
            return (None, 'the row list is read outside its append/sort/slice');
        }
    }
    if init != 1 {
        return (None, 'the row list is not initialised exactly once as `[]`');
    }
    if srt is None or klim is None {
        return (None, 'the row list has no `.sort(key=...)` or no `[:K]` report');
    }
    return ((str(srt[0]), str(srt[1]), klim), '');
}


def _dict_elem_type(scopes: list, dname: str) -> (str | None) {
    # The archetype of `<D>`'s values, read off the ONE `<D>[<k>] = <e>` store
    # whose `<e>` is the element of an enclosing `for <e> in [... ->[?:T]]`.
    # That `T` is the type whose MIRROR the aggregation orders on, so an
    # ambiguous or unprovable one declines rather than guessing a table.
    found: set = set();
    seen: set = set();
    for scope in scopes {
        if not isinstance(scope, uni.UniNode) {
            return None;
        }
        for at in _walk(scope, uni.AtomTrailer, []) {
            if id(at) in seen {
                continue;
            }
            seen.add(id(at));
            b = getattr(at, 'target', None);
            if not isinstance(b, uni.Name) or str(b.value) != dname
                or not isinstance(getattr(at, 'right', None), uni.IndexSlice)
                or not _on_store_path(at) {
                continue;
            }
            asg = _ancestor(at, (uni.Assignment, ));
            val = getattr(asg, 'value', None) if asg is not None else None;
            if not isinstance(val, uni.Name) {
                return None;
            }
            lp = _ancestor(at, (uni.InForStmt, ));
            while lp is not None {
                lt = getattr(lp, 'target', None);
                if isinstance(lt, uni.Name) and str(lt.value) == str(val.value) {
                    break;
                }
                lp = _ancestor(lp, (uni.InForStmt, ));
            }
            if lp is None {
                return None;
            }
            t = _ranged_filter_type(getattr(lp, 'collection', None));
            if t is None {
                return None;
            }
            found.add(t);
        }
    }
    return str(list(found)[0]) if len(found) == 1 else None;
}


def _topk_plan(scopes: list, l2: object, plan: tuple) -> tuple {
    # -> (tplan | None, reason). Only ever called on a loop `_hopcount_plan`
    # already ACCEPTED, so the `(k, v)` target, the `<D>.items()` collection
    # and the whole counting nest are proven; this adds the tail. Reason is
    # never '' - a stamped hopcount loop that is not a top-K is worth one
    # debug line, unlike the thousands of ordinary `for`s rung B stays quiet
    # about.
    tv = list(getattr(getattr(l2, 'target', None), 'values', []) or []);
    kname = str(plan[5]);
    cname = str(plan[6]);
    vname = str(getattr(tv[1], 'value', ''));
    dname = str(_items_dict_name(getattr(l2, 'collection', None)));
    body = list(getattr(l2, 'body', []) or []);
    if len(body) != 3 {
        return (None, 'the loop body is not exactly `<cnt> = 0`, the nest and one append');
    }
    got = _append_call(body[2]);
    if got is None {
        return (None, 'the loop body does not end in `<rows>.append({...})`');
    }
    keys = _row_dict_keys(got[1], vname, cname, kname);
    if keys is None {
        return (None, 'the appended dict is not element field reads plus the count');
    }
    app = getattr(body[2], 'expr', None) if isinstance(body[2], uni.ExprStmt)
        else body[2];
    gotr = _rows_tail(scopes, str(got[0]), app);
    tail = gotr[0];
    if tail is None {
        return (None, str(gotr[1]));
    }
    if str(tail[0]) != str(keys[0]) {
        return (None, 'the sort orders by a key that is not the count');
    }
    fld = keys[1].get(str(tail[1]));
    if not fld {
        return (None, 'the sort tie-break is not a field read of the loop element');
    }
    kt = _dict_elem_type(scopes, dname);
    if kt is None {
        return (None, 'the iterated dict has no single provable element archetype');
    }
    return ((dname, vname, kt, str(fld), int(tail[2])), '');
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
                self._stamp_hopcount(nd);
            } except Exception as e {
                # rung B: same stance - any doubt leaves the nest as written
                if os.environ.get('JAC_EFFECT_DEBUG') {
                    sys.stderr.write(
                        'EFFECTPASS ' + str(nd.name)
                        + ' hopcount internal: ' + str(e) + chr(10)
                    );
                }
            }
            # C2: the projection audit reads the hopcount stamps (a use of the
            # element inside a nest the hopcount lowering DELETES is not an
            # observation), so the hopcount stamp has to be in place first.
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
        # Item #24 / T7: the trailing sufficiency threshold on the walker's
        # closure restates the walker's own sort+slice for the engine. When the
        # walker PROVES that restatement the compiler stamps the SITE and
        # PyastGenPass appends limit=K itself; the app stops spelling it.
        # Two sites are recognised: a `jclosure(...)` FuncCall (T1) and a
        # variable-length hop `[origin <-:E:*n:-> [?:T ..]]` (T7). Three
        # consumption shapes:
        #  (A)  hits = <site>;  for h in hits / for (x, d) in hits  -> rows
        #       carrying "distance", sorted distance-first, sliced [:K] -> K
        #  (A') for (x, d) in <site>            (no intermediate name) -> K
        #  (B)  hits[0][1] behind a bare emptiness test              -> 1
        # Sound per PHASE_D lever 2: after level d completes, >=K matches at
        # depth <= d determine the top-K under a distance-first order; the
        # stamp is withheld for ANY other consumption shape and the runtime
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
        ranged: list = [];
        seen: set = set();
        for scope in self._scopes_of(w) {
            if scope is None {
                continue;
            }
            for e in _walk(scope, uni.EdgeRefTrailer, []) {
                if _is_ranged(e) and id(e) not in seen {
                    seen.add(id(e));
                    ranged.append(e);
                }
            }
        }
        if len(calls) + len(ranged) != 1 {
            return;
        }
        is_call = bool(calls);
        site = calls[0] if is_call else ranged[0];
        if is_call {
            params = list(getattr(site, 'params', []) or []);
            if len(params) != 6 {
                return;   # limit already spelled (7), or not the plain shape
            }
            for prm in params {
                if isinstance(prm, uni.KWPair) {
                    return;
                }
            }
        }
        # binding: the site is the sole value of a one-Name assignment
        hsym = None;
        htgt = None;
        asg = _ancestor(site, (uni.Assignment, ));
        if asg is not None and getattr(asg, 'value', None) is site {
            tgts = list(getattr(asg, 'target', []) or []);
            if len(tgts) == 1 and isinstance(tgts[0], uni.Name) {
                hsym = getattr(tgts[0], 'sym', None);
                htgt = tgts[0];
            }
        }
        loop = None;
        if hsym is not None {
            # shape B: the result is consumed as a SINGLE element (`h[0]`,
            # guarded by a bare emptiness test) -> one nearest match is enough
            if _single_element_use(w, hsym, htgt) {
                site.closure_limit = 1;
                if os.environ.get('JAC_EFFECT_DEBUG') {
                    sys.stderr.write(
                        'EFFECTPASS ' + str(w.name)
                        + ' closure sufficiency limit=1 (single-element)' + chr(10)
                    );
                }
                return;
            }
            loops: list = [];
            for fr in UniPass.get_all_sub_nodes(nd=w, typ=uni.InForStmt) {
                coll = getattr(fr, 'collection', None);
                if isinstance(coll, uni.Name) and getattr(coll, 'sym', None) is hsym {
                    loops.append(fr);
                }
            }
            if len(loops) != 1 {
                return;
            }
            loop = loops[0];
        } elif not is_call {
            # shape A': the ranged chain IS the loop's collection
            pnt = getattr(site, 'parent', None);
            if isinstance(pnt, uni.InForStmt)
                and getattr(pnt, 'collection', None) is site {
                loop = pnt;
            }
        }
        if loop is None {
            return;
        }
        pair = _loop_pair(loop);
        if pair[0] is None and pair[1] is None {
            return;
        }
        klim = _shape_a_limit(w, loop, pair[0], pair[1]);
        if klim is None {
            return;
        }
        site.closure_limit = int(klim);
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
            if not params or isinstance(params[0], uni.KWPair) {
                continue;
            }
            # T7: `jobj(id, T)` names the archetype itself, so the walker no
            # longer writes `isinstance(x, T)` and the type comes from the
            # call's own 2nd argument instead.
            dflt: (str | None) = None;
            if fname == 'jobj' and len(params) == 2
                and isinstance(params[1], uni.Name) {
                dflt = str(params[1].value);
            } elif len(params) != 1 {
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
            proj = _projection_of(scopes, bind, tgt, dflt);
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
        # T7: the same proof over a ranged chain's loop element. Binding forms:
        # `for (x, d) in <ranged chain>` (also as a comprehension clause) and
        # `for (x, d) in hits` where `hits = <ranged chain>`. The stamp goes on
        # the EdgeRefTrailer; PyastGenPass turns it into the same
        # `_proj=(T, (fields...))` keyword the jobj sites get.
        rseen: set = set();
        for scope in scopes {
            if scope is None {
                continue;
            }
            for ert in _walk(scope, uni.EdgeRefTrailer, []) {
                if not _is_ranged(ert) or id(ert) in rseen {
                    continue;
                }
                rseen.add(id(ert));
                loop = None;
                hs = None;   # T7b: set when the chain is bound to a NAME
                pnt = getattr(ert, 'parent', None);
                if isinstance(pnt, (uni.InForStmt, uni.InnerCompr))
                    and getattr(pnt, 'collection', None) is ert {
                    loop = pnt;
                } else {
                    asg = _ancestor(ert, (uni.Assignment, ));
                    if asg is not None and getattr(asg, 'value', None) is ert {
                        tgts = list(getattr(asg, 'target', []) or []);
                        if len(tgts) == 1 and isinstance(tgts[0], uni.Name) {
                            hs = getattr(tgts[0], 'sym', None);
                        }
                    }
                    if hs is not None {
                        lseen: set = set();
                        over: list = [];
                        for sc2 in scopes {
                            if sc2 is None {
                                continue;
                            }
                            binds: list = _walk(sc2, uni.InForStmt, []);
                            binds.extend(_walk(sc2, uni.InnerCompr, []));
                            for fr in binds {
                                coll = getattr(fr, 'collection', None);
                                if id(fr) not in lseen and isinstance(coll, uni.Name)
                                    and getattr(coll, 'sym', None) is hs {
                                    lseen.add(id(fr));
                                    over.append(fr);
                                }
                            }
                        }
                        if len(over) == 1 {
                            loop = over[0];
                        }
                    }
                }
                if loop is None {
                    continue;
                }
                pair = _loop_pair(loop);
                if pair[1] is None or pair[2] is None {
                    continue;   # a ranged chain yields PAIRS: need `(x, d)`
                }
                rproj = _projection_of(
                    scopes, loop, pair[2], _ranged_filter_type(ert)
                );
                if os.environ.get('JAC_EFFECT_DEBUG') {
                    sys.stderr.write(
                        'EFFECTPASS ' + str(w.name) + ' hydrate projection ranged@'
                        + str(getattr(ert.loc, 'first_line', '?')) + ' '
                        + (str(rproj) if rproj is not None else 'declined') + chr(10)
                    );
                }
                if rproj is not None {
                    ert.hydrate_proj = rproj;
                }
                # T7b: ids-only materialization, the level BELOW T6's field
                # projection. Zero projected fields says nothing is read off
                # the element; _ids_only_of says every use is `jid(x)` - the
                # walker consumes IDS, so the engine can hand back (hex,
                # depth) pairs and build no anchor and no archetype stand-in
                # at all. Bound through a NAME the elements can still escape
                # the loop (`report hits`), so the name must be referenced
                # exactly ONCE - as that single loop's collection.
                if rproj is not None and not rproj[1] {
                    esc = 0;
                    eseen: set = set();
                    if hs is not None {
                        for sc3 in scopes {
                            if sc3 is None {
                                continue;
                            }
                            for nm3 in _walk(sc3, uni.Name, []) {
                                if getattr(nm3, 'sym', None) is not hs
                                    or id(nm3) in eseen {
                                    continue;
                                }
                                eseen.add(id(nm3));
                                p3 = getattr(nm3, 'parent', None);
                                if isinstance(p3, uni.Assignment)
                                    and nm3 in list(p3.target or []) {
                                    continue;
                                }
                                esc += 1;
                            }
                        }
                    }
                    if (hs is None or esc == 1)
                        and _ids_only_of(scopes, loop, pair[2]) {
                        ert.ids_only = True;
                        if os.environ.get('JAC_EFFECT_DEBUG') {
                            sys.stderr.write(
                                'EFFECTPASS ' + str(w.name)
                                + ' hydrate projection ranged@'
                                + str(getattr(ert.loc, 'first_line', '?'))
                                + ' ids_only' + chr(10)
                            );
                        }
                    }
                }
            }
        }
        # C2: the same proof over a PLAIN (unranged) edge-reference loop -
        # `for x in [ <origin> <-:E:- [?:T] ]`. The type comes from the
        # chain's own `[?:T]` filter; the element may additionally escape
        # into ONE local staging dict (`D[k] = x`, read back by
        # `for (k2, v2) in D.items()`), which _dict_alias_fields audits.
        # Uses that sit inside a nest rung B's hopcount stamp DELETES are
        # not observations of the element and are skipped.
        dead: set = set();
        for scope in scopes {
            if scope is None {
                continue;
            }
            for l2 in _walk(scope, uni.InForStmt, []) {
                plan = getattr(l2, 'hopcount_plan', None);
                if plan is not None {
                    dead.add(id(plan[7]));
                }
            }
        }
        pseen: set = set();
        for scope in scopes {
            if scope is None {
                continue;
            }
            for ert in _walk(scope, uni.EdgeRefTrailer, []) {
                if _is_ranged(ert) or id(ert) in pseen
                    or getattr(ert, 'edges_only', False)
                    or _in_dead(ert, dead) {
                    continue;   # a chain the hopcount lowering deletes
                }
                pseen.add(id(ert));
                etype = _ranged_filter_type(ert);
                pnt = getattr(ert, 'parent', None);
                if etype is None
                    or not isinstance(pnt, (uni.InForStmt, uni.InnerCompr))
                    or getattr(pnt, 'collection', None) is not ert
                    or not isinstance(getattr(pnt, 'target', None), uni.Name) {
                    continue;   # not even a candidate: stay silent
                }
                tgt2 = pnt.target;
                vn2 = str(getattr(tgt2, 'value', ''));
                aliases: set = set();
                for sc4 in scopes {
                    if sc4 is None {
                        continue;
                    }
                    for nm4 in _walk(sc4, uni.Name, []) {
                        if str(nm4.value) != vn2 {
                            continue;
                        }
                        dn = _dict_store_base(nm4);
                        if dn is not None {
                            aliases.add(dn);
                        }
                    }
                }
                pproj = None;
                alias = None;
                why = 'a use of the element is not admissible';
                if len(aliases) > 1 {
                    why = 'element escapes into more than one dict';
                } else {
                    alias = str(list(aliases)[0]) if aliases else None;
                    pproj = _projection_of(scopes, pnt, tgt2, etype, alias, dead);
                    if pproj is not None and alias is not None {
                        af = _dict_alias_fields(scopes, alias, vn2, etype, dead);
                        if af is None {
                            pproj = None;
                            why = 'dict alias ' + str(alias) + ' is not private';
                        } else {
                            pproj = (
                                pproj[0], tuple(sorted(set(pproj[1]) | af))
                            );
                        }
                    }
                }
                if os.environ.get('JAC_EFFECT_DEBUG') {
                    sys.stderr.write(
                        'EFFECTPASS ' + str(w.name) + ' hydrate projection edgeref@'
                        + str(getattr(ert.loc, 'first_line', '?')) + ' '
                        + (
                            str(pproj)
                                if pproj is not None
                                else ('declined:' + why)
                        ) + chr(10)
                    );
                }
                # D4: one rung BELOW the projection - when the ONLY reader of
                # the staged dict's values is the rung-D top-K tail, and the
                # element itself is observed only as `jid(x)` (T7b's rule),
                # this nest needs no objects at all: it stages IDS, and the K
                # winners are hydrated by the tail's own typed `jobj` from the
                # same mirror columns `pproj` names. Declines keep C2's
                # projection - a walker whose tail still reads Phi objects
                # would otherwise get hex strings where it wanted archetypes.
                d4 = None;
                why4 = 'the staging dict has no single rung-D top-K reader';
                if pproj is not None and alias is not None {
                    l2 = _topk_items_loop(scopes, str(alias));
                    if l2 is not None {
                        tp = getattr(l2, 'hopcount_topk', None);
                        dead4: set = set(dead);
                        if str(tp[1]) == vn2 {
                            # the tail REBINDS this name at its own loop
                            # header, so nothing under it can observe THIS
                            # binding (python binds the target before the
                            # body runs) - the same "not an observation"
                            # argument the hopcount `dead` set makes
                            dead4.add(id(l2));
                        }
                        if _ids_only_of(scopes, pnt, tgt2, str(alias), dead4) {
                            d4 = pproj;
                        } else {
                            why4 = 'the element is observed outside the top-K tail';
                        }
                    }
                }
                if os.environ.get('JAC_EFFECT_DEBUG')
                    and pproj is not None and alias is not None {
                    sys.stderr.write(
                        'EFFECTPASS ' + str(w.name) + ' ids_only edgeref@'
                        + str(getattr(ert.loc, 'first_line', '?')) + ' '
                        + ('accepted' if d4 is not None else 'declined:' + why4)
                        + chr(10)
                    );
                }
                if d4 is not None {
                    ert.ids_only = True;
                    # the tail's `<v> = <D>[<k>]` becomes `jobj(<D>[<k>], T)`;
                    # this is the T6 stamp that jobj site would have carried.
                    # setattr, not `l2.topk_ids_proj =`: `l2` types as
                    # `object | None` here and a direct store adds an E1099
                    # (T7b deviation 1) - same store, error count held.
                    setattr(l2, 'topk_ids_proj', d4);
                } elif pproj is not None {
                    ert.hydrate_proj = pproj;
                }
            }
        }
    }

    def _stamp_hopcount(self: EffectPass, w: uni.Archetype) -> None {
        # Rung B: prove the ic5 counting nest (see _hopcount_plan above) and
        # stamp the OUTER loop with the relational plan. PyastGenPass then
        # hoists one `jhopcount(<S>, E2, T2, E3, T3)` in front of the loop and
        # replaces `cnt = 0` + the whole inner nest with a dict lookup, so the
        # request costs ONE statement instead of one per inner-hop element.
        # Only reached for a walker that already proved effect-free, which is
        # what makes "the loop reads and counts, nothing else" checkable at
        # all. Advisory like the other two stamps: no stamp = today's codegen.
        import os;
        import sys;
        scopes = self._scopes_of(w);
        seen: set = set();
        for scope in scopes {
            if scope is None {
                continue;
            }
            for l2 in _walk(scope, uni.InForStmt, []) {
                if id(l2) in seen {
                    continue;
                }
                seen.add(id(l2));
                got = _hopcount_plan(scopes, l2);
                plan = got[0];
                why = str(got[1]);   # str(): a bare `tuple` element is `object`
                if plan is None and not why {
                    continue;   # not the nest at all: nothing to report
                }
                if os.environ.get('JAC_EFFECT_DEBUG') {
                    sys.stderr.write(
                        'EFFECTPASS ' + str(w.name) + ' hopcount@'
                        + str(getattr(l2.loc, 'first_line', '?')) + ' '
                        + ('accepted' if plan is not None else 'declined:' + why)
                        + chr(10)
                    );
                }
                if plan is not None {
                    l2.hopcount_plan = plan;
                    # Rung D: the same loop's TAIL (append / sort / [:K]).
                    # A second, independent stamp rather than a longer plan
                    # tuple, so a loop that is a counting nest but not a
                    # top-K keeps rung B's codegen byte-identical.
                    got2 = _topk_plan(scopes, l2, plan);
                    tplan = got2[0];
                    why2 = str(got2[1]);
                    if os.environ.get('JAC_EFFECT_DEBUG') {
                        sys.stderr.write(
                            'EFFECTPASS ' + str(w.name) + ' topk@'
                            + str(getattr(l2.loc, 'first_line', '?')) + ' '
                            + ('accepted' if tplan is not None
                                else 'declined:' + why2)
                            + chr(10)
                        );
                    }
                    if tplan is not None {
                        l2.hopcount_topk = tplan;
                    }
                }
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
