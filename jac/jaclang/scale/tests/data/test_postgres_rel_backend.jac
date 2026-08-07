"""Conformance suite for PostgresRelBackend -- the edges-as-rows Postgres L3.

Extends the KV backend (test_postgres_backend.jac covers the inherited
surface); this suite covers only the rel delta: the edges index table
(lifecycle rides apply()'s transaction) and resolve_hop_sql (indexed SQL hop
resolution). Runs against a SEPARATE local database (jactest_rel) so the two
PG suites cannot truncate each other's state.

Test names carry a phase prefix ("rows: ...", "hop: ...", "caps: ...") so
gates can run `-f "rows"` etc.
"""

import os;
import shutil;
import psycopg;
import from tempfile { mkdtemp }
import from uuid { UUID, uuid4 }
import from psycopg.types.json { Jsonb }

import from jaclang.jac0core.archetype { Root, GenericEdge, EdgeAnchor, NodeAnchor }
import from jaclang.jac0core.runtime { JacRuntime }
import from jaclang.runtimelib.context { ExecutionContext }
import from jaclang.runtimelib.changeset { ChangeSet, WriteOp, ApplyReport }
import from jaclang.runtimelib.serializer { Serializer }
import from jaclang.runtimelib.query_plan { QueryPlan }
import from jaclang.project.config { JacConfig, set_config }
import from jaclang.scale.memory.memory_hierarchy { PostgresRelBackend }
import from jaclang.runtimelib.utils { order_pushdown_cfg }

glob _DSN = os.environ.get('POSTGRESQL_REL_URI', 'postgresql:///jactest_rel'),
     _EDGE_ANCHOR: any = EdgeAnchor;


# Distinct archetype names: the Serializer registry is process-global, so
# reusing the KV suite's Person/Knows here would collide if both suites load.
node RelPerson {
    has name: str = "";
}


node RelPet {
    has name: str = "";
}


edge RelKnows {}


edge RelLikes {}


# ---------------------------------------------------------------------------
# Harness helpers (mirroring test_postgres_backend.jac conventions)
# ---------------------------------------------------------------------------
"""A raw autocommit psycopg connection for injection / verification."""
def _raw -> any {
    return psycopg.connect(_DSN, autocommit=True);
}


"""A fresh backend on a truncated store. First construction bootstraps the
schema (anchors tables + edges); then TRUNCATE working tables."""
def _fresh -> PostgresRelBackend {
    be: PostgresRelBackend = PostgresRelBackend(dsn=_DSN, pool_min=1, pool_max=3);
    raw: any = _raw();
    raw.execute("TRUNCATE anchors, anchors_quarantine, aliases");
    raw.execute("TRUNCATE edges RESTART IDENTITY");
    raw.close();
    return be;
}


"""A persistent Root anchor rooted at itself."""
def _root_anchor -> any {
    r: any = Root();
    a: any = r.__jac__;
    a.persistent = True;
    setattr(a, 'root', a.id);
    return a;
}


"""A persistent node anchor of the given archetype instance, rooted at `r`."""
def _node(arch: any, r: any) -> any {
    a: any = arch.__jac__;
    a.persistent = True;
    setattr(a, 'root', r.id);
    return a;
}


"""A typed EdgeAnchor source->target."""
def _tedge(arch: any, source: any, target: any, undirected: bool = False) -> any {
    eanch: any = _EDGE_ANCHOR(
        archetype=arch, source=source, target=target, is_undirected=undirected
    );
    arch.__jac__ = eanch;
    eanch.persistent = True;
    setattr(eanch, 'root', source.id);
    return eanch;
}


"""Apply a create unit linking source -e-> target (node creates included when
given); returns the ApplyReport."""
def _link(be: any, e: any, creates: list) -> any {
    cs: any = ChangeSet();
    for a in creates {
        cs.record_create(a);
    }
    cs.record_create(e);
    src: any = e.source;
    tgt: any = e.target;
    src.edges.append(e);
    tgt.edges.append(e);
    cs.record_edge_delta(src, [e.id], []);
    if tgt.id != src.id {
        cs.record_edge_delta(tgt, [e.id], []);
    }
    return be.apply(cs);
}


