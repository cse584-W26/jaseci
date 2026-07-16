"""Conformance suite for PostgresBackend — the jac-scale L3 Postgres anchor store.

Mirrors SqliteMemory/MongoBackend semantics against a local Postgres
(DSN postgresql:///jactest). Each test builds its own fixtures on a truncated
store and closes every backend it opens (bounded pools would exhaust PG
connections otherwise). Raw psycopg connections are used for injection and
out-of-band verification; the backend's own pool is opaque.

Anchor handles (and backend handles) are typed `any`: the checker has no stub
for `.__jac__` / anchor metadata, and these tests poke the persistence layer
and pass duck-typed changesets directly.

Test names carry a phase prefix ("reads: …", "apply: …", "ops: …") so each
gate can run `-f "reads"` etc.
"""

import os;
import json;
import shutil;
import psycopg;
import from tempfile { mkdtemp }
import from uuid { UUID, uuid4 }
import from psycopg.types.json { Jsonb }

import from jaclang.jac0core.archetype { Root, GenericEdge, EdgeAnchor, NodeAnchor }
import from jaclang.jac0core.runtime { JacRuntime }
import from jaclang.runtimelib.context { ExecutionContext }
import from jaclang.runtimelib.changeset { ChangeSet, WriteOp, ApplyReport }
import from jaclang.runtimelib.exceptions { WriteConflict }
import from jaclang.runtimelib.serializer { Serializer }
import from jaclang.project.config { JacConfig, set_config }
import from jaclang.scale.memory.memory_hierarchy { PostgresBackend }

glob _DSN = os.environ.get('POSTGRESQL_URI', 'postgresql:///jactest'),
     # any-aliased callable: an any-typed constructor is unchecked, so the checker
     # does not enforce EdgeAnchor's typed params against our `any` anchor handles.
     _EDGE_ANCHOR: any = EdgeAnchor;


# The canonical custom archetype (Serializer auto-registers it).
node Counter {
    has count: int = 0,
        label: str = "";
}


# Graph archetypes for the GTI round-trip tests.
node Person {
    has name: str = "",
        age: int = 0;
}


edge Knows {}


# ---------------------------------------------------------------------------
# Transaction-level failure injection (copied verbatim from
# jac/tests/runtimelib/test_changeset.jac:187-210) — exercises apply()'s outer
# rollback path after the real stages have executed.
# ---------------------------------------------------------------------------
"""A stage whose iteration raises: simulates a transaction-level failure
(not a per-intent one) that strikes after the real stages have executed."""
obj _BoomStage {
    def __iter__ {
        raise RuntimeError("forced transaction-level failure");
    }
}


"""Changeset wrapper that appends a transaction-level failure after the
real stages, so apply()'s outer rollback path is exercised."""
obj _PoisonTailChangeSet {
    has inner: any;

    def is_empty -> bool {
        return bool(self.inner.is_empty());
    }

    def staged -> list {
        out: list = list(self.inner.staged());
        out.append(_BoomStage());
        return out;
    }
}


# ---------------------------------------------------------------------------
# Harness helpers
# ---------------------------------------------------------------------------
"""A raw autocommit psycopg connection for injection / verification."""
def _raw -> any {
    return psycopg.connect(_DSN, autocommit=True);
}


"""A fresh backend on a truncated store. First construction bootstraps the
schema; then TRUNCATE the working tables (leave schema_meta). Never assume a
clean DB."""
def _fresh -> PostgresBackend {
    be: PostgresBackend = PostgresBackend(dsn=_DSN, pool_min=1, pool_max=3);
    raw: any = _raw();
    raw.execute("TRUNCATE anchors, anchors_quarantine, aliases");
    raw.close();
    return be;
}


"""A second backend instance on the same store — a cold read (no __mem__
carry-over from the writer instance)."""
def _cold -> PostgresBackend {
    return PostgresBackend(dsn=_DSN, pool_min=1, pool_max=3);
}


"""A persistent Root anchor rooted at itself."""
def _root_anchor -> any {
    r: any = Root();
    a: any = r.__jac__;
    a.persistent = True;
    setattr(a, 'root', a.id);
    return a;
}


"""A persistent Counter anchor."""
def _counter(count: int, label: str) -> any {
    c: any = Counter(count=count, label=label);
    a: any = c.__jac__;
    a.persistent = True;
    return a;
}


"""A bare persistent edge anchor — id-only, for edge-list-delta tests (mirrors
test_occ_sqlite._edge). NOT a row-typed EdgeAnchor."""
def _edge -> any {
    edge_arch: any = GenericEdge();
    e: any = edge_arch.__jac__;
    e.persistent = True;
    return e;
}


"""A real EdgeAnchor source->target (rows as type=EdgeAnchor; mirrors
test_occ_replay:308-314)."""
def _mk_edge(source: any, target: any) -> any {
    edge_arch: any = GenericEdge();
    eanch: any = _EDGE_ANCHOR(
        archetype=edge_arch, source=source, target=target, is_undirected=False
    );
    edge_arch.__jac__ = eanch;
    eanch.persistent = True;
    setattr(eanch, 'root', source.id);
    return eanch;
}


"""Seed a fresh Root at version 0 via a create unit; return its anchor."""
def _seed_root(be: any) -> any {
    r: any = _root_anchor();
    cs: any = ChangeSet();
    cs.record_create(r);
    be.apply(cs);
    return r;
}


"""A valid serialized-anchor payload whose embedded archetype identity points
at a class that does not exist (`nowhere.Missing`). Valid JSONB, unresolvable
class — the PG analog of sqlite's malformed-text corruption (JSONB rejects
malformed text at INSERT, so we corrupt the class identity instead)."""
def _missing_class_payload -> any {
    c: any = Counter(count=1, label="doomed");
    a: any = c.__jac__;
    a.persistent = True;
    payload: any = Serializer.serialize(a, include_type=True);
    arch: any = payload.get('archetype');
    if isinstance(arch, dict) {
        arch['__type__'] = 'Missing';
        arch['__module__'] = 'nowhere';
    }
    return payload;
}


"""Raw-INSERT a row with VALID jsonb data but an unresolvable class
(arch_module='nowhere', arch_type='Missing'). get() must quarantine it
CLASS_MISSING, not crash."""
def _inject_missing_class(raw: any, aid: str) {
    raw.execute(
        """
        INSERT INTO anchors
            (id, type, arch_module, arch_type, fingerprint, data,
             format_version, updated_at)
        VALUES (%s, 'NodeAnchor', 'nowhere', 'Missing', 'deadbeef01234567',
                %s, 1, '2026-01-01T00:00:00')
        """,
        (aid, Jsonb(_missing_class_payload()))
    );
}


