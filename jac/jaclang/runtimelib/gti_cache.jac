import os;
import threading;
import from collections { OrderedDict }
import from hashlib { blake2b }
import from jaclang.runtimelib.topology_index { TopologyIndex }

glob _cache: OrderedDict = OrderedDict(),
     _lock = threading.Lock(),
     _stats: dict[str, int] = {"hits": 0, "misses": 0, "evictions": 0};

glob DEFAULT_CAPACITY: int = 1024;


def cache_capacity -> int {
    env = os.environ.get("JAC_GTI_CACHE_SIZE");
    if env {
        try {
            cap = int(env);
            if cap > 0 {
                return cap;
            }
        } except ValueError { }
    }
    return DEFAULT_CAPACITY;
}


def decode_cached(blob: bytes) -> TopologyIndex {
    key = blake2b(blob, digest_size=16).digest();
    with _lock {
        cached = _cache.get(key);
        if cached is not None {
            _cache.move_to_end(key);
            _stats["hits"] += 1;
            return cached;
        }
    }
    idx = TopologyIndex.decode(blob);
    with _lock {
        existing = _cache.get(key);
        if existing is not None {
            _cache.move_to_end(key);
            _stats["hits"] += 1;
            return existing;
        }
        _stats["misses"] += 1;
        _cache[key] = idx;
        cap = cache_capacity();
        while len(_cache) > cap {
            _cache.popitem(last=False);
            _stats["evictions"] += 1;
        }
    }
    return idx;
}


def cache_stats -> dict[str, int] {
    with _lock {
        return dict(_stats);
    }
}


def clear_cache {
    with _lock {
        _cache.clear();
        for k in list(_stats.keys()) {
            _stats[k] = 0;
        }
    }
}