"""Count edges rows matching a predicate column."""
def _edge_rows(raw: any, where: str, params: tuple) -> list {
    return raw.execute(
        f"SELECT edge_id, source, target, edge_type, is_undirected, seq "
        f"FROM edges WHERE {where} ORDER BY seq",
        params
    ).fetchall();
}


"""Seed the canonical hop graph on a fresh backend. Returns dict of anchors.

    R(root) ; A,B,C(RelPerson) ; P(RelPet)
    A -RelKnows-> B      (e1, first)
    A -RelKnows-> C      (e2)
    A -RelLikes-> P      (e3)
    D -RelKnows-> A      (e4, gives A an inbound)
    A <-RelKnows(undirected)-> U   (e5, undirected edge A->U)
"""
def _seed_graph(be: any) -> dict {
    r: any = _root_anchor();
    cs0: any = ChangeSet();
    cs0.record_create(r);
    be.apply(cs0);

    a: any = _node(RelPerson(name="A"), r);
    b: any = _node(RelPerson(name="B"), r);
    c: any = _node(RelPerson(name="C"), r);
    d: any = _node(RelPerson(name="D"), r);
    u: any = _node(RelPerson(name="U"), r);
    p: any = _node(RelPet(name="P"), r);

    e1: any = _tedge(RelKnows(), a, b);
    rep: any = _link(be, e1, [a, b]);
    assert not rep.failed;
    e2: any = _tedge(RelKnows(), a, c);
    assert not _link(be, e2, [c]).failed;
    e3: any = _tedge(RelLikes(), a, p);
    assert not _link(be, e3, [p]).failed;
    e4: any = _tedge(RelKnows(), d, a);
    assert not _link(be, e4, [d]).failed;
    e5: any = _tedge(RelKnows(), a, u, undirected=True);
    assert not _link(be, e5, [u]).failed;

    return {
        'r': r,
        'a': a,
        'b': b,
        'c': c,
        'd': d,
        'u': u,
        'p': p,
        'e1': e1,
        'e2': e2,
        'e3': e3,
        'e4': e4,
        'e5': e5
    };
}


# ===========================================================================
# rows phase -- edge-row lifecycle inside apply()
# ===========================================================================
test "rows: edges table bootstrapped with indexes" {
    be: any = _fresh();
    raw: any = _raw();
    rows: any = raw.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public'"
    ).fetchall();
    tables: set = {x[0] for x in rows};
    assert 'edges' in tables;
    idx: any = raw.execute(
        "SELECT indexname FROM pg_indexes WHERE tablename='edges'"
    ).fetchall();
    names: set = {x[0] for x in idx};
    assert 'idx_edges_src' in names;
    assert 'idx_edges_tgt' in names;
    raw.close();
    be.close();
}


test "rows: EDGE_CREATE inserts edge row in same unit" {
    be: any = _fresh();
    r: any = _root_anchor();
    cs0: any = ChangeSet();
    cs0.record_create(r);
    be.apply(cs0);
    a: any = _node(RelPerson(name="A"), r);
    b: any = _node(RelPerson(name="B"), r);
    e: any = _tedge(RelKnows(), a, b);
    rep: any = _link(be, e, [a, b]);
    assert not rep.failed;
    raw: any = _raw();
    rows: any = _edge_rows(raw, "edge_id = %s", (str(e.id), ));
    assert len(rows) == 1;
    # UUID columns: psycopg returns uuid.UUID objects.
    assert rows[0][1] == a.id;
    assert rows[0][2] == b.id;
    assert rows[0][3] == 'RelKnows';
    assert rows[0][4] is False;
    anch: any = raw.execute(
        "SELECT count(*) FROM anchors WHERE id = %s", (str(e.id), )
    ).fetchone();
    assert anch[0] == 1;
    raw.close();
    be.close();
}


