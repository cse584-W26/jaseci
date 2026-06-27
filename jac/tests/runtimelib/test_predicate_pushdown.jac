"""Tests that value predicates in filter comprehensions are extracted and
pushed down to a backend that advertises native field filtering.

The default SQLite backend declares no `field_pushdown` capability, so on it a
value-filtered hop falls back to the in-process walk (covered by the e2e
suite). Here we stand in a backend that DOES advertise `field_pushdown` and
assert the planner hands it a `QueryPlan` carrying the extracted
`field_predicates` — i.e. `_extract_field_predicates` + the resolver fast path
work end to end — while results stay correct via the retained post-filter.
"""

import from jaclang.jac0core.runtime { JacRuntime }
import from jaclang.runtimelib.context { ExecutionContext }
import from jaclang.runtimelib.query_utils { _extract_field_predicates }
import from jaclang.project.config { JacConfig, set_config }

node Person {
    has name: str = "",
        age: int = 0;
}

edge Link {}

glob captured: list = [];


"""Make `mem` advertise native field pushdown and record every plan handed to
execute_plan, fulfilling it from the floor (batch_get of the narrowed ids) so
the resolver's retained post_filter still applies the real comparison."""
def _instrument(mem: any) -> None {
    def fake_caps -> set {
        return {'type_pushdown', 'field_pushdown', 'id_in', 'slice'};
    }
    def fake_execute_plan(plan: any) {
        captured.append(plan.field_predicates);
        loaded = mem.batch_get(`list(plan.id_in));
        for a in loaded.values() {
            yield a;
        }
    }
    mem.capabilities = fake_caps;
    mem.execute_plan = fake_execute_plan;
}


test "value predicate is extracted and pushed to a field_pushdown backend" {
    cfg = JacConfig();
    cfg.run.topology_index = True;
    set_config(cfg);
    captured.clear();
    ctx = ExecutionContext();
    JacRuntime.set_context(ctx);
    try {
        r = root;
        for i in range(20) {
            r +>:Link:+> Person(name=f"p{i}", age=i);
        }
        _instrument(ctx.mem);

        result = [r->:Link:->[?:Person, age > 5]];

        # Correctness: only ages 6..19 survive.
        assert sorted([n.age for n in result]) == list(range(6, 20)) ,
            f"got {sorted([n.age for n in result])}";
        # Pushdown fired exactly once and carried the extracted predicate.
        assert len(captured) == 1 , f"execute_plan calls: {len(captured)}";
        assert captured[0] == {'age': {'$gt': 5}} , f"field_predicates: {captured[0]}";
    } finally {
        ctx.close();
        set_config(JacConfig());
    }
}


test "multiple comparisons on one field merge into a single operator dict" {
    cfg = JacConfig();
    cfg.run.topology_index = True;
    set_config(cfg);
    captured.clear();
    ctx = ExecutionContext();
    JacRuntime.set_context(ctx);
    try {
        r = root;
        for i in range(20) {
            r +>:Link:+> Person(name=f"p{i}", age=i);
        }
        _instrument(ctx.mem);

        result = [r->:Link:->[?:Person, age > 5, age < 10]];

        assert sorted([n.age for n in result]) == [6, 7, 8, 9] ,
            f"got {sorted([n.age for n in result])}";
        assert captured[0] == {'age': {'$gt': 5, '$lt': 10}} ,
            f"field_predicates: {captured[0]}";
    } finally {
        ctx.close();
        set_config(JacConfig());
    }
}


test "equality predicate extracts to an $eq operator dict" {
    cfg = JacConfig();
    cfg.run.topology_index = True;
    set_config(cfg);
    captured.clear();
    ctx = ExecutionContext();
    JacRuntime.set_context(ctx);
    try {
        r = root;
        for i in range(10) {
            r +>:Link:+> Person(name=f"p{i}", age=i);
        }
        _instrument(ctx.mem);

        result = [r->:Link:->[?:Person, age == 3]];

        assert sorted([n.age for n in result]) == [3] , f"got {[n.age for n in result]}";
        assert captured[0] == {'age': {'$eq': 3}} , f"field_predicates: {captured[0]}";
    } finally {
        ctx.close();
        set_config(JacConfig());
    }
}
