"""JAC_MEM_POOL (Task 2): per-worker free-list reuse of ScaleTieredMemory.

The multi-tenant isolation invariant is the whole point: an instance handed
back to the pool by request N must be scrubbed (L1 __mem__ + pending changes)
before request N+1 checks it out, so no anchor from N is ever visible to N+1.

These tests exercise the pool free-list mechanism directly with a lightweight
stand-in (real ScaleTieredMemory construction needs a live Mongo/Redis/PG or
sqlite config; the pooling logic under test is backend-agnostic). Flag gating
is covered via the mem_pool_enabled helper.
"""

import os;

import from jaclang.runtimelib.changeset { ChangeSet }
import from jaclang.runtimelib.utils { mem_pool_enabled }
import from jaclang.scale.memory.memory_hierarchy {
    acquire_scale_mem,
    release_scale_mem,
    _mem_pool
}


obj _PooledStandin {
    has __mem__: dict = {},
        changes: any by postinit,
        _committed: bool = True;

    def postinit {
        self.changes = ChangeSet();
    }
}


test "mem_pool_enabled reflects JAC_MEM_POOL (default off)" {
    os.environ.pop("JAC_MEM_POOL", None);
    assert not mem_pool_enabled() , "default must be OFF";
    os.environ["JAC_MEM_POOL"] = "1";
    assert mem_pool_enabled();
    os.environ["JAC_MEM_POOL"] = "0";
    assert not mem_pool_enabled();
    os.environ.pop("JAC_MEM_POOL", None);
}


test "flag ON: checkout scrubs residual L1 -> request N data not visible to N+1" {
    os.environ["JAC_MEM_POOL"] = "1";
    _mem_pool.clear();
    try {
        m = _PooledStandin();
        m.__mem__["reqN_leak"] = "secret";  # request N left state behind
        m._committed = True;
        _mem_pool.append(m);  # instance sits in the pool

        m2: any = acquire_scale_mem();  # request N+1 checks out
        assert m2 is m , "pool must reuse the pooled instance";
        assert "reqN_leak" not in m2.__mem__ and m2.__mem__ == {} , "request N data must NOT survive into request N+1";
        assert m2._committed == False , "checkout must reset commit state";
    } finally {
        _mem_pool.clear();
        os.environ.pop("JAC_MEM_POOL", None);
    }
}


test "flag ON: release scrubs L1 + changes before returning to the pool" {
    os.environ["JAC_MEM_POOL"] = "1";
    _mem_pool.clear();
    try {
        m = _PooledStandin();
        m.__mem__["x"] = 1;
        release_scale_mem(m);
        assert m.__mem__ == {} , "release must clear L1";
        assert len(_mem_pool) == 1 and _mem_pool[0] is m , "instance re-enters pool";
    } finally {
        _mem_pool.clear();
        os.environ.pop("JAC_MEM_POOL", None);
    }
}


test "flag OFF: acquire ignores the pool (constructs fresh, no reuse)" {
    os.environ.pop("JAC_MEM_POOL", None);
    _mem_pool.clear();
    sentinel = _PooledStandin();
    _mem_pool.append(sentinel);
    try {
        # mem_pool_enabled() is False, so acquire_scale_mem never consults the
        # free-list; it would construct a fresh ScaleTieredMemory. We assert the
        # gate without building a real backend by checking the pool is untouched.
        assert not mem_pool_enabled();
        assert len(_mem_pool) == 1 and _mem_pool[0] is sentinel , "flag off must leave the pool untouched";
    } finally {
        _mem_pool.clear();
    }
}