test "rows: EDGE_DELETE removes edge row" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    e1: any = g['e1'];
    cs: any = ChangeSet();
    cs.record_delete(e1);
    rep: any = be.apply(cs);
    assert not rep.failed;
    raw: any = _raw();
    assert len(_edge_rows(raw, "edge_id = %s", (str(e1.id), ))) == 0;
    anch: any = raw.execute(
        "SELECT count(*) FROM anchors WHERE id = %s", (str(e1.id), )
    ).fetchone();
    assert anch[0] == 0;
    # Untouched edges survive.
    assert len(_edge_rows(raw, "TRUE", ())) == 4;
    raw.close();
    be.close();
}


test "rows: NODE_DELETE sweeps touching edge rows" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    a: any = g['a'];
    cs: any = ChangeSet();
    # Python-side cascade normally stages the edge deletes too; the sweep must
    # clean up even when it doesn't (defensive vs orphan rows).
    cs.intents[a.id] = __create_delete_intent(a);
    rep: any = be.apply(cs);
    assert not rep.failed;
    raw: any = _raw();
    rows: any = _edge_rows(raw, "source = %s OR target = %s", (str(a.id), str(a.id)));
    assert len(rows) == 0;
    raw.close();
    be.close();
}


"""Build a bare NODE_DELETE intent without record_delete's cascade staging."""
def __create_delete_intent(anchor: any) -> any {
    import from jaclang.runtimelib.changeset { WriteIntent }
    return WriteIntent(op=WriteOp.NODE_DELETE, anchor=anchor);
}


test "rows: put() of an EdgeAnchor upserts edge row" {
    be: any = _fresh();
    r: any = _root_anchor();
    a: any = _node(RelPerson(name="A"), r);
    b: any = _node(RelPerson(name="B"), r);
    e: any = _tedge(RelKnows(), a, b);
    be.put(a);
    be.put(b);
    be.put(e);
    raw: any = _raw();
    rows: any = _edge_rows(raw, "edge_id = %s", (str(e.id), ));
    assert len(rows) == 1;
    assert rows[0][3] == 'RelKnows';
    raw.close();
    be.close();
}


test "rows: conflicted unit rolls back edge rows" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    a: any = g['a'];
    b: any = g['b'];
    # New edge + a doomed CAS delta in the same unit: apply() rolls the whole
    # unit back on conflict, so the new edge row must vanish with it.
    # _pg_merge_write's populated path derives the delta from edge_delta()
    # (initial-ids snapshot), not intent.edges_added -- snapshot before append.
    e6: any = _tedge(RelKnows(), b, a);
    b._initial_edge_ids = frozenset({ed.id for ed in b.edges});
    cs: any = ChangeSet();
    cs.record_create(e6);
    b.edges.append(e6);
    cs.record_edge_delta(b, [e6.id], []);
    doomed: any = cs.intents[b.id];
    doomed.cas_version = 999999;
    rep: any = be.apply(cs);
    assert rep.conflicts;
    assert rep.applied == [];
    raw: any = _raw();
    assert len(_edge_rows(raw, "edge_id = %s", (str(e6.id), ))) == 0;
    raw.close();
    be.close();
}


# ===========================================================================
# hop phase -- resolve_hop_sql
# ===========================================================================
test "hop: OUT with edge and node filter" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    res: any = be.resolve_hop_sql({g['a'].id}, 'RelKnows', 'RelPerson', 2, None);
    assert res == {g['b'].id, g['c'].id, g['u'].id};
    be.close();
}


test "hop: IN direction" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    res: any = be.resolve_hop_sql({g['b'].id}, 'RelKnows', None, 1, None);
    assert res == {g['a'].id};
    be.close();
}


test "hop: ANY direction unions both ends" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    res: any = be.resolve_hop_sql({g['a'].id}, 'RelKnows', None, 3, None);
    assert res == {g['b'].id, g['c'].id, g['d'].id, g['u'].id};
    be.close();
}


