"""Safety guards for projected anchors in TieredMemory (spec Decision 3).

- dirty-scan guard: _collect_into must never record intents for anchors
  carrying _projected_fields, even with read-only OFF.
- L1/L2 rule: TieredMemory.execute_plan must yield projected anchors without
  inserting them into L1 (__mem__) or batching them to L2.
"""

import os;
import shutil;
import from tempfile { mkdtemp }
import from uuid { UUID, uuid4 }

import from jaclang.jac0core.runtime { JacRuntime }
import from jaclang.runtimelib.context { ExecutionContext }
import from jaclang.runtimelib.changeset { ChangeSet, snapshot_field_hashes }
import from jaclang.runtimelib.serializer { Serializer }
import from jaclang.runtimelib.query_plan { QueryPlan }
import from jaclang.project.config { JacConfig, set_config }


node MemT {
    has name: str = "";
}


def _ctx_fixture -> tuple {
    tmpdir = mkdtemp();
    orig_base = JacRuntime.get_base_path_dir();
    cfg = JacConfig();
    set_config(cfg);
    JacRuntime.set_base_path(tmpdir);
    ctx = ExecutionContext();
    JacRuntime.set_context(ctx);
    return (ctx, tmpdir, orig_base);
}


def _teardown(ctx: any, tmpdir: str, orig_base: any) {
    mem: any = ctx.mem;
    mem.l3 = None;
    ctx.close();
    JacRuntime.set_base_path(orig_base);
    set_config(JacConfig());
    shutil.rmtree(tmpdir, ignore_errors=True);
}


test "dirty scan skips projected anchors even with read-only off" {
    os.environ.pop("JAC_READ_ONLY", None);
    (ctx, tmpdir, orig_base) = _ctx_fixture();
    try {
        r = root;
        p = MemT(name="before");
        r ++> p;
        a: any = p.__jac__;
        a.persistent = True;
        a.hash = Serializer._compute_hash(a);
        snapshot_field_hashes(a);

        # sanity: without the marker this mutation IS collected
        p.name = "after";
        cs = ChangeSet();
        ctx.mem._collect_into(cs);
        assert a.id in cs.intents , "unmarked mutation must be collected";

        setattr(a, '_projected_fields', {"name"});
        cs2 = ChangeSet();
        ctx.mem._collect_into(cs2);
        assert a.id not in cs2.intents , "projected anchor must never produce intents";
    } finally {
        _teardown(ctx, tmpdir, orig_base);
    }
}


obj _StubL3 {
    has yielded: list = [];

    def execute_plan(plan: any) -> any {
        for a in self.yielded {
            yield a;
        }
    }
}


test "execute_plan yields projected anchors without caching in L1" {
    (ctx, tmpdir, orig_base) = _ctx_fixture();
    try {
        marked = Serializer.deserialize_projected(
            uuid4(), MemT.__module__, "MemT", {"name": "slim"}, {"name"}
        );
        assert marked is not None;

        full = MemT(name="full");
        fa: any = full.__jac__;
        ctx.mem.__mem__.pop(fa.id, None);

        stub = _StubL3(yielded=[marked, fa]);
        mem: any = ctx.mem;
        mem.l3 = stub;
        mem.l2 = None;

        out = list(mem.execute_plan(QueryPlan(id_in={marked.id, fa.id})));
        assert len(out) == 2;
        assert marked in out and fa in out;
        assert marked.id not in mem.__mem__ , "projected anchor must not enter L1";
        assert fa.id in mem.__mem__ , "full anchor keeps today's L1 insert";
    } finally {
        _teardown(ctx, tmpdir, orig_base);
    }
}