"""Rewrite a stored anchor's class name (column + embedded identity) to
`newname`, an unregistered class — so get() quarantines it and an alias can
later rescue it."""
def _rename_class(raw: any, aid: str, newname: str) {
    row: any = raw.execute("SELECT data FROM anchors WHERE id=%s", (aid, )).fetchone();
    payload: any = row[0];
    arch: any = payload.get('archetype');
    if isinstance(arch, dict) {
        arch['__type__'] = newname;
    }
    raw.execute(
        "UPDATE anchors SET arch_type=%s, data=%s WHERE id=%s",
        (newname, Jsonb(payload), aid)
    );
}


"""Raw-INSERT an EdgeAnchor row citing `source_id`/`target_id` (as plain id
strings, matching how apply persists endpoints)."""
def _insert_edge_row(raw: any, eid: str, source_id: str, target_id: str) {
    s: any = _root_anchor();
    t: any = _root_anchor();
    e: any = _mk_edge(s, t);
    payload: any = Serializer.serialize(e, include_type=True);
    payload['source'] = source_id;
    payload['target'] = target_id;
    payload['id'] = eid;
    raw.execute(
        """
        INSERT INTO anchors
            (id, type, arch_module, arch_type, fingerprint, data,
             format_version, updated_at)
        VALUES (%s, 'EdgeAnchor', %s, 'GenericEdge', 'fp', %s, 1,
                '2026-01-01T00:00:00')
        """,
        (eid, type(GenericEdge()).__module__, Jsonb(payload))
    );
}


"""Raw-INSERT a stranded child node that cites a half-linked edge `e2` (root
does NOT cite it): child->e2->root, root silent. Returns (child_id, e2)."""
def _add_half_linked(raw: any, r_id: any) -> tuple {
    c2: any = _counter(2, "stranded");
    e2: str = str(uuid4());
    payload: any = Serializer.serialize(c2, include_type=True);
    payload['edges'] = [e2];
    raw.execute(
        """
        INSERT INTO anchors
            (id, type, arch_module, arch_type, fingerprint, data,
             format_version, updated_at)
        VALUES (%s, 'NodeAnchor', %s, 'Counter', 'fp', %s, 1,
                '2026-01-01T00:00:00')
        """,
        (str(c2.id), type(Counter()).__module__, Jsonb(payload))
    );
    _insert_edge_row(raw, e2, str(r_id), str(c2.id));
    return (c2.id, e2);
}


"""Seed root -e-> child via one create unit; return (root_id, edge_id,
child_id)."""
def _seed_linked(be: any) -> tuple {
    seed: any = _seed_root(be);
    b0: any = _cold();
    r: any = b0.get(seed.id);
    child_arch: any = Counter(count=1, label="child");
    child: any = child_arch.__jac__;
    child.persistent = True;
    setattr(child, 'root', r.id);
    e: any = _mk_edge(r, child);
    r.edges.append(e);
    child.edges.append(e);
    cs: any = ChangeSet();
    cs.record_create(child);
    cs.record_create(e);
    cs.record_edge_delta(r, [e.id], []);
    b0.apply(cs);
    b0.close();
    return (r.id, e.id, child.id);
}


# ===========================================================================
# P2 GATE — reads / CRUD / batch_get
# ===========================================================================
test "reads: schema bootstrap and is_available" {
    be: any = _fresh();
    assert be.is_available() is True;
    raw: any = _raw();
    rows: any = raw.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public'"
    ).fetchall();
    tables: set = {r[0] for r in rows};
    assert 'anchors' in tables;
    assert 'anchors_quarantine' in tables;
    assert 'aliases' in tables;
    assert 'schema_meta' in tables;
    fmt: any = raw.execute(
        "SELECT value FROM schema_meta WHERE key='db_format_version'"
    ).fetchone();
    assert fmt[0] == '1';
    raw.close();
    # Constructing a second backend is idempotent (no error, no wipe).
    be2: any = _cold();
    assert be2.is_available() is True;
    be2.close();
    be.close();
}


test "reads: pool is process-cached per DSN; close drops only local ref" {
    a: any = _cold();
    b: any = _cold();
    # Same DSN + pool bounds -> the very same ConnectionPool object.
    assert a.__pool__ is b.__pool__;
    shared: any = a.__pool__;
    a.close();
    assert a.is_available() is False;
    # The shared pool survives a sibling's close and stays usable.
    assert b.is_available() is True;
    assert b.get(uuid4()) is None;
    # A later backend re-attaches to the same cached pool.
    c: any = _cold();
    assert c.__pool__ is shared;
    b.close();
    c.close();
}


test "reads: put/get round-trips a Root anchor" {
    be: any = _fresh();
    a: any = _root_anchor();
    rid: any = uuid4();
    setattr(a, 'root', rid);
    be.put(a);
    got: any = be.get(a.id);
    assert got is not None;
    assert got.id == a.id;
    assert isinstance(got.archetype, Root);
    assert got.root == rid;
    be.close();
}


test "reads: get of a missing id returns None" {
    be: any = _fresh();
    assert be.get(uuid4()) is None;
    be.close();
}


test "reads: custom archetype fields survive a cold round-trip as real jsonb" {
    be: any = _fresh();
    a: any = _counter(7, "widgets");
    be.put(a);
    be.close();
    cold: any = _cold();
    got: any = cold.get(a.id);
    assert got is not None;
    assert got.archetype.count == 7;
    assert got.archetype.label == "widgets";
    raw: any = _raw();
    typ: any = raw.execute(
        "SELECT jsonb_typeof(data) FROM anchors WHERE id=%s", (str(a.id), )
    ).fetchone();
    assert typ[0] == 'object' , f"data must be a jsonb object (double-encode trap), got {typ}";
    raw.close();
    cold.close();
}


test "reads: undeserializable row is quarantined on get, not crash" {
    be: any = _fresh();
    raw: any = _raw();
    bad_id: str = str(uuid4());
    _inject_missing_class(raw, bad_id);
    assert be.get(UUID(bad_id)) is None;
    live: any = raw.execute(
        "SELECT count(*) FROM anchors WHERE id=%s", (bad_id, )
    ).fetchone();
    assert live[0] == 0 , "bad row must leave the anchors table";
    q: any = raw.execute(
        "SELECT reason_code FROM anchors_quarantine WHERE id=%s", (bad_id, )
    ).fetchone();
    assert q is not None , "bad row must land in quarantine";
    assert q[0] == 'CLASS_MISSING' , f"expected reason_code CLASS_MISSING, got {q}";
    raw.close();
    be.close();
}