test "hop: undirected edge matches reverse direction" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    # e5 is A->U undirected: OUT from U must still reach A.
    res: any = be.resolve_hop_sql({g['u'].id}, 'RelKnows', None, 2, None);
    assert res == {g['a'].id};
    # ...but a plain directed edge is NOT reversible: OUT from B is empty.
    res2: any = be.resolve_hop_sql({g['b'].id}, 'RelKnows', None, 2, None);
    assert res2 == set();
    be.close();
}


test "hop: no filters returns all OUT neighbors" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    res: any = be.resolve_hop_sql({g['a'].id}, None, None, 2, None);
    assert res == {g['b'].id, g['c'].id, g['p'].id, g['u'].id};
    be.close();
}


test "hop: node-type filter joins anchors.arch_type" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    res: any = be.resolve_hop_sql({g['a'].id}, None, 'RelPet', 2, None);
    assert res == {g['p'].id};
    be.close();
}


test "hop: multi-origin frontier unions" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    res: any = be.resolve_hop_sql(
        {g['a'].id, g['d'].id}, 'RelKnows', 'RelPerson', 2, None
    );
    assert res == {g['a'].id, g['b'].id, g['c'].id, g['u'].id};
    be.close();
}


test "hop: ordered slice returns creation order with first-seen dedup" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    a: any = g['a'];
    # Duplicate edge A->B (later seq): B must appear once, at its FIRST seq.
    edup: any = _tedge(RelKnows(), a, g['b']);
    assert not _link(be, edup, []).failed;
    full: any = be.resolve_hop_sql({a.id}, 'RelKnows', None, 2, slice(None, None));
    assert full == [g['b'].id, g['c'].id, g['u'].id];
    sliced: any = be.resolve_hop_sql({a.id}, 'RelKnows', None, 2, slice(1, 3));
    assert sliced == [g['c'].id, g['u'].id];
    be.close();
}


test "hop: JAC_ORDER_PUSHDOWN orders by archetype field in PG" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    prior: any = os.environ.pop('JAC_ORDER_PUSHDOWN', None);
    try {
        os.environ['JAC_ORDER_PUSHDOWN'] = 'RelPerson:name:asc';
        res: any = be.resolve_hop_sql({g['a'].id}, 'RelKnows', 'RelPerson', 2, None);
        # Flag match -> ordered LIST (asc by name: B, C, U), not a set.
        assert res == [g['b'].id, g['c'].id, g['u'].id];
        os.environ['JAC_ORDER_PUSHDOWN'] = 'RelPerson:name:desc';
        res2: any = be.resolve_hop_sql({g['a'].id}, 'RelKnows', 'RelPerson', 2, None);
        assert res2 == [g['u'].id, g['c'].id, g['b'].id];
        # Non-matching node type -> untouched set semantics.
        res3: any = be.resolve_hop_sql({g['a'].id}, None, 'RelPet', 2, None);
        assert res3 == {g['p'].id};
    } finally {
        if prior is None {
            os.environ.pop('JAC_ORDER_PUSHDOWN', None);
        } else {
            os.environ['JAC_ORDER_PUSHDOWN'] = prior;
        }
    }
    be.close();
}


