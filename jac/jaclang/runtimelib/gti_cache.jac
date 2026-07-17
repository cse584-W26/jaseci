import os;
import threading;
import from uuid { UUID }
import from collections { OrderedDict }
import from hashlib { blake2b }
import from jaclang.runtimelib.topology_index { TopologyIndex }


def _resolve_capacity -> int {
    env = os.environ.get("JAC_GTI_CACHE_SIZE");
    if env is None or env == "" {
        return 1024;
    }
    try {
        cap = int(env);
    } except ValueError {
        raise ValueError(f"JAC_GTI_CACHE_SIZE must be a positive integer, got {env!r}");
    }
    if cap <= 0 {
        raise ValueError(f"JAC_GTI_CACHE_SIZE must be a positive integer, got {env!r}");
    }
    return cap;
}


glob _cache: OrderedDict = OrderedDict(),
     _lock = threading.Lock(),
     _stats: dict[str, int] = {"hits": 0, "misses": 0, "evictions": 0},
     _capacity: dict[str, int] = {"value": _resolve_capacity()};


def cache_capacity -> int {
    return _capacity["value"];
}


def decode_cached(root_id: UUID, blob: bytes) -> TopologyIndex {
    digest = blake2b(blob, digest_size=16).digest();
    with _lock {
        entry = _cache.get(root_id);
        if entry is not None and entry[0] == digest {
            _cache.move_to_end(root_id);
            _stats["hits"] += 1;
            return entry[1];
        }
    }
    idx = TopologyIndex.decode(blob);
    idx._frozen = True;
    with _lock {
        _stats["misses"] += 1;
        _cache[root_id] = (digest, idx);
        _cache.move_to_end(root_id);
        if len(_cache) > _capacity["value"] {
            _cache.popitem(last=False);
            _stats["evictions"] += 1;
        }
    }
    return idx;
}


def cache_stats -> dict[str, int] {
    with _lock {
        out = dict(_stats);
        out["size"] = len(_cache);
        return out;
    }
}


def clear_cache {
    cap = _resolve_capacity();
    with _lock {
        _capacity["value"] = cap;
        _cache.clear();
        for k in list(_stats.keys()) {
            _stats[k] = 0;
        }
    }
}