test "reads: field hashes are snapshotted on load" {
    be: any = _fresh();
    a: any = _counter(3, "hh");
    be.put(a);
    be.close();
    cold: any = _cold();
    got: any = cold.get(a.id);
    assert got is not None;
    hashes: any = got.archetype.__dict__.get('__jac_field_hashes__');
    assert isinstance(hashes, dict) , "__jac_field_hashes__ must be set after load";
    assert 'count' in hashes;
    assert 'label' in hashes;
    cold.close();
}


test "reads: has, and delete is cache-eviction only (row survives)" {
    be: any = _fresh();
    a: any = _root_anchor();
    assert not be.`has(a.id);
    be.put(a);
    assert be.`has(a.id);
    # delete() is a no-op cache eviction on L3 (mirrors Mongo/Sqlite); durable
    # removal happens ONLY via apply()'s delete intents / fsck. The committed
    # row MUST survive -- a durable delete here is the #6587 corruption window
    # and would let TieredMemory.abort wipe merely-mutated rows.
    be.delete(a.id);
    assert be.`has(a.id) , "delete() must not durably remove the row";
    assert be.get(a.id) is not None , "committed anchor survives cache-eviction delete";
    be.close();
}


test "reads: put skips a non-persistent anchor" {
    be: any = _fresh();
    r: any = Root();
    a: any = r.__jac__;
    a.persistent = False;
    be.put(a);
    assert not be.`has(a.id);
    be.close();
}


test "reads: put upserts on conflict" {
    be: any = _fresh();
    a: any = _counter(1, "first");
    be.put(a);
    a.archetype.count = 99;
    a.archetype.label = "second";
    be.put(a);
    be.close();
    cold: any = _cold();
    got: any = cold.get(a.id);
    assert got is not None;
    assert got.archetype.count == 99;
    assert got.archetype.label == "second";
    cold.close();
}


test "reads: get_roots yields only roots" {
    be: any = _fresh();
    r1: any = _root_anchor();
    r2: any = _root_anchor();
    c: any = _counter(1, "c");
    be.put(r1);
    be.put(r2);
    be.put(c);
    be.close();
    cold: any = _cold();
    got_ids: set = set();
    for rt in cold.get_roots() {
        h: any = rt;
        got_ids.add(h.__jac__.id);
    }
    assert got_ids == {r1.id, r2.id} , f"expected exactly the 2 roots, got {got_ids}";
    cold.close();
}


test "reads: find and find_one accept a single id and an iterable" {
    be: any = _fresh();
    a1: any = _counter(1, "a");
    a2: any = _counter(2, "b");
    be.put(a1);
    be.put(a2);
    single: list = list(be.find(a1.id));
    assert len(single) == 1;
    both: list = list(be.find([a1.id, a2.id]));
    assert len(both) == 2;
    one: any = be.find_one(a1.id);
    assert one is not None and one.id == a1.id;
    assert be.find_one(uuid4()) is None;
    filtered: list = list(
        be.find([a1.id, a2.id], lambda x: any : x.archetype.count == 2)
    );
    assert len(filtered) == 1 and filtered[0].id == a2.id;
    be.close();
}


test "reads: query with and without filter" {
    be: any = _fresh();
    be.put(_root_anchor());
    be.put(_counter(1, "a"));
    be.put(_counter(2, "b"));
    be.close();
    cold: any = _cold();
    all_rows: list = list(cold.query());
    assert len(all_rows) == 3;
    counters: list = list(cold.query(lambda a: any : isinstance(a.archetype, Counter)));
    assert len(counters) == 2;
    cold.close();
}


test "reads: batch_get returns hits and skips misses" {
    be: any = _fresh();
    a1: any = _counter(1, "a");
    a2: any = _counter(2, "b");
    a3: any = _counter(3, "c");
    be.put(a1);
    be.put(a2);
    be.put(a3);
    be.close();
    cold: any = _cold();
    bogus: any = uuid4();
    res: dict = dict(cold.batch_get([a1.id, a2.id, a3.id, bogus]));
    assert len(res) == 3;
    assert a1.id in res and a2.id in res and a3.id in res;
    assert bogus not in res;
    assert all(isinstance(k, UUID) for k in res.keys()) , "keys must be UUID objects";
    assert res[a1.id].archetype.count == 1;
    cold.close();
}


test "reads: batch_get with an empty list returns an empty dict" {
    be: any = _fresh();
    assert be.batch_get([]) == {};
    be.close();
}


test "reads: batch_get is one round-trip, not N" {
    be: any = _fresh();
    seeded: list = [];
    for i in range(5) {
        a: any = _counter(i, f"c{i}");
        be.put(a);
        seeded.append(a.id);
    }
    be.close();
    cold: any = _cold();
    assert cold.l3_fetch_count == 0;
    res: dict = dict(cold.batch_get(seeded));
    assert len(res) == 5;
    assert cold.l3_fetch_count == 1 , f"batch_get must be ONE round-trip, got {cold.l3_fetch_count}";
    cold.get(seeded[0]);
    assert cold.l3_fetch_count == 2 , "get() increments the fetch count by exactly 1";
    cold.close();
}