test "order_pushdown_cfg fails loud on malformed JAC_ORDER_PUSHDOWN" {
    prior: any = os.environ.pop('JAC_ORDER_PUSHDOWN', None);
    try {
        # wrong arity (no direction segment).
        os.environ['JAC_ORDER_PUSHDOWN'] = 'RelPerson:name';
        raised: bool = False;
        try {
            order_pushdown_cfg('RelPerson');
        } except ValueError as e {
            raised = True;
            assert 'RelPerson:name' in str(e);
        }
        assert raised;

        # empty field segment.
        os.environ['JAC_ORDER_PUSHDOWN'] = 'RelPerson::desc';
        raised = False;
        try {
            order_pushdown_cfg('RelPerson');
        } except ValueError as e {
            raised = True;
            assert 'RelPerson::desc' in str(e);
        }
        assert raised;

        # bad direction.
        os.environ['JAC_ORDER_PUSHDOWN'] = 'RelPerson:name:sideways';
        raised = False;
        try {
            order_pushdown_cfg('RelPerson');
        } except ValueError as e {
            raised = True;
            assert 'RelPerson:name:sideways' in str(e);
        }
        assert raised;

        # bad limit segment (non-int / non-positive).
        os.environ['JAC_ORDER_PUSHDOWN'] = 'RelPerson:name:desc:twenty';
        raised = False;
        try {
            order_pushdown_cfg('RelPerson');
        } except ValueError as e {
            raised = True;
            assert 'twenty' in str(e);
        }
        assert raised;
        os.environ['JAC_ORDER_PUSHDOWN'] = 'RelPerson:name:desc:0';
        raised = False;
        try {
            order_pushdown_cfg('RelPerson');
        } except ValueError {
            raised = True;
        }
        assert raised;

        # happy paths still parse, direction case/whitespace-insensitive.
        os.environ['JAC_ORDER_PUSHDOWN'] = 'T:f:asc';
        assert order_pushdown_cfg('T') == ('T', 'f', 'ASC', None);
        os.environ['JAC_ORDER_PUSHDOWN'] = 'T:f:DESC';
        assert order_pushdown_cfg('T') == ('T', 'f', 'DESC', None);
        os.environ['JAC_ORDER_PUSHDOWN'] = 'T:f:desc:20';
        assert order_pushdown_cfg('T') == ('T', 'f', 'DESC', 20);
    } finally {
        if prior is None {
            os.environ.pop('JAC_ORDER_PUSHDOWN', None);
        } else {
            os.environ['JAC_ORDER_PUSHDOWN'] = prior;
        }
    }
}


test "hop: empty frontier and unknown type return empty not None" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    assert be.resolve_hop_sql(set(), 'RelKnows', None, 2, None) == set();
    assert be.resolve_hop_sql(set(), 'RelKnows', None, 2, slice(None, None)) == [];
    assert be.resolve_hop_sql({g['a'].id}, 'NoSuchEdge', None, 2, None) == set();
    be.close();
}


# ===========================================================================
# chain phase -- resolve_chain_sql (whole traversal, one round-trip)
# ===========================================================================
test "chain: two-hop OUT resolves in one round-trip" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    p2: any = _node(RelPet(name="P2"), g['r']);
    e6: any = _tedge(RelLikes(), g['b'], p2);
    assert not _link(be, e6, [p2]).failed;
    before: any = be.rel_chain_count;
    res: any = be.resolve_chain_sql(
        {g['a'].id}, [('RelKnows', 'RelPerson', 2), ('RelLikes', 'RelPet', 2)]
    );
    # a -Knows-> {b,c,u}; only b -Likes-> p2.
    assert res == {p2.id};
    assert be.rel_chain_count == before + 1;
    be.close();
}


test "chain: direction mix and dead mid-frontier" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    # IN then OUT: b <-Knows- a, then a -Likes-> p.
    res: any = be.resolve_chain_sql(
        {g['b'].id}, [('RelKnows', None, 1), ('RelLikes', 'RelPet', 2)]
    );
    assert res == {g['p'].id};
    # Unknown edge type mid-chain -> empty set, not None.
    res2: any = be.resolve_chain_sql(
        {g['a'].id}, [('NoSuchEdge', None, 2), ('RelLikes', None, 2)]
    );
    assert res2 == set();
    # Empty chain -> None (caller falls back).
    assert be.resolve_chain_sql({g['a'].id}, []) is None;
    be.close();
}


