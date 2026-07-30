"""Regression tests for the serializer anchor-peek fix and the shared
projected Permission.

Invariant 1: serializing a plain view object must NOT materialize an
anchor as a side effect. `_serialize_attrs` peeks `__jac__` via the
instance `__dict__` instead of touching the cached_property, which would
construct a throwaway ObjectAnchor + uuid4 + Permission per object.

Invariant 2: real projected anchors are still detected through the same
peek - the serializer emits only the projected field subset.

Invariant 3: projected anchors share one NO_ACCESS Permission whose
roots dict is a mapping proxy; a grant attempt raises instead of
silently mutating state shared across anchors.
"""

import uuid;
import from jaclang.runtimelib.serializer {
    Serializer,
    _shared_projected_permission
}

obj TweetView {
    has id: str,
        content: str,
        author_username: str = "",
        likes: list[str] = [];
}

node ProjTweet {
    has content: str = "",
        author_username: str = "",
        secret_field: str = "hidden-default";
}

test "serializing a view object materializes no anchor" {
    views = [
        TweetView(id=f"v{i}", content=f"c{i}", likes=["a", "b"])
        for i in range(20)
    ];
    out = Serializer.serialize(views, api_mode=True);
    assert isinstance(out, list) and len(out) == 20;
    for v in views {
        assert '__jac__' not in v.__dict__, (
            "serialize() built a throwaway anchor on a view object"
        );
    }
}

test "projected anchor: only the projected subset is emitted" {
    anchor = Serializer.deserialize_projected(
        uuid.uuid4(),
        __name__,
        'ProjTweet',
        {'content': 'hello', 'author_username': 'alice'},
        {'content', 'author_username'},
        str(uuid.uuid4())
    );
    assert anchor is not None;
    attrs = Serializer._serialize_attrs(
        anchor.archetype, include_type=False, api_mode=True
    );
    assert set(attrs.keys()) == {'content', 'author_username'}, (
        f"projected serialization leaked fields: {set(attrs.keys())}"
    );
    assert 'secret_field' not in attrs;
}

test "projected anchors share one Permission; grants fail loud" {
    a1 = Serializer.deserialize_projected(
        uuid.uuid4(), __name__, 'ProjTweet', {'content': 'x'}, {'content'}
    );
    a2 = Serializer.deserialize_projected(
        uuid.uuid4(), __name__, 'ProjTweet', {'content': 'y'}, {'content'}
    );
    assert a1.access is a2.access, "projected anchors should share one Permission";
    assert a1.access is _shared_projected_permission();
    raised = False;
    try {
        a1.access.roots.anchors['some-root'] = 2;
    } except TypeError {
        raised = True;
    }
    assert raised, (
        "grant on a projected anchor must raise, not mutate shared state"
    );
}
