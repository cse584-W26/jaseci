"""Unit tests for the content-addressed decoded-GTI process cache.

The cache maps blake2b(topology_index_data) -> decoded TopologyIndex, so a
cached entry can never go stale: any blob change changes the key. These tests
drive the cache module directly with hand-built TopologyIndex blobs -- no
backend, no server.
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


"""Build a small encoded index: n0 -Knows-> n1."""
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
    cached = decode_cached(blob);
    direct = TopologyIndex.decode(blob);
    assert len(cached) == len(direct);
    assert set(cached.node_to_lid.keys()) == set(direct.node_to_lid.keys());
}


test "same bytes hit returns the same decoded object" {
    clear_cache();
    blob = _blob();
    a = decode_cached(blob);
    b = decode_cached(bytes(blob));
    assert a is b , "content-equal blob must hit the cache";
    stats = cache_stats();
    assert stats["misses"] == 1 , f"expected 1 miss, got {stats}";
    assert stats["hits"] == 1 , f"expected 1 hit, got {stats}";
}


test "different bytes miss independently" {
    clear_cache();
    a = decode_cached(_blob("Knows"));
    b = decode_cached(_blob("Follows"));
    assert a is not b;
    stats = cache_stats();
    assert stats["misses"] == 2 and stats["hits"] == 0 , f"got {stats}";
}


test "capacity bounds the cache with LRU eviction" {
    prev = os.environ.get("JAC_GTI_CACHE_SIZE");
    _set_env("JAC_GTI_CACHE_SIZE", "2");
    try {
        clear_cache();
        assert cache_capacity() == 2;
        (b1, b2, b3) = (_blob("E1"), _blob("E2"), _blob("E3"));
        decode_cached(b1);
        decode_cached(b2);
        decode_cached(b1);  # touch b1 -> b2 becomes LRU
        decode_cached(b3);  # evicts b2
        stats = cache_stats();
        assert stats["evictions"] == 1 , f"expected 1 eviction, got {stats}";
        decode_cached(b1);  # still cached
        assert cache_stats()["hits"] == 2 , f"b1 should still hit: {cache_stats()}";
        decode_cached(b2);  # was evicted -> miss
        assert cache_stats()["misses"] == 4 , f"b2 should re-miss: {cache_stats()}";
    } finally {
        _set_env("JAC_GTI_CACHE_SIZE", prev);
        clear_cache();
    }
}


test "gti_cache_enabled reads JAC_GTI_CACHE env first, defaults off" {
    prev = os.environ.get("JAC_GTI_CACHE");
    try {
        _set_env("JAC_GTI_CACHE", None);
        assert gti_cache_enabled() == False , "flag must default off";
        _set_env("JAC_GTI_CACHE", "1");
        assert gti_cache_enabled() == True;
        _set_env("JAC_GTI_CACHE", "0");
        assert gti_cache_enabled() == False;
    } finally {
        _set_env("JAC_GTI_CACHE", prev);
    }
}
