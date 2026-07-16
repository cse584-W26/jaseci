"""Unit tests for Serializer.deserialize_projected -- the slim anchor
constructor for projection pushdown (spec Decision 2).

No database required. Covers: projected-field set + value deserialization,
anchor scaffolding (id/edges/version/access/marker), the loudness contract
(factory-default fields raise on unprojected access; scalar defaults are a
documented silent read), and the __jac__ link.
"""

import from uuid { UUID }

import from jaclang.jac0core.archetype { NodeAnchor }
import from jaclang.runtimelib.serializer { Serializer }


node SlimT {
    has a: str = "",
        b: int = 0,
        c: list[str] = [];
}


test "slim anchor sets projected fields and scaffolding" {
    aid = UUID(int=7);
    anchor = Serializer.deserialize_projected(
        aid, SlimT.__module__, "SlimT", {"a": "x"}, {"a"}
    );
    assert isinstance(anchor, NodeAnchor);
    assert anchor.id == aid;
    assert anchor.edges == [];
    assert anchor.version == 0;
    assert anchor.hash == 0;
    assert anchor.persistent;
    assert anchor.is_populated();
    assert anchor.archetype.a == "x";
    assert anchor.archetype.__jac__ is anchor;
    assert anchor._projected_fields == {"a"};
}

test "unprojected scalar reads class default silently, factory field raises" {
    anchor = Serializer.deserialize_projected(
        UUID(int=8), SlimT.__module__, "SlimT", {"a": "y"}, {"a"}
    );
    assert anchor.archetype.b == 0;
    ok = False;
    try {
        _ = anchor.archetype.c;
    } except AttributeError {
        ok = True;
    }
    assert ok;
}

test "projected list field survives with type intact" {
    anchor = Serializer.deserialize_projected(
        UUID(int=9),
        SlimT.__module__,
        "SlimT",
        {"c": ["u1", "u2"], "a": "z"},
        {"a", "c"}
    );
    assert anchor.archetype.c == ["u1", "u2"];
    assert anchor._projected_fields == {"a", "c"};
}

test "unknown class returns None" {
    anchor = Serializer.deserialize_projected(
        UUID(int=10), "nonexistent.module.xyz", "Nope", {"a": 1}, {"a"}
    );
    assert anchor is None;
}

test "projected field absent in storage stays unset" {
    anchor = Serializer.deserialize_projected(
        UUID(int=11), SlimT.__module__, "SlimT", {}, {"c"}
    );
    ok = False;
    try {
        _ = anchor.archetype.c;
    } except AttributeError {
        ok = True;
    }
    assert ok;
}


test "api serialization of slim archetype emits only projected fields" {
    anchor = Serializer.deserialize_projected(
        UUID(int=12), SlimT.__module__, "SlimT", {"a": "x"}, {"a"}
    );
    out = Serializer.serialize(anchor.archetype, api_mode=True);
    # Only the projected scalar 'a' appears -- the unprojected scalar-default
    # 'b' and factory-default 'c' must NOT leak class defaults into the payload.
    assert out["a"] == "x";
    assert "b" not in out;
    assert "c" not in out;
}
