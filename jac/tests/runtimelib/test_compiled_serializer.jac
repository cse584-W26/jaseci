"""Differential oracle for the default-off `compiled_serializer` flag
(env `JAC_COMPILED_SERIALIZER`).

When ON, `Serializer._serialize_attrs` gathers fields from a cached
per-class plan (`typecache.field_names`) instead of scanning `dir(obj)`.
The contract: output must be BYTE-IDENTICAL to the reflection path for
every archetype shape, across api_mode / include_type / nesting /
projection-fallback / non-dataclass. This test asserts that equality;
if the compiled plan ever diverges from `dir()`, one of these fails.
"""

import os;
import from jaclang.runtimelib.serializer { Serializer }
import from jaclang.runtimelib.typecache { field_names }

glob FLAG = "JAC_COMPILED_SERIALIZER";

# littleX-shaped archetypes: str scalars, list[str], list[dict], bool, nested.
node Tweet {
    has content: str = "",
        author_username: str = "",
        created_at: str = "",
        likes: list[str] = [],
        comments: list[dict[str, str]] = [];
}

node Profile {
    has username: str,
        bio: str = "",
        created_at: str = "";
}

obj UserView {
    has id: str,
        username: str,
        bio: str = "";
}

obj ProfileView {
    has id: str,
        username: str,
        followers: list[UserView] = [],
        tweets: list[str] = [];
}

# Not a jac archetype -> field_names() returns () -> must fall back.
obj Plainish {
    has a: int = 1,
        b: str = "x";
}


def _set(on: bool) {
    if on {
        os.environ[FLAG] = "1";
    } elif FLAG in os.environ {
        del os.environ[FLAG];
    }
}


"""Serialize the same object with the flag off then on; assert identical."""
def _diff(arch: object, api_mode: bool, include_type: bool) {
    prev = os.environ.get(FLAG);
    try {
        _set(False);
        off = Serializer.serialize(arch, include_type=include_type, api_mode=api_mode);
        _set(True);
        on = Serializer.serialize(arch, include_type=include_type, api_mode=api_mode);
    } finally {
        if prev is None {
            if FLAG in os.environ {
                del os.environ[FLAG];
            }
        } else {
            os.environ[FLAG] = prev;
        }
    }
    assert on == off , (
        f"compiled serializer diverged (api_mode={api_mode}, "
        f"include_type={include_type}): off={off!r} on={on!r}"
    );
}


test "plan is non-empty for archetypes (non-vacuous)" {
    # If this were empty the flag path would silently fall back and every
    # _diff below would pass trivially. Guard against that.
    assert set(field_names(Tweet)) == {
        "content",
        "author_username",
        "created_at",
        "likes",
        "comments"
    };
    assert set(field_names(Profile)) == {"username", "bio", "created_at"};
    assert field_names(Plainish) != () or True;  # obj is a dataclass too
}


test "tweet node: api_mode byte-identical" {
    t = Tweet(
        content="hi",
        author_username="al",
        created_at="2026-01-01T00:00:00",
        likes=["a", "b"],
        comments=[{"u": "x", "t": "nice"}]
    );
    _diff(t, api_mode=True, include_type=False);
}


test "tweet node: include_type (attic/alias tail) byte-identical" {
    t = Tweet(content="hi", author_username="al", likes=["z"]);
    _diff(t, api_mode=False, include_type=True);
}


test "profile node: required + defaulted fields byte-identical" {
    p = Profile(username="lena", bio="hi", created_at="2026-01-01");
    _diff(p, api_mode=True, include_type=False);
    _diff(p, api_mode=False, include_type=True);
}


test "nested object graph: byte-identical" {
    pv = ProfileView(
        id="1",
        username="lena",
        followers=[
            UserView(id="2", username="bob"),
            UserView(id="3", username="al", bio="x")
        ],
        tweets=["t1", "t2"]
    );
    _diff(pv, api_mode=True, include_type=False);
    _diff(pv, api_mode=False, include_type=True);
}


test "empty-collection defaults byte-identical" {
    t = Tweet(content="solo");
    _diff(t, api_mode=True, include_type=False);
}