test "chain: order pushdown on final hop returns ordered list" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    prior: any = os.environ.pop('JAC_ORDER_PUSHDOWN', None);
    try {
        os.environ['JAC_ORDER_PUSHDOWN'] = 'RelPerson:name:desc';
        # d -Knows-> a, then a -Knows-> {b,c,u}: desc by name = [u, c, b].
        res: any = be.resolve_chain_sql(
            {g['d'].id}, [('RelKnows', 'RelPerson', 2), ('RelKnows', 'RelPerson', 2)]
        );
        assert res == [g['u'].id, g['c'].id, g['b'].id];
    } finally {
        if prior is None {
            os.environ.pop('JAC_ORDER_PUSHDOWN', None);
        } else {
            os.environ['JAC_ORDER_PUSHDOWN'] = prior;
        }
    }
    be.close();
}


# ===========================================================================
# seam phase -- resolver dispatch through a live runtime context
# ===========================================================================
"""Run body() inside a runtime context whose TieredMemory L3 is the rel
backend and GTI is OFF (topology_index=False) -- proving SQL hops need no
blob. Returns (backend, traversal_result_names)."""
def _with_rel_ctx(be: any) -> tuple {
    tmpdir = mkdtemp();
    orig_base = JacRuntime.get_base_path_dir();
    names: any = None;
    try {
        cfg = JacConfig();
        cfg.run.topology_index = False;
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);
        mem: any = ctx.mem;
        mem.l3 = be;

        r = root;
        for i in range(3) {
            r +>:RelKnows:+> RelPerson(name=f"p{i}");
        }
        r_any: any = r;
        ra: any = r_any.__jac__;
        cs: any = ChangeSet();
        cs.record_create(ra);
        for e in ra.edges {
            ea: any = e;
            cs.record_create(ea);
            cs.record_create(ea.target);
        }
        rep: any = be.apply(cs);
        assert rep.ok();

        found = [r->:RelKnows:->];
        names = sorted([p.name for p in found]);
        ctx.close();
    } finally {
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
    return (be, names);
}


test "seam: resolve_hop routes through SQL with GTI off" {
    be: any = _fresh();
    prior: any = os.environ.pop('JAC_TOPOLOGY_SQL', None);
    try {
        (be2, names) = _with_rel_ctx(be);
        assert names == ['p0', 'p1', 'p2'];
        assert be.rel_hop_count > 0 , "hop must have been answered by SQL";
        assert be.rel_hop_fallback_count == 0;
    } finally {
        if prior is not None {
            os.environ['JAC_TOPOLOGY_SQL'] = prior;
        }
    }
    be.close();
}


test "seam: JAC_TOPOLOGY_SQL=0 falls back to walk, same result" {
    be: any = _fresh();
    prior: any = os.environ.pop('JAC_TOPOLOGY_SQL', None);
    os.environ['JAC_TOPOLOGY_SQL'] = '0';
    try {
        (be2, names) = _with_rel_ctx(be);
        assert names == ['p0', 'p1', 'p2'];
        assert be.rel_hop_count == 0 , "SQL path must be disabled";
    } finally {
        if prior is None {
            os.environ.pop('JAC_TOPOLOGY_SQL', None);
        } else {
            os.environ['JAC_TOPOLOGY_SQL'] = prior;
        }
    }
    be.close();
}


