"""Resolver seam tests for projection pushdown Routes A and B (spec Decision 4).

Route A: set-path final-hop tail attaches plan.projection when declared +
read-only + backend advertises 'projection' + no post filter -> slim marked
anchors via execute_plan.
Route B: ordered/sliced list path routes through projected materialization
on topology_sql backends, preserving hop order.

Requires local Postgres (jactest_rel), same as test_postgres_rel_backend.jac.
"""

import os;
import shutil;
import psycopg;
import from tempfile { mkdtemp }
import from uuid { UUID }

import from jaclang.jac0core.archetype { Root }
import from jaclang.jac0core.runtime { JacRuntime }
import from jaclang.runtimelib.context { ExecutionContext }
import from jaclang.runtimelib.changeset { ChangeSet }
import from jaclang.project.config { JacConfig, set_config }
import from jaclang.scale.memory.memory_hierarchy { PostgresRelBackend }

glob _DSN = os.environ.get('POSTGRESQL_REL_URI', 'postgresql:///jactest_rel');


node ResProjP {
    has name: str = "",
        age: int = 0;
}


edge ResKnows {}


def _fresh_be -> PostgresRelBackend {
    be: PostgresRelBackend = PostgresRelBackend(dsn=_DSN, pool_min=1, pool_max=3);
    raw: any = psycopg.connect(_DSN, autocommit=True);
    raw.execute("TRUNCATE anchors, anchors_quarantine, aliases");
    raw.execute("TRUNCATE edges RESTART IDENTITY");
    raw.close();
    return be;
}


"""ExecutionContext wired to a fresh rel backend; seeds root -ResKnows-> 3
ResProjP nodes through the live graph API + ChangeSet apply."""
def _ctx_with_graph -> tuple {
    be: any = _fresh_be();
    tmpdir = mkdtemp();
    orig_base = JacRuntime.get_base_path_dir();
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
        p = ResProjP(name=f"p{i}", age=i);
        r +>:ResKnows:+> p;
    }
    ra: any = r.__jac__;
    cs: any = ChangeSet();
    cs.record_create(ra);
    for e in ra.edges {
        ea: any = e;
        cs.record_create(ea);
        cs.record_create(ea.target);
    }
    rep: any = be.apply(cs);
    assert not rep.failed;
    return (ctx, be, r, tmpdir, orig_base);
}


def _teardown(ctx: any, be: any, tmpdir: str, orig_base: any) {
    mem: any = ctx.mem;
    mem.l3 = None;
    ctx.close();
    be.close();
    JacRuntime.set_base_path(orig_base);
    set_config(JacConfig());
    shutil.rmtree(tmpdir, ignore_errors=True);
    os.environ.pop('JAC_PROJECTION', None);
    os.environ.pop('JAC_READ_ONLY', None);
    os.environ.pop('JAC_ORDER_PUSHDOWN', None);
}


test "route A: declared + read-only -> slim marked anchors via execute_plan" {
    os.environ['JAC_PROJECTION'] = 'ResProjP:name';
    os.environ['JAC_READ_ONLY'] = '1';
    (ctx, be, r, tmpdir, orig_base) = _ctx_with_graph();
    try {
        found = [r->:ResKnows:->[?:ResProjP]];
        assert len(found) == 3;
        names = sorted([p.name for p in found]);
        assert names == ['p0', 'p1', 'p2'];
        assert be.rel_projection_count == 3 , "all three must come from projected fetch";
        marks = [p.__jac__?._projected_fields for p in found];
        assert all(m == {"name"} for m in marks);
    } finally {
        _teardown(ctx, be, tmpdir, orig_base);
    }
}


test "route A counter: read-only off -> full anchors" {
    os.environ['JAC_PROJECTION'] = 'ResProjP:name';
    os.environ.pop('JAC_READ_ONLY', None);
    (ctx, be, r, tmpdir, orig_base) = _ctx_with_graph();
    try {
        found = [r->:ResKnows:->[?:ResProjP]];
        assert len(found) == 3;
        assert be.rel_projection_count == 0;
        assert all(p.__jac__?._projected_fields is None for p in found);
        ages = sorted([p.age for p in found]);
        assert ages == [0, 1, 2] , "full anchors carry every field";
    } finally {
        _teardown(ctx, be, tmpdir, orig_base);
    }
}


test "route A counter: no declaration -> full anchors" {
    os.environ.pop('JAC_PROJECTION', None);
    os.environ['JAC_READ_ONLY'] = '1';
    (ctx, be, r, tmpdir, orig_base) = _ctx_with_graph();
    try {
        found = [r->:ResKnows:->[?:ResProjP]];
        assert len(found) == 3;
        assert be.rel_projection_count == 0;
        assert all(p.__jac__?._projected_fields is None for p in found);
    } finally {
        _teardown(ctx, be, tmpdir, orig_base);
    }
}


test "route A counter: field predicate keeps full path and correct results" {
    os.environ['JAC_PROJECTION'] = 'ResProjP:name';
    os.environ['JAC_READ_ONLY'] = '1';
    (ctx, be, r, tmpdir, orig_base) = _ctx_with_graph();
    try {
        found = [r->:ResKnows:->[?:ResProjP, age>=1]];
        names = sorted([p.name for p in found]);
        assert names == ['p1', 'p2'] , "predicate must filter on REAL values, never slim defaults";
        assert all(p.__jac__?._projected_fields is None for p in found);
    } finally {
        _teardown(ctx, be, tmpdir, orig_base);
    }
}


test "route B: ordered sliced hop -> projected anchors in hop order" {
    os.environ['JAC_PROJECTION'] = 'ResProjP:name';
    os.environ['JAC_READ_ONLY'] = '1';
    os.environ['JAC_ORDER_PUSHDOWN'] = 'ResProjP:name:desc';
    (ctx, be, r, tmpdir, orig_base) = _ctx_with_graph();
    try {
        found = [r->:ResKnows:->[?:ResProjP]][:2];
        assert len(found) == 2;
        names = [p.name for p in found];
        assert names == ['p2', 'p1'] , f"PG DESC order must survive: {names}";
        assert be.rel_projection_count == 2 , "page must hydrate via projected fetch";
        assert all(p.__jac__?._projected_fields == {"name"} for p in found);
    } finally {
        _teardown(ctx, be, tmpdir, orig_base);
    }
}