test "reads: every Memory read method returns its documented shape on an empty store" {
    be: any = _fresh();
    assert be.is_available() is True;
    assert be.get(uuid4()) is None;
    assert be.`has(uuid4()) is False;
    assert list(be.query()) == [];
    assert list(be.get_roots()) == [];
    assert list(be.find(uuid4())) == [];
    assert be.find_one(uuid4()) is None;
    empty: dict = dict(be.batch_get([uuid4()]));
    assert isinstance(empty, dict) and empty == {};
    assert isinstance(be.get_mem(), dict);
    assert be.commit(None) is None;
    be.close();
}


# ===========================================================================
# P3 GATE — apply + OCC
# ===========================================================================
test "apply: empty changeset is a no-op ok report" {
    be: any = _fresh();
    raw: any = _raw();
    n0: any = raw.execute("SELECT count(*) FROM anchors").fetchone();
    rep: any = be.apply(ChangeSet());
    assert rep.applied == [];
    assert rep.failed == {};
    assert rep.skipped == {};
    assert rep.conflicts == [];
    assert rep.ok() is True;
    n1: any = raw.execute("SELECT count(*) FROM anchors").fetchone();
    assert n0[0] == n1[0] , "empty apply must have no side effects";
    raw.close();
    be.close();
}


test "apply: a full create unit lands atomically" {
    be: any = _fresh();
    seed: any = _seed_root(be);
    b0: any = _cold();
    r: any = b0.get(seed.id);
    child_arch: any = Counter(count=8, label="child");
    child: any = child_arch.__jac__;
    child.persistent = True;
    setattr(child, 'root', r.id);
    e: any = _mk_edge(r, child);
    r.edges.append(e);
    child.edges.append(e);
    cs: any = ChangeSet();
    cs.record_create(child);
    cs.record_create(e);
    cs.record_edge_delta(r, [e.id], []);
    rep: any = b0.apply(cs);
    assert rep.ok();
    assert child.id in list(rep.applied);
    assert e.id in list(rep.applied);
    assert r.id in list(rep.applied);
    b0.close();
    cold: any = _cold();
    gc: any = cold.get(child.id);
    assert gc is not None and gc.archetype.count == 8;
    assert cold.get(e.id) is not None;
    gr: any = cold.get(r.id);
    assert e.id in [ed.id for ed in gr.edges];
    cold.close();
    be.close();
}


test "apply: FIELD_UPDATE merges only dirty fields" {
    be: any = _fresh();
    seed: any = _counter(1, "a");
    cs0: any = ChangeSet();
    cs0.record_create(seed);
    be.apply(cs0);
    be.close();
    bx: any = _cold();
    hx: any = bx.get(seed.id);
    hx.archetype.label = "x";
    by: any = _cold();
    hy: any = by .get(seed.id);
    hy.archetype.count = 99;
    csy: any = ChangeSet();
    csy.record_update(hy, {"count"});
    by .apply(csy);
    csx: any = ChangeSet();
    csx.record_update(hx, {"label"});
    bx.apply(csx);
    bx.close();
    by .close();
    cold: any = _cold();
    g: any = cold.get(seed.id);
    assert g.archetype.count == 99 , "Y's count must survive";
    assert g.archetype.label == "x" , "X must merge only its dirty field, not clobber count";
    cold.close();
    be.close();
}


test "apply: a delete unit removes rows and repairs the edge list" {
    be: any = _fresh();
    (r_id, e_id, c_id) = _seed_linked(be);
    b1: any = _cold();
    e2: any = b1.get(e_id);
    child2: any = b1.get(c_id);
    cs: any = ChangeSet();
    cs.record_delete(e2);
    cs.record_delete(child2);
    rep: any = b1.apply(cs);
    assert rep.ok();
    b1.close();
    cold: any = _cold();
    assert cold.get(c_id) is None;
    assert cold.get(e_id) is None;
    gr: any = cold.get(r_id);
    assert gr is not None;
    assert e_id not in [ed.id for ed in gr.edges];
    cold.close();
    be.close();
}


test "apply: concurrent blind edge appends both survive (merge vs DB-current)" {
    be: any = _fresh();
    seed: any = _seed_root(be);
    be.close();
    b1: any = _cold();
    b2: any = _cold();
    h1: any = b1.get(seed.id);
    h2: any = b2.get(seed.id);
    assert len(list(h1.edges)) == 0 and len(list(h2.edges)) == 0;
    e1: any = _edge();
    e2: any = _edge();
    h1.edges.append(e1);
    cs1: any = ChangeSet();
    cs1.record_edge_delta(h1, [e1.id], []);
    h2.edges.append(e2);
    cs2: any = ChangeSet();
    cs2.record_edge_delta(h2, [e2.id], []);
    r1: any = b1.apply(cs1);
    r2: any = b2.apply(cs2);
    assert not r1.conflicts and not r2.conflicts , "blind appends must not conflict";
    b1.close();
    b2.close();
    cold: any = _cold();
    g: any = cold.get(seed.id);
    assert len(list(g.edges)) == 2 , f"both blind appends must merge, got {len(
        list(g.edges)
    )}";
    assert g.version == 2 , f"blind appends advance version from stored, got {g.version}";
    cold.close();
}


test "apply: OCC stale CAS conflicts and rolls back the whole unit" {
    be: any = _fresh();
    seed: any = _seed_root(be);
    be.close();
    bw: any = _cold();
    rw: any = bw.get(seed.id);
    ew: any = _edge();
    rw.edges.append(ew);
    csw: any = ChangeSet();
    csw.record_edge_delta(rw, [ew.id], []);
    csw.intents[rw.id].cas_version = rw.version;
    repw: any = bw.apply(csw);
    assert not repw.conflicts;
    bl: any = _cold();
    rl: any = bl.get(seed.id);
    rl.version = 0;
    child_arch: any = Counter(count=1, label="loser");
    child: any = child_arch.__jac__;
    child.persistent = True;
    setattr(child, 'root', rl.id);
    el: any = _mk_edge(rl, child);
    rl.edges.append(el);
    child.edges.append(el);
    csl: any = ChangeSet();
    csl.record_create(child);
    csl.record_create(el);
    csl.record_edge_delta(rl, [el.id], []);
    csl.intents[rl.id].cas_version = 0;
    repl: any = bl.apply(csl);
    assert len(list(repl.conflicts)) == 1;
    assert repl.conflicts[0].expected_version == 0;
    assert repl.conflicts[0].actual_version == 1;
    assert repl.applied == [] , "rollback clears applied";
    bw.close();
    bl.close();
    cold: any = _cold();
    assert cold.get(child.id) is None , "loser child rolled back (no orphan)";
    assert cold.get(el.id) is None , "loser edge rolled back (no orphan)";
    gr: any = cold.get(seed.id);
    ids: list = [ed.id for ed in gr.edges];
    assert ew.id in ids and el.id not in ids;
    cold.close();
}


test "apply: read-gated first write to a never-persisted anchor inserts, not conflicts" {
    be: any = _fresh();
    r_arch: any = Root();
    ra: any = r_arch.__jac__;
    ra.persistent = True;
    setattr(ra, 'root', ra.id);
    e: any = _edge();
    ra.edges.append(e);
    cs: any = ChangeSet();
    cs.record_create(ra);
    cs.record_edge_delta(ra, [e.id], []);
    cs.intents[ra.id].cas_version = 0;
    rep: any = be.apply(cs);
    assert len(list(rep.conflicts)) == 0 , f"first write to an absent row must not conflict, got {rep.conflicts}";
    be.close();
    cold: any = _cold();
    g: any = cold.get(ra.id);
    assert g is not None;
    assert e.id in [ed.id for ed in g.edges];
    cold.close();
}


test "apply: depends_on skip-cascade through a conflicted repair" {
    be: any = _fresh();
    (r_id, e_id, c_id) = _seed_linked(be);
    bl: any = _cold();
    rl: any = bl.get(r_id);
    e1l: any = bl.get(e_id);
    childl: any = bl.get(c_id);
    # Winner bumps root to v1 (read-gated edge add).
    bw: any = _cold();
    rw: any = bw.get(r_id);
    ew: any = _edge();
    rw.edges.append(ew);
    csw: any = ChangeSet();
    csw.record_edge_delta(rw, [ew.id], []);
    csw.intents[rw.id].cas_version = rw.version;
    bw.apply(csw);
    # Loser's stale DELETE unit: root repair conflicts -> e1 skipped -> child skipped.
    rl.version = 0;
    csd: any = ChangeSet();
    csd.record_delete(e1l);
    csd.record_delete(childl);
    csd.intents[rl.id].cas_version = 0;
    repl: any = bl.apply(csd);
    assert len(list(repl.conflicts)) == 1;
    assert e_id in repl.skipped;
    assert c_id in repl.skipped;
    assert "dependency" in str(repl.skipped[e_id]);
    assert "dependency" in str(repl.skipped[c_id]);
    bw.close();
    bl.close();
    cold: any = _cold();
    assert cold.get(e_id) is not None , "whole-txn rollback keeps e1";
    assert cold.get(c_id) is not None , "whole-txn rollback keeps child";
    gr: any = cold.get(r_id);
    assert e_id in [ed.id for ed in gr.edges];
    cold.close();
}


test "apply: apply-time quarantine rides the transaction" {
    be: any = _fresh();
    c: any = _counter(5, "orig");
    be.put(c);
    raw: any = _raw();
    _rename_class(raw, str(c.id), 'Missing');
    raw.execute("UPDATE anchors SET arch_module='nowhere' WHERE id=%s", (str(c.id), ));
    corrupt: any = raw.execute(
        "SELECT data::text FROM anchors WHERE id=%s", (str(c.id), )
    ).fetchone();
    ghost: any = _counter(1, "ghost");
    cs: any = ChangeSet();
    cs.record_create(ghost);
    c.archetype.label = "renamed";
    cs.record_update(c, {"label"});
    poison: any = _PoisonTailChangeSet(inner=cs);
    try {
        be.apply(poison);
    } except Exception { }
    qn: any = raw.execute("SELECT count(*) FROM anchors_quarantine").fetchone();
    assert qn[0] == 0 , "in-txn quarantine must roll back with the failed unit";
    gh: any = raw.execute(
        "SELECT count(*) FROM anchors WHERE id=%s", (str(ghost.id), )
    ).fetchone();
    assert gh[0] == 0 , "rolled-back create must not persist";
    after: any = raw.execute(
        "SELECT data::text FROM anchors WHERE id=%s", (str(c.id), )
    ).fetchone();
    assert after is not None and after[0] == corrupt[0] , "corrupt row must be byte-identical after rollback";
    raw.close();
    be.close();
}


test "apply: a mid-unit SQL abort fails loud -- no silent partial commit" {
    # A BEFORE INSERT trigger that raises once the table already holds a row
    # (visible in-txn) forces the SECOND create of a 2-create unit to abort the
    # psycopg transaction mid-flight. psycopg's commit() on an aborted txn does
    # NOT raise (PG converts COMMIT->ROLLBACK), so without the INERROR guard
    # apply() would report the first create as applied while 0 rows persist --
    # silent data loss. Assert the report is truthful and nothing persisted.
    be: any = _fresh();
    raw: any = _raw();
    raw.execute(
        "CREATE OR REPLACE FUNCTION _pg_abort_second() RETURNS trigger AS $$ "
        "BEGIN IF (SELECT count(*) FROM anchors) >= 1 THEN "
        "RAISE EXCEPTION 'forced mid-unit abort'; END IF; RETURN NEW; END; $$ "
        "LANGUAGE plpgsql"
    );
    raw.execute("DROP TRIGGER IF EXISTS _pg_abort_second_trg ON anchors");
    raw.execute(
        "CREATE TRIGGER _pg_abort_second_trg BEFORE INSERT ON anchors "
        "FOR EACH ROW EXECUTE FUNCTION _pg_abort_second()"
    );
    a: any = _counter(1, "first");
    b: any = _counter(2, "second");
    cs: any = ChangeSet();
    cs.record_create(a);
    cs.record_create(b);
    try {
        rep: any = be.apply(cs);
        assert rep.applied == [] , f"aborted unit must apply nothing, got {rep.applied}";
        failed_ids: list = list(rep.failed.keys());
        assert a.id in failed_ids , "the pre-error create must be reported failed, not lost";
        assert b.id in failed_ids , "the aborting create must be reported failed";
        folded: list = [
            m
            for m in rep.failed.values()
            if "aborted by earlier failure" in str(m)
        ];
        assert len(folded) == 1 , f"exactly the pre-error create must be folded into failed, got {rep.failed}";
        assert rep.ok() is False;
        na: any = raw.execute(
            "SELECT count(*) FROM anchors WHERE id=%s", (str(a.id), )
        ).fetchone();
        assert na[0] == 0 , "the pre-error row must be absent (COMMIT became ROLLBACK)";
        nb: any = raw.execute(
            "SELECT count(*) FROM anchors WHERE id=%s", (str(b.id), )
        ).fetchone();
        assert nb[0] == 0 , "the aborting row must be absent";
    } finally {
        raw.execute("DROP TRIGGER IF EXISTS _pg_abort_second_trg ON anchors");
        raw.execute("DROP FUNCTION IF EXISTS _pg_abort_second()");
        raw.close();
        be.close();
    }
}


test "apply: GTI blob survives create and is traversal-usable cold" {
    pg: any = _fresh();
    tmpdir = mkdtemp();
    orig_base = JacRuntime.get_base_path_dir();
    root_id: any = None;
    topo_before: any = None;
    idx_len: int = 0;
    try {
        cfg = JacConfig();
        cfg.run.topology_index = True;
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);

        r = root;
        for i in range(3) {
            r +>:Knows:+> Person(name=f"p{i}", age=20 + i);
        }
        r_any: any = r;
        ra: any = r_any.__jac__;
        idx_before: any = ra.get_topology_index();
        assert len(list(idx_before.node_table)) >= 3 , "root must carry a topology index";
        root_id = ra.id;
        topo_before = ra.topology_index_data;
        idx_len = len(list(idx_before.node_table));
        assert topo_before is not None;

        cs: any = ChangeSet();
        cs.record_create(ra);
        for e in ra.edges {
            ea: any = e;
            cs.record_create(ea);
            cs.record_create(ea.target);
        }
        rep: any = pg.apply(cs);
        assert rep.ok();
        ctx.close();
    } finally {
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
    cold: any = _cold();
    restored: any = cold.get(root_id);
    assert restored is not None;
    assert restored.topology_index_data == topo_before , "GTI blob must survive the round-trip";
    assert len(list(restored.get_topology_index().node_table)) == idx_len;
    cold.close();
    pg.close();
}


test "apply: GTI topology-only update persists through the merge path" {
    pg: any = _fresh();
    tmpdir = mkdtemp();
    orig_base = JacRuntime.get_base_path_dir();
    root_id: any = None;
    blob_old: any = None;
    blob_new: any = None;
    try {
        cfg = JacConfig();
        cfg.run.topology_index = True;
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);

        r = root;
        p0 = Person(name="p0", age=20);
        r +>:Knows:+> p0;
        for i in range(1, 3) {
            r +>:Knows:+> Person(name=f"p{i}", age=20 + i);
        }
        r_any: any = r;
        ra: any = r_any.__jac__;
        root_id = ra.id;
        cs0: any = ChangeSet();
        cs0.record_create(ra);
        for e in ra.edges {
            ea: any = e;
            cs0.record_create(ea);
            cs0.record_create(ea.target);
        }
        pg.apply(cs0);
        blob_old = ra.topology_index_data;
        edges_before: list = [ed.id for ed in ra.edges];

        # A deep edge (p0 -> Person) updates root's topology_index_data WITHOUT
        # touching root's own edges or fields.
        p0 +>:Knows:+> Person(name="deep", age=99);
        blob_new = ra.topology_index_data;
        edges_after: list = [ed.id for ed in ra.edges];
        assert blob_new != blob_old , "deep edge must update root topology_index_data";
        assert edges_after == edges_before , "deep edge must not change root's own edge list";

        p0_any: any = p0;
        p0a: any = p0_any.__jac__;
        deep_e: any = p0a.edges[-1];
        deep_person: any = deep_e.target;
        cs1: any = ChangeSet();
        cs1.record_create(deep_person);
        cs1.record_create(deep_e);
        # An empty edge-delta forces an EDGE_LIST_DELTA intent whose merge path
        # reaches the unconditional topology_index_data comparison.
        cs1.record_edge_delta(ra, [], []);
        pg.apply(cs1);
        ctx.close();
    } finally {
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
    cold: any = _cold();
    restored: any = cold.get(root_id);
    assert restored is not None;
    assert restored.topology_index_data == blob_new , "merge must persist the updated GTI blob";
    assert restored.topology_index_data != blob_old;
    cold.close();
    pg.close();
}


# ===========================================================================
# P4 GATE — operator surface
# ===========================================================================
test "ops: inspect_summary shape and counts" {
    be: any = _fresh();
    be.put(_counter(1, "a"));
    be.put(_counter(2, "b"));
    be.put(_root_anchor());
    raw: any = _raw();
    bad: str = str(uuid4());
    _inject_missing_class(raw, bad);
    be.get(UUID(bad));  # move the bad row into quarantine
    try {
        be.add_alias("OldC", "Counter");
        d: dict = dict(be.inspect_summary());
        assert set(d.keys()) == {
            'format_version',
            'anchors_total',
            'anchors_by_type',
            'quarantine_total',
            'quarantine_by_type',
            'aliases_total',
            'location'
        };
        assert d['format_version'] == '1';
        assert d['anchors_total'] == 3;
        assert ('Counter', 2) in d['anchors_by_type'];
        assert d['quarantine_total'] == 1;
        assert d['aliases_total'] == 1;
        assert 'jactest' in d['location'];
    } finally {
        Serializer._aliases.pop('OldC', None);
    }
    raw.close();
    be.close();
}


test "ops: list_quarantined is newest-first with documented keys and limit" {
    be: any = _fresh();
    raw: any = _raw();
    b1: str = str(uuid4());
    _inject_missing_class(raw, b1);
    be.get(UUID(b1));
    b2: str = str(uuid4());
    _inject_missing_class(raw, b2);
    be.get(UUID(b2));
    lst: list = list(be.list_quarantined());
    assert len(lst) == 2;
    for entry in lst {
        assert set(entry.keys()) == {
            'id',
            'arch',
            'fingerprint',
            'error',
            'quarantined_at'
        };
        for v in entry.values() {
            assert isinstance(v, str);
        }
    }
    one: list = list(be.list_quarantined(limit=1));
    assert len(one) == 1;
    assert one[0]['id'] == b2 , "newest-first";
    raw.close();
    be.close();
}


test "ops: show_quarantined exact id / unique prefix / ambiguous / miss" {
    be: any = _fresh();
    raw: any = _raw();
    id1: str = 'aaaaaaaa-0000-0000-0000-000000000001';
    id2: str = 'aaaaaaaa-0000-0000-0000-000000000002';
    _inject_missing_class(raw, id1);
    _inject_missing_class(raw, id2);
    be.get(UUID(id1));
    be.get(UUID(id2));
    full: any = be.show_quarantined(id1);
    assert full is not None;
    assert set(full.keys()) == {
        'id',
        'type',
        'arch_module',
        'arch_type',
        'fingerprint',
        'error',
        'quarantined_at',
        'from_format_version',
        'data'
    };
    assert isinstance(full['data'], dict) , "data must be parsed";
    uniq: any = be.show_quarantined('aaaaaaaa-0000-0000-0000-000000000001');
    assert uniq is not None and uniq['id'] == id1;
    amb: any = be.show_quarantined('aaaaaaaa');
    assert amb is not None
    and amb.get('error') == 'ambiguous'
    and amb.get('count') == 2;
    assert be.show_quarantined('ffffffff') is None;
    raw.close();
    be.close();
}


test "ops: alias CRUD round-trip" {
    be: any = _fresh();
    try {
        assert be.list_aliases() == [];
        be.add_alias('OldName', 'Counter');
        be.add_alias('OldName', 'Counter');
        al: list = list(be.list_aliases());
        assert len(al) == 1;
        assert set(al[0].keys()) == {'old_name', 'new_name', 'created_at'};
        be.add_alias('OldName', 'Other');
        al2: list = list(be.list_aliases());
        assert len(al2) == 1 and al2[0]['new_name'] == 'Other';
        assert be.remove_alias('OldName') is True;
        assert be.remove_alias('OldName') is False;
        assert be.list_aliases() == [];
    } finally {
        Serializer._aliases.pop('OldName', None);
    }
    be.close();
}


test "ops: recover_one rescues a class-renamed row after alias add" {
    be: any = _fresh();
    raw: any = _raw();
    c: any = _counter(5, "keep");
    be.put(c);
    _rename_class(raw, str(c.id), 'LegacyCounter');
    assert be.get(c.id) is None;
    qc: any = raw.execute(
        "SELECT reason_code FROM anchors_quarantine WHERE id=%s", (str(c.id), )
    ).fetchone();
    assert qc is not None and qc[0] == 'CLASS_MISSING';
    # The Serializer registry/alias map is keyed by fully-qualified module.class
    # (serializer.impl.jac:326,545), so the rescue alias must be too — mirrors
    # test_mongo_layer123.jac:291.
    mod: str = type(Counter()).__module__;
    old_key: str = f"{mod}.LegacyCounter";
    try {
        res0: any = be.recover_one(str(c.id));
        ok0: any = res0[0];
        assert ok0 is False;
        be.add_alias(old_key, f"{mod}.Counter");
        res1: any = be.recover_one(str(c.id));
        ok1: any = res1[0];
        reason1: any = res1[1];
        assert ok1 is True and reason1 == 'recovered';
        qn: any = raw.execute(
            "SELECT count(*) FROM anchors_quarantine WHERE id=%s", (str(c.id), )
        ).fetchone();
        assert qn[0] == 0;
        cold: any = _cold();
        g: any = cold.get(c.id);
        assert g is not None and g.archetype.count == 5;
        cold.close();
    } finally {
        Serializer._aliases.pop(old_key, None);
    }
    raw.close();
    be.close();
}


test "ops: recover_all returns (n_recovered, still_stuck)" {
    be: any = _fresh();
    raw: any = _raw();
    good: any = _counter(1, "good");
    be.put(good);
    _rename_class(raw, str(good.id), 'LegacyCounter2');
    be.get(good.id);
    bad: str = str(uuid4());
    _inject_missing_class(raw, bad);
    be.get(UUID(bad));
    # Alias keyed by fully-qualified module.class (see recover_one test).
    mod: str = type(Counter()).__module__;
    old_key: str = f"{mod}.LegacyCounter2";
    try {
        be.add_alias(old_key, f"{mod}.Counter");
        r: any = be.recover_all();
        assert isinstance(r, tuple);
        assert r[0] == 1;
        stuck: list = list(r[1]);
        assert len(stuck) == 1;
        assert stuck[0][0] == bad;
        q: any = raw.execute(
            "SELECT count(*) FROM anchors_quarantine WHERE id=%s", (bad, )
        ).fetchone();
        assert q[0] == 1 , "hopeless row stays quarantined";
    } finally {
        Serializer._aliases.pop(old_key, None);
    }
    raw.close();
    be.close();
}


test "ops: DANGLING_REF is filed and excluded from is_recoverable_quarantine" {
    be: any = _fresh();
    raw: any = _raw();
    missing: any = uuid4();
    referrer: any = uuid4();
    be.quarantine_dangling(missing, referrer, 'edge');
    be.quarantine_dangling(missing, referrer, 'edge');
    rows: any = raw.execute(
        "SELECT reason_code FROM anchors_quarantine WHERE id=%s", (str(missing), )
    ).fetchall();
    assert len(list(rows)) == 1 , "idempotent — never raises, one row";
    assert rows[0][0] == 'DANGLING_REF';
    lst: list = list(be.list_quarantined());
    assert any(entry['id'] == str(missing) for entry in lst);
    assert be.is_recoverable_quarantine(missing) is False;
    bad: str = str(uuid4());
    _inject_missing_class(raw, bad);
    be.get(UUID(bad));
    assert be.is_recoverable_quarantine(UUID(bad)) is True;
    assert be.is_recoverable_quarantine(uuid4()) is False;
    raw.close();
    be.close();
}


test "ops: fsck read-only classifies every violation kind and mutates nothing" {
    be: any = _fresh();
    (r_id, e_id, c_id) = _seed_linked(be);
    raw: any = _raw();
    rs: str = str(r_id);
    # (a) dangling_node_edge: root cites a bogus edge id.
    bogus_e: str = str(uuid4());
    raw.execute(
        "UPDATE anchors SET data = jsonb_set(data, '{edges}', "
        "(data->'edges') || %s::jsonb) WHERE id=%s",
        (json.dumps([bogus_e]), rs)
    );
    # (b) dangling_edge_node: an edge row citing a missing node.
    de_edge: str = str(uuid4());
    _insert_edge_row(raw, de_edge, str(c_id), str(uuid4()));
    # (c) orphan_edges: an edge nobody cites.
    orphan_e: str = str(uuid4());
    _insert_edge_row(raw, orphan_e, str(r_id), str(c_id));
    # (d) half_linked_edges + orphan_nodes: a stranded child citing an edge the root rejects.
    (c2, e2) = _add_half_linked(raw, r_id);
    n_before: any = raw.execute("SELECT count(*) FROM anchors").fetchone();
    q_before: any = raw.execute("SELECT count(*) FROM anchors_quarantine").fetchone();
    rep: dict = dict(be.fsck(False));
    assert set(rep.keys()) == {
        'location',
        'dangling_node_edge',
        'dangling_edge_node',
        'orphan_edges',
        'orphan_nodes',
        'half_linked_edges',
        'repaired',
        'repaired_counts'
    };
    assert any(pair[1] == bogus_e for pair in rep['dangling_node_edge']);
    assert any(pair[0] == de_edge for pair in rep['dangling_edge_node']);
    assert orphan_e in rep['orphan_edges'];
    assert any(t[0] == e2 for t in rep['half_linked_edges']);
    assert str(c2) in [str(n) for n in rep['orphan_nodes']];
    assert rep['repaired'] is False;
    assert rep['repaired_counts']['pruned'] == 0;
    assert rep['repaired_counts']['quarantined'] == 0;
    assert rep['repaired_counts']['collected'] == 0;
    n_after: any = raw.execute("SELECT count(*) FROM anchors").fetchone();
    q_after: any = raw.execute("SELECT count(*) FROM anchors_quarantine").fetchone();
    assert n_before[0] == n_after[0] , "read-only fsck must not mutate anchors";
    assert q_before[0] == q_after[0] , "read-only fsck must not mutate quarantine";
    raw.close();
    be.close();
}


test "ops: fsck repair heals and a second pass is clean" {
    be: any = _fresh();
    (r_id, e_id, c_id) = _seed_linked(be);
    raw: any = _raw();
    rs: str = str(r_id);
    bogus_e: str = str(uuid4());
    raw.execute(
        "UPDATE anchors SET data = jsonb_set(data, '{edges}', "
        "(data->'edges') || %s::jsonb) WHERE id=%s",
        (json.dumps([bogus_e]), rs)
    );
    de_edge: str = str(uuid4());
    _insert_edge_row(raw, de_edge, str(c_id), str(uuid4()));
    orphan_e: str = str(uuid4());
    _insert_edge_row(raw, orphan_e, str(r_id), str(c_id));
    (c2, e2) = _add_half_linked(raw, r_id);
    rep: dict = dict(be.fsck(True));
    assert rep['repaired'] is True;
    assert rep['repaired_counts']['pruned'] > 0;
    assert rep['repaired_counts']['quarantined'] > 0;
    assert rep['repaired_counts']['collected'] >= 3;
    assert be.get(c_id) is not None , "healthy child untouched";
    assert be.get(e_id) is not None , "healthy edge untouched";
    clean: dict = dict(be.fsck(False));
    assert clean['dangling_node_edge'] == [];
    assert clean['dangling_edge_node'] == [];
    assert clean['orphan_edges'] == [];
    assert clean['orphan_nodes'] == [];
    assert clean['half_linked_edges'] == [];
    raw.close();
    be.close();
}


test "ops: fsck repair preserves a live row cited as a dangling edge" {
    # Regression: fsck classifies a cited id that is a LIVE NodeAnchor (not an
    # EdgeAnchor) as dangling_node_edge. Repair must quarantine the citation
    # WITHOUT deleting the live row — SqliteMemory._record_dangling is
    # insert-only. (Old bug: _pg_record_dangling reused _pg_quarantine's
    # unconditional DELETE FROM anchors, destroying the live child.)
    be: any = _fresh();
    (r_id, e_id, c_id) = _seed_linked(be);
    raw: any = _raw();
    # Root's edges array now also cites c_id (a live NODE, not an edge row).
    raw.execute(
        "UPDATE anchors SET data = jsonb_set(data, '{edges}', "
        "(data->'edges') || %s::jsonb) WHERE id=%s",
        (json.dumps([str(c_id)]), str(r_id))
    );
    rep: dict = dict(be.fsck(True));
    assert any(pair[1] == str(c_id) for pair in rep['dangling_node_edge']);
    live: any = raw.execute(
        "SELECT count(*) FROM anchors WHERE id=%s", (str(c_id), )
    ).fetchone();
    assert live[0] == 1 , "repair must NOT delete the live cited row";
    assert be.get(c_id) is not None , "live child still readable after repair";
    raw.close();
    be.close();
}


test "ops: full operator surface returns documented shapes on an empty store" {
    be: any = _fresh();
    rep: any = be.apply(ChangeSet());
    assert isinstance(rep, ApplyReport);
    d: dict = dict(be.inspect_summary());
    assert isinstance(d, dict);
    assert set(d.keys()) == {
        'format_version',
        'anchors_total',
        'anchors_by_type',
        'quarantine_total',
        'quarantine_by_type',
        'aliases_total',
        'location'
    };
    assert d['anchors_total'] == 0;
    assert d['quarantine_total'] == 0;
    assert d['aliases_total'] == 0;
    assert be.list_quarantined() == [];
    assert be.show_quarantined('deadbeef') is None;
    ro: any = be.recover_one('deadbeef');
    assert isinstance(ro, tuple) and len(ro) == 2;
    assert ro[0] is False and isinstance(ro[1], str);
    assert be.recover_all() == (0, []);
    assert be.list_aliases() == [];
    try {
        assert be.add_alias('x', 'Counter') is None;
    } finally {
        Serializer._aliases.pop('x', None);
    }
    assert be.remove_alias('nope') is False;
    assert be.quarantine_dangling(uuid4(), None, 'node') is None;
    assert be.is_recoverable_quarantine(uuid4()) is False;
    f: dict = dict(be.fsck());
    assert isinstance(f, dict);
    assert set(f.keys()) == {
        'location',
        'dangling_node_edge',
        'dangling_edge_node',
        'orphan_edges',
        'orphan_nodes',
        'half_linked_edges',
        'repaired',
        'repaired_counts'
    };
    assert f['dangling_node_edge'] == [];
    be.close();
}


# ===========================================================================
# P5 GATE — projection no-op safety (coverage gap: KV never advertises
# 'projection', so JAC_PROJECTION must be inert here by construction)
# ===========================================================================
test "proj: KV backend never advertises the projection capability" {
    be: any = _fresh();
    prior: any = os.environ.pop('JAC_PROJECTION', None);
    try {
        assert be.capabilities() == set();
        os.environ['JAC_PROJECTION'] = 'Person:name';
        assert be.capabilities() == set() , (
            "KV inherits the base Memory.capabilities() no-op (memory.impl.jac"
            ":47-49) -- it must stay empty even with JAC_PROJECTION declared"
        );
    } finally {
        os.environ.pop('JAC_PROJECTION', None);
        if prior is not None {
            os.environ['JAC_PROJECTION'] = prior;
        }
    }
    be.close();
}


test "proj: JAC_PROJECTION + JAC_READ_ONLY on KV is a no-op -- full anchors, nothing raises" {
    be: any = _fresh();
    tmpdir = mkdtemp();
    orig_base = JacRuntime.get_base_path_dir();
    prior_proj: any = os.environ.pop('JAC_PROJECTION', None);
    prior_ro: any = os.environ.pop('JAC_READ_ONLY', None);
    try {
        os.environ['JAC_PROJECTION'] = 'Person:name';
        os.environ['JAC_READ_ONLY'] = '1';

        set_config(JacConfig());
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);
        mem: any = ctx.mem;
        mem.l3 = be;

        r = root;
        for i in range(3) {
            r +>:Knows:+> Person(name=f"p{i}", age=i);
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
        assert not rep.failed;

        found = [r->:Knows:->[?:Person]];
        assert len(found) == 3;
        names = sorted([p.name for p in found]);
        assert names == ['p0', 'p1', 'p2'];
        ages = sorted([p.age for p in found]);
        assert ages == [0, 1, 2] , (
            "KV no-op must return FULL anchors -- real field values, not "
            "leaked defaults from a phantom projection"
        );
        assert all(p.__jac__?._projected_fields is None for p in found) , (
            "no anchor may carry a projection marker -- KV never engages the "
            "pushdown, declared or not"
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
