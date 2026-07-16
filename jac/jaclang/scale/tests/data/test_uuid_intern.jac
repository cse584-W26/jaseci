"""UUID interning on the deserialize path (flagless perf rider).

_intern_uuid is an lru_cache over UUID(str) construction; same string must
return the SAME object (cache hit skips re-parse). Value equality with bare
UUID() is the safety contract (no is-identity callers exist).
"""

import from uuid { UUID }

import from jaclang.runtimelib.serializer { Serializer, _intern_uuid }
import from jaclang.runtimelib.utils { to_uuid }


node ProjT {
    has name: str = "";
}


test "intern uuid identity and value" {
    a = _intern_uuid("00000000-0000-0000-0000-000000000001");
    b = _intern_uuid("00000000-0000-0000-0000-000000000001");
    assert a == UUID(int=1);
    assert a is b;
}


test "deserialize_anchor ids intern" {
    data = {
        '__type__': 'NodeAnchor',
        'id': '00000000-0000-0000-0000-00000000000a',
        'root': '00000000-0000-0000-0000-00000000000b',
        'persistent': True,
        'edges': ['00000000-0000-0000-0000-00000000000c']
    };
    a1 = Serializer._deserialize_anchor(data);
    a2 = Serializer._deserialize_anchor(dict(data));
    assert a1 is not None and a2 is not None;
    assert a1.id is a2.id , "anchor ids must be interned across deserializes";
    assert a1.root is a2.root;
}


test "deserialize_projected ids intern" {
    id_str = '00000000-0000-0000-0000-00000000000d';
    a1 = Serializer.deserialize_projected(
        to_uuid(id_str), ProjT.__module__, "ProjT", {"name": "slim"}, {"name"}
    );
    a2 = Serializer.deserialize_projected(
        to_uuid(id_str), ProjT.__module__, "ProjT", {"name": "slim"}, {"name"}
    );
    assert a1 is not None and a2 is not None;
    assert a1.id is a2.id , "projected anchor ids must be interned across deserializes";
}
