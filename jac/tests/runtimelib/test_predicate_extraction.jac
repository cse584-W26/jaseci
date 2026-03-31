"""Tests for predicate extraction from FilterCompr via UniIR AST introspection.

Verifies that extract_query_filter() correctly extracts structured predicates
from filter comprehension lambdas without requiring any database interaction.
"""

import os;
import shutil;
import from tempfile { mkdtemp }
import from jaclang { JacRuntimeInterface as Jac }
import from jaclang.jac0core.runtime { JacRuntime }
import from jaclang.runtimelib.context { ExecutionContext }
import from jaclang.project.config { JacConfig, set_config }
import from jaclang.runtimelib.query_filter { CompareOp, Predicate, QueryFilter }
import from jaclang.runtimelib.topo_utils { extract_query_filter }

node PersonNode {
    has name: str = "",
        age: int = 0,
        active: bool = True,
        score: float = 0.0;
}

node ItemNode {
    has tag: str = "";
}

edge Link {}

test "extract_query_filter returns None for None input" {
    qf = extract_query_filter(None);
    assert qf is None;
}

test "extract_query_filter returns None for plain python lambda" {
    filt = lambda x: x > 5;
    qf = extract_query_filter(filt);
    assert qf is None;
}

test "QueryFilter types are constructible" {
    p = Predicate(field_name="name", op=CompareOp.EQ, value="Alice");
    assert p.field_name == "name";
    assert p.op == CompareOp.EQ;
    assert p.value == "Alice";

    qf = QueryFilter(type_name="PersonNode", predicates=[p]);
    assert qf.type_name == "PersonNode";
    assert len(qf.predicates) == 1;
    assert qf.predicates[0].field_name == "name";
}

test "QueryFilter with multiple predicates" {
    preds = [
        Predicate(field_name="name", op=CompareOp.EQ, value="Alice"),
        Predicate(field_name="age", op=CompareOp.GT, value=21),
        Predicate(field_name="score", op=CompareOp.GE, value=3.5)
    ];
    qf = QueryFilter(type_name="PersonNode", predicates=preds);
    assert qf.type_name == "PersonNode";
    assert len(qf.predicates) == 3;
    assert qf.predicates[0].op == CompareOp.EQ;
    assert qf.predicates[1].op == CompareOp.GT;
    assert qf.predicates[2].op == CompareOp.GE;
}

test "QueryFilter defaults" {
    qf = QueryFilter();
    assert qf.type_name is None;
    assert qf.predicates == [];
}

test "CompareOp enum values" {
    assert CompareOp.EQ.value == "eq";
    assert CompareOp.NE.value == "ne";
    assert CompareOp.LT.value == "lt";
    assert CompareOp.LE.value == "le";
    assert CompareOp.GT.value == "gt";
    assert CompareOp.GE.value == "ge";
    assert CompareOp.IN.value == "in";
    assert CompareOp.NOT_IN.value == "not_in";
}

test "filter comprehension with type only returns correct results" {
    tmpdir = mkdtemp();
    orig_base = JacRuntime.base_path_dir;
    try {
        cfg = JacConfig();
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);

        r = root;
        Jac.save(r);
        r +>: Link :+> PersonNode(name="Bob", age=25);
        r +>: Link :+> ItemNode(tag="item1");
        Jac.save(r);

        persons = [r->:Link:->[?:PersonNode]];
        assert len(persons) == 1, f"Expected 1 person, got {len(persons)}";
        assert persons[0].name == "Bob";

        items = [r->:Link:->[?:ItemNode]];
        assert len(items) == 1, f"Expected 1 item, got {len(items)}";
        assert items[0].tag == "item1";

        ctx.close();
    } finally {
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
}

test "filter comprehension with data predicate returns correct results" {
    tmpdir = mkdtemp();
    orig_base = JacRuntime.base_path_dir;
    try {
        cfg = JacConfig();
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);

        r = root;
        Jac.save(r);
        for i in range(10) {
            r +>: Link :+> PersonNode(name=f"Person_{i}", age=20 + i);
        }
        Jac.save(r);

        result = [r->:Link:->[?:PersonNode, name=="Person_5"]];
        assert len(result) == 1, f"Expected 1 result, got {len(result)}";
        assert result[0].name == "Person_5";
        assert result[0].age == 25;

        ctx.close();
    } finally {
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
}
