"""JAC_LAZY_HYDRATION (Task 1): _materialize_ids hands callers id-only stubs
that defer archetype hydration until a field is read, then populate correctly
from L1 (batched by the single batch_get -- never a per-anchor L3 refetch, the
projection-arm N+1 trap). Flag OFF must be byte-identical to today.

topology_index is forced OFF so the traversal lands on the floor/walk path
(_hop_via_walk -> _materialize_ids); with the GTI on, mid-chain nodes stay bare
UUIDs and no anchor is built at all, so lazy has nothing to defer.
"""

import os;
import shutil;
import from tempfile { mkdtemp }

import from jaclang.jac0core.runtime { JacRuntime }
import from jaclang.runtimelib.context { ExecutionContext }
import from jaclang.runtimelib.query_utils { _materialize_ids }
import from jaclang.project.config { JacConfig, set_config }


node LazyT {
    has name: str = "";
}


edge LKnows {}


def _ctx_fixture -> tuple {
    tmpdir = mkdtemp();
    orig_base = JacRuntime.get_base_path_dir();
    cfg = JacConfig();
    cfg.run.topology_index = False;
    set_config(cfg);
    JacRuntime.set_base_path(tmpdir);
    ctx = ExecutionContext();
    JacRuntime.set_context(ctx);
    return (ctx, tmpdir, orig_base);
}


def _teardown(ctx: any, tmpdir: str, orig_base: any) {
    ctx.close();
    JacRuntime.set_base_path(orig_base);
    set_config(JacConfig());
    shutil.rmtree(tmpdir, ignore_errors=True);
    os.environ.pop("JAC_LAZY_HYDRATION", None);
}


test "flag off: _materialize_ids returns fully populated anchors (unchanged)" {
    os.environ.pop("JAC_LAZY_HYDRATION", None);
    (ctx, tmpdir, orig_base) = _ctx_fixture();
    try {
        r = root;
        p = LazyT(name="alpha");
        r ++> p;
        pid = p.__jac__.id;
        got = _materialize_ids(ctx.mem, [pid]);
        assert len(got) == 1;
        a: any = got[0];
        assert a.is_populated() , "flag off must yield a populated anchor";
        assert a.__dict__.get('_lazy_stub') is None , "no lazy marker when off";
        assert a.archetype.name == "alpha";
    } finally {
        _teardown(ctx, tmpdir, orig_base);
    }
}


test "flag on: stub defers hydration then field access populates correctly" {
    os.environ["JAC_LAZY_HYDRATION"] = "1";
    (ctx, tmpdir, orig_base) = _ctx_fixture();
    try {
        r = root;
        p = LazyT(name="beta");
        r ++> p;
        pid = p.__jac__.id;
        got = _materialize_ids(ctx.mem, [pid]);
        assert len(got) == 1;
        stub: any = got[0];
        assert stub.__dict__.get('_lazy_stub') is True , "must carry lazy marker";
        assert not stub.is_populated() , "stub must start unhydrated";
        # lazy state is NOT projection state -- distinct markers, must compose
        assert stub.__dict__.get('_projected_fields') is None;
        # first field access hydrates lazily AND correctly (from L1, no refetch)
        assert stub.archetype.name == "beta" , "deferred field must be correct";
        assert stub.is_populated() , "field access must have populated the stub";
    } finally {
        _teardown(ctx, tmpdir, orig_base);
    }
}


test "traversal through stubs yields the same results as eager" {
    (ctx, tmpdir, orig_base) = _ctx_fixture();
    try {
        r = root;
        for nm in ["a", "b", "c"] {
            r ++> LazyT(name=nm);
        }

        os.environ.pop("JAC_LAZY_HYDRATION", None);
        eager = sorted([p.name for p in [r-->[?:LazyT]]]);

        os.environ["JAC_LAZY_HYDRATION"] = "1";
        lazy = sorted([p.name for p in [r-->[?:LazyT]]]);

        assert eager == ["a", "b", "c"] , f"eager baseline wrong: {eager}";
        assert lazy == eager , f"lazy traversal must match eager: {lazy}";
    } finally {
        _teardown(ctx, tmpdir, orig_base);
    }
}
