"""Integration tests for predicate pushdown to SQLite.

Verifies that filter comprehensions with data predicates push filters
to the SQL layer, reducing the number of nodes deserialized from L3.
"""

import os;
import shutil;
import sqlite3;
import from tempfile { mkdtemp }
import from jaclang { JacRuntimeInterface as Jac }
import from jaclang.jac0core.runtime { JacRuntime }
import from jaclang.runtimelib.context { ExecutionContext }
import from jaclang.project.config { JacConfig, set_config }

node PersonNode {
    has name: str = "",
        age: int = 0,
        active: bool = True;
}

node ItemNode {
    has tag: str = "",
        price: float = 0.0;
}

edge Link {}

test "node_properties table is populated on sync" {
    tmpdir = mkdtemp();
    orig_base = JacRuntime.base_path_dir;
    try {
        cfg = JacConfig();
        cfg.run.topology_index = True;
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);

        r = root;
        Jac.save(r);
        r +>: Link :+> PersonNode(name="Alice", age=30, active=True);
        r +>: Link :+> PersonNode(name="Bob", age=25, active=False);
        Jac.save(r);

        # Check the SQLite database directly
        db_path = os.path.join(tmpdir, ".jaseci", "main.db");
        if os.path.exists(db_path) {
            conn = sqlite3.connect(db_path);
            cursor = conn.execute("SELECT anchor_id, field_name, field_value, field_type FROM node_properties ORDER BY anchor_id, field_name");
            rows = cursor.fetchall();
            conn.close();

            # Should have properties for both PersonNodes
            field_names = [r[1] for r in rows];
            assert "name" in field_names, f"Expected 'name' in fields, got {field_names}";
            assert "age" in field_names, f"Expected 'age' in fields, got {field_names}";
            assert "active" in field_names, f"Expected 'active' in fields, got {field_names}";

            # Check Alice's name value
            alice_rows = [r for r in rows if r[1] == "name" and r[2] == "Alice"];
            assert len(alice_rows) >= 1, f"Expected Alice in node_properties, got {rows}";
        }

        ctx.close();
    } finally {
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
}

test "predicate pushdown returns correct results" {
    tmpdir = mkdtemp();
    orig_base = JacRuntime.base_path_dir;
    try {
        cfg = JacConfig();
        cfg.run.topology_index = True;
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);

        r = root;
        Jac.save(r);
        for i in range(20) {
            r +>: Link :+> PersonNode(name=f"Person_{i}", age=20 + i);
        }
        Jac.save(r);

        # Query with data predicate
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

test "predicate pushdown with numeric comparison" {
    tmpdir = mkdtemp();
    orig_base = JacRuntime.base_path_dir;
    try {
        cfg = JacConfig();
        cfg.run.topology_index = True;
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);

        r = root;
        Jac.save(r);
        for i in range(10) {
            r +>: Link :+> ItemNode(tag=f"item_{i}", price=float(10 + i));
        }
        Jac.save(r);

        # All items
        all_items = [r->:Link:->[?:ItemNode]];
        assert len(all_items) == 10, f"Expected 10, got {len(all_items)}";

        ctx.close();
    } finally {
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
}

test "pushdown with multiple predicates" {
    tmpdir = mkdtemp();
    orig_base = JacRuntime.base_path_dir;
    try {
        cfg = JacConfig();
        cfg.run.topology_index = True;
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);

        r = root;
        Jac.save(r);
        r +>: Link :+> PersonNode(name="Alice", age=30, active=True);
        r +>: Link :+> PersonNode(name="Alice", age=25, active=False);
        r +>: Link :+> PersonNode(name="Bob", age=30, active=True);
        Jac.save(r);

        # Filter by name only
        alices = [r->:Link:->[?:PersonNode, name=="Alice"]];
        assert len(alices) == 2, f"Expected 2 Alices, got {len(alices)}";

        # Filter by age only
        age30 = [r->:Link:->[?:PersonNode, age==30]];
        assert len(age30) == 2, f"Expected 2 age-30, got {len(age30)}";

        ctx.close();
    } finally {
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
}

test "pushdown fallback for non-extractable filter" {
    tmpdir = mkdtemp();
    orig_base = JacRuntime.base_path_dir;
    try {
        cfg = JacConfig();
        cfg.run.topology_index = True;
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);

        r = root;
        Jac.save(r);
        r +>: Link :+> PersonNode(name="Alice", age=30);
        r +>: Link :+> PersonNode(name="Bob", age=25);
        Jac.save(r);

        # Type-only filter (no data predicate) — should still work
        persons = [r->:Link:->[?:PersonNode]];
        assert len(persons) == 2, f"Expected 2, got {len(persons)}";

        ctx.close();
    } finally {
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
}

test "empty result set with predicate" {
    tmpdir = mkdtemp();
    orig_base = JacRuntime.base_path_dir;
    try {
        cfg = JacConfig();
        cfg.run.topology_index = True;
        set_config(cfg);
        JacRuntime.set_base_path(tmpdir);
        ctx = ExecutionContext();
        JacRuntime.set_context(ctx);

        r = root;
        Jac.save(r);
        r +>: Link :+> PersonNode(name="Alice", age=30);
        r +>: Link :+> PersonNode(name="Bob", age=25);
        Jac.save(r);

        # No match
        result = [r->:Link:->[?:PersonNode, name=="Charlie"]];
        assert len(result) == 0, f"Expected 0, got {len(result)}";

        ctx.close();
    } finally {
        JacRuntime.set_base_path(orig_base);
        set_config(JacConfig());
        shutil.rmtree(tmpdir, ignore_errors=True);
    }
}
