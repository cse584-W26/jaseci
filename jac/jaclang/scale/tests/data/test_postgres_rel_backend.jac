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
import psycopg;
import from uuid { UUID, uuid4 }
import from psycopg.types.json { Jsonb }

import from jaclang.jac0core.archetype { Root, GenericEdge, EdgeAnchor, NodeAnchor }
import from jaclang.runtimelib.changeset { ChangeSet, WriteOp, ApplyReport }
import from jaclang.runtimelib.serializer { Serializer }
import from jaclang.scale.memory.memory_hierarchy { PostgresRelBackend }

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
    assert rows[0][1] == str(a.id);
    assert rows[0][2] == str(b.id);
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


test "hop: empty frontier and unknown type return empty not None" {
    be: any = _fresh();
    g: any = _seed_graph(be);
    assert be.resolve_hop_sql(set(), 'RelKnows', None, 2, None) == set();
    assert be.resolve_hop_sql(set(), 'RelKnows', None, 2, slice(None, None)) == [];
    assert be.resolve_hop_sql({g['a'].id}, 'NoSuchEdge', None, 2, None) == set();
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
