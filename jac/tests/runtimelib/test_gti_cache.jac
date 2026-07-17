"""Unit tests for the decoded-GTI process cache.

The cache maps root_id -> (blake2b(blob), decoded TopologyIndex): the digest
check makes staleness impossible (any blob change changes the digest) while
root_id keying means a mutated root REPLACES its old entry instead of
accumulating dead versions. Cached entries are frozen -- mutating one raises.
These tests drive the cache module directly with hand-built TopologyIndex
blobs -- no backend, no server.
"""

import os;
import from uuid { uuid4 }
import from jaclang.runtimelib.topology_index { TopologyIndex }
import from jaclang.runtimelib.gti_cache {
    decode_cached,
    clear_cache,
    cache_stats,
    cache_capacity
}
import from jaclang.runtimelib.utils { gti_cache_enabled }


"""Build a small encoded index: n0 -edge_type-> n1."""
def _blob(edge_type: str = "Knows") -> bytes {
    idx = TopologyIndex();
    (n0, n1) = (uuid4(), uuid4());
    idx.add_node(n0, "Person");
    idx.add_node(n1, "Person");
    idx.add_edge(n0, n1, edge_type);
    return idx.encode();
}


def _set_env(name: str, value: (str | None)) {
    if value is None {
        if name in os.environ {
            del os.environ[name];
        }
    } else {
        os.environ[name] = value;
    }
}


test "decode_cached matches direct decode" {
    clear_cache();
    blob = _blob();
    cached = decode_cached(uuid4(), blob);
    direct = TopologyIndex.decode(blob);
    assert len(cached) == len(direct);
    assert set(cached.node_to_lid.keys()) == set(direct.node_to_lid.keys());
}


test "same root and blob hit returns the same decoded object" {
    clear_cache();
    rid = uuid4();
    blob = _blob();
    a = decode_cached(rid, blob);
    b = decode_cached(rid, bytes(blob));
    assert a is b , "content-equal blob for the same root must hit the cache";
    stats = cache_stats();
    assert stats["misses"] == 1 , f"expected 1 miss, got {stats}";
    assert stats["hits"] == 1 , f"expected 1 hit, got {stats}";
}


test "changed blob for the same root replaces the entry, not accumulates" {
    clear_cache();
    rid = uuid4();
    old = decode_cached(rid, _blob("Knows"));
    new = decode_cached(rid, _blob("Follows"));
    assert new is not old , "changed blob must decode fresh";
    stats = cache_stats();
    assert stats["misses"] == 2 and stats["size"] == 1 , (
        f"superseded version must be replaced, not retained: {stats}"
    );
}


test "distinct roots occupy distinct entries" {
    clear_cache();
    decode_cached(uuid4(), _blob("Knows"));
    decode_cached(uuid4(), _blob("Follows"));
    stats = cache_stats();
    assert stats["misses"] == 2 and stats["size"] == 2 , f"got {stats}";
}


test "capacity bounds the cache with LRU eviction" {
    prev = os.environ.get("JAC_GTI_CACHE_SIZE");
    _set_env("JAC_GTI_CACHE_SIZE", "2");
    try {
        clear_cache();
        assert cache_capacity() == 2;
        (r1, r2, r3) = (uuid4(), uuid4(), uuid4());
        (b1, b2, b3) = (_blob("E1"), _blob("E2"), _blob("E3"));
        decode_cached(r1, b1);
        decode_cached(r2, b2);
        decode_cached(r1, b1);  # touch r1 -> r2 becomes LRU
        decode_cached(r3, b3);  # evicts r2
        stats = cache_stats();
        assert stats["evictions"] == 1 , f"expected 1 eviction, got {stats}";
        decode_cached(r1, b1);  # still cached
        assert cache_stats()["hits"] == 2 , f"r1 should still hit: {cache_stats()}";
        decode_cached(r2, b2);  # was evicted -> miss
        assert cache_stats()["misses"] == 4 , f"r2 should re-miss: {cache_stats()}";
    } finally {
        _set_env("JAC_GTI_CACHE_SIZE", prev);
        clear_cache();
    }
}


test "malformed JAC_GTI_CACHE_SIZE fails loud" {
    prev = os.environ.get("JAC_GTI_CACHE_SIZE");
    _set_env("JAC_GTI_CACHE_SIZE", "512MB");
    try {
        raised = False;
        try {
            clear_cache();
        } except ValueError {
            raised = True;
        }
        assert raised , "malformed capacity must raise, not silently default";
    } finally {
        _set_env("JAC_GTI_CACHE_SIZE", prev);
        clear_cache();
    }
}


test "cached index is frozen: mutation raises" {
    clear_cache();
    cached = decode_cached(uuid4(), _blob());
    raised = False;
    try {
        cached.add_node(uuid4(), "Person");
    } except RuntimeError {
        raised = True;
    }
    assert raised , "mutating a shared cached index must raise";
    # A privately decoded index stays mutable.
    private = TopologyIndex.decode(_blob());
    private.add_node(uuid4(), "Person");
}


test "gti_cache_enabled reads JAC_GTI_CACHE env first" {
    prev = os.environ.get("JAC_GTI_CACHE");
    try {
        _set_env("JAC_GTI_CACHE", "1");
        assert gti_cache_enabled() == True;
        _set_env("JAC_GTI_CACHE", "0");
        assert gti_cache_enabled() == False;
    } finally {
        _set_env("JAC_GTI_CACHE", prev);
    }
}