test "seam: two-hop traversal collapses into one chain SQL call" {
    be: any = _fresh();
    tmpdir = mkdtemp();
    orig_base = JacRuntime.get_base_path_dir();
    prior: any = os.environ.pop('JAC_TOPOLOGY_SQL_CHAIN', None);
    try {
        cfg = JacConfig();
        cfg.run.topology_index = False;
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);
        mem: any = ctx.mem;
        mem.l3 = be;

        r = root;
        ps: list = [];
        for i in range(3) {
            p = RelPerson(name=f"p{i}");
            r +>:RelKnows:+> p;
            ps.append(p);
        }
        deep = RelPerson(name="deep");
        p0: any = ps[0];
        p0 +>:RelKnows:+> deep;

        r_any: any = r;
        ra: any = r_any.__jac__;
        cs: any = ChangeSet();
        cs.record_create(ra);
        for e in ra.edges {
            ea: any = e;
            cs.record_create(ea);
            cs.record_create(ea.target);
        }
        p0a: any = p0.__jac__;
        deep_e: any = p0a.edges[-1];
        cs.record_create(deep_e);
        cs.record_create(deep_e.target);
        rep: any = be.apply(cs);
        assert not rep.failed;

        found = [r->:RelKnows:->[?:RelPerson]->:RelKnows:->[?:RelPerson]];
        names = sorted([p.name for p in found]);
        assert names == ['deep'];
        assert be.rel_chain_count == 1 , "two-hop must be ONE chain SQL call";

        # Kill switch: same traversal, per-hop path, same answer.
        os.environ['JAC_TOPOLOGY_SQL_CHAIN'] = '0';
        hops_before: any = be.rel_hop_count;
        found2 = [r->:RelKnows:->[?:RelPerson]->:RelKnows:->[?:RelPerson]];
        assert sorted([p.name for p in found2]) == ['deep'];
        assert be.rel_chain_count == 1;
        assert be.rel_hop_count >= hops_before + 2 , "per-hop path must dispatch per hop";
        ctx.close();
    } finally {
        if prior is None {
            os.environ.pop('JAC_TOPOLOGY_SQL_CHAIN', None);
        } else {
            os.environ['JAC_TOPOLOGY_SQL_CHAIN'] = prior;
        }
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
    be.close();
}


test "seam: chain + projection compose -- sliced chain still ONE SQL call" {
    # Coverage gap: chain pushdown (Route B feeder) and projection pushdown
    # were only ever exercised separately. A slice on a multi-hop path makes
    # resolve_chain_sql return an ordered list (not a set), which is exactly
    # what resolve_path_anchors' isinstance(result, list) arm requires to
    # route into _materialize_ids_projected (Route B) -- proving the two
    # pushdowns compose on the same round-trip instead of one silently
    # bypassing the other.
    be: any = _fresh();
    tmpdir = mkdtemp();
    orig_base = JacRuntime.get_base_path_dir();
    prior_proj: any = os.environ.pop('JAC_PROJECTION', None);
    prior_ro: any = os.environ.pop('JAC_READ_ONLY', None);
    try {
        cfg = JacConfig();
        cfg.run.topology_index = False;
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);
        mem: any = ctx.mem;
        mem.l3 = be;

        r = root;
        ps: list = [];
        for i in range(3) {
            p = RelPerson(name=f"p{i}");
            r +>:RelKnows:+> p;
            ps.append(p);
        }
        deep = RelPerson(name="deep");
        p0: any = ps[0];
        p0 +>:RelKnows:+> deep;

        r_any: any = r;
        ra: any = r_any.__jac__;
        cs: any = ChangeSet();
        cs.record_create(ra);
        for e in ra.edges {
            ea: any = e;
            cs.record_create(ea);
            cs.record_create(ea.target);
        }
        p0a: any = p0.__jac__;
        deep_e: any = p0a.edges[-1];
        cs.record_create(deep_e);
        cs.record_create(deep_e.target);
        rep: any = be.apply(cs);
        assert not rep.failed;

        os.environ['JAC_PROJECTION'] = 'RelPerson:name';
        os.environ['JAC_READ_ONLY'] = '1';

        found = [r->:RelKnows:->[?:RelPerson]->:RelKnows:->[?:RelPerson]][:1];
        names = sorted([p.name for p in found]);
        assert names == ['deep'];
        assert be.rel_chain_count == 1 , (
            "sliced two-hop + projection must remain ONE chain SQL call"
        );
        assert be.rel_projection_count > 0 , (
            "sliced chain result must route through projected materialization"
        );
        marks = [p.__jac__?._projected_fields for p in found];
        assert all(m == {"name"} for m in marks) , (
            f"chain-fed anchors must carry the projection marker: {marks}"
        );
        ctx.close();
    } finally {
        os.environ.pop('JAC_PROJECTION', None);
        os.environ.pop('JAC_READ_ONLY', None);
        if prior_proj is not None {
            os.environ['JAC_PROJECTION'] = prior_proj;
        }
        if prior_ro is not None {
            os.environ['JAC_READ_ONLY'] = prior_ro;
        }
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
    be.close();
}


# ===========================================================================
# caps phase
# ===========================================================================
test "caps: topology_sql advertised; JAC_TOPOLOGY_SQL=0 empties it" {
    be: any = _fresh();
    prior: any = os.environ.pop('JAC_TOPOLOGY_SQL', None);
    try {
        assert 'topology_sql' in be.capabilities();
        os.environ['JAC_TOPOLOGY_SQL'] = '0';
        assert be.capabilities() == set();
    } finally {
        if prior is None {
            os.environ.pop('JAC_TOPOLOGY_SQL', None);
        } else {
            os.environ['JAC_TOPOLOGY_SQL'] = prior;
        }
    }
    be.close();
}


# ---------------------------------------------------------------------------
# proj: projection pushdown (execute_plan + env-gated capabilities)
# ---------------------------------------------------------------------------
node RelProjP {
    has name: str = "",
        age: int = 0,
        tags: list[str] = [];
}


"""Seed one RelProjP under a fresh backend; returns (be, anchor)."""
def _seed_proj -> tuple {
    be: any = _fresh();
    r: any = _root_anchor();
    p: any = _node(RelProjP(name="ann", age=3, tags=["x", "y"]), r);
    cs: any = ChangeSet();
    cs.record_create(r);
    cs.record_create(p);
    rep: any = be.apply(cs);
    assert not rep.failed;
    return (be, p);
}


test "proj: capabilities gated on JAC_PROJECTION env" {
    be: any = _fresh();
    prior: any = os.environ.pop('JAC_PROJECTION', None);
    prior_topo: any = os.environ.pop('JAC_TOPOLOGY_SQL', None);
    try {
        assert be.capabilities() == {'topology_sql'};
        os.environ['JAC_PROJECTION'] = 'RelProjP:name';
        assert be.capabilities() == {
            'topology_sql',
            'id_in',
            'type_pushdown',
            'projection'
        };
        os.environ['JAC_TOPOLOGY_SQL'] = '0';
        assert be.capabilities() == {'id_in', 'type_pushdown', 'projection'} , (
            "kill switches stay independent: TOPOLOGY_SQL=0 must not disable projection caps"
        );
    } finally {
        os.environ.pop('JAC_PROJECTION', None);
        if prior is not None {
            os.environ['JAC_PROJECTION'] = prior;
        }
        if prior_topo is not None {
            os.environ['JAC_TOPOLOGY_SQL'] = prior_topo;
        }
    }
    be.close();
}


test "proj: execute_plan returns slim marked anchor with jsonb types" {
    (be, p) = _seed_proj();
    plan: any = QueryPlan(
        id_in={p.id}, node_type_final="RelProjP", projection={"name", "tags"}
    );
    res: any = list(be.execute_plan(plan));
    assert len(res) == 1;
    assert res[0].id == p.id;
    assert res[0]._projected_fields == {"name", "tags"};
    assert res[0].archetype.name == "ann";
    assert res[0].archetype.tags == ["x", "y"];
    assert res[0].archetype.age == 0;
    assert res[0].edges == [];
    assert be.rel_projection_count == 1;
    be.close();
}


test "proj: execute_plan arch_type filter excludes other types" {
    (be, p) = _seed_proj();
    plan: any = QueryPlan(
        id_in={p.id}, node_type_final="RelPerson", projection={"name"}
    );
    res: any = list(be.execute_plan(plan));
    assert res == [];
    be.close();
}


test "proj: execute_plan undeclared type full-hydrates (caps-leak guard)" {
    (be, p) = _seed_proj();
    plan: any = QueryPlan(id_in={p.id}, node_type_final="RelProjP");
    res: any = list(be.execute_plan(plan));
    assert len(res) == 1;
    assert res[0]?._projected_fields is None;
    assert res[0].archetype.age == 3;
    assert res[0].archetype.tags == ["x", "y"];
    assert be.rel_projection_count == 0;
    be.close();
}
