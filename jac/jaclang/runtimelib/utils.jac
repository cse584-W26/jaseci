import os;
import platform;
import from collections.abc { Callable }
import from functools { lru_cache }
import from pathlib { Path }
import from uuid { UUID }
import type from jaclang.jac0core.constructs { NodeArchetype }

def collect_node_connections(
    current_node: NodeArchetype, visited_nodes: set, connections: set, edge_ids: set
) -> None;

def traverse_graph(
    nd: NodeArchetype,
    cur_depth: int,
    depth: int,
    edge_type: list[str],
    traverse: bool,
    connections: list,
    node_depths: dict[(NodeArchetype, int)],
    visited_nodes: list,
    queue: list[tuple[NodeArchetype, int]],
    bfs: bool,
    dfs: Callable,
    node_limit: int,
    edge_limit: int
) -> None;

def storage_key(id: UUID) -> str {
    return f"anchor:{str(id)}";
}

def to_uuid(id: (UUID | str)) -> UUID {
    if isinstance(id, UUID) {
        return id;
    }
    return UUID(str(id));
}


def projection_cfg -> dict[str, set[str]] {
    raw = os.environ.get("JAC_PROJECTION", "");
    out: dict[str, set[str]] = {};
    for part in raw.split(";") {
        if ":" not in part {
            continue;
        }
        (tname, _, flist) = part.partition(":");
        fields = {
            f.strip()
            for f in flist.split(",")
            if f.strip()
        };
        if tname.strip() and fields {
            out[tname.strip()] = fields;
        }
    }
    return out;
}


def order_pushdown_cfg(node_type: (str | None)) -> (tuple | None) {
    if node_type is None {
        return None;
    }
    raw = os.environ.get("JAC_ORDER_PUSHDOWN");
    if not raw {
        return None;
    }
    parts = raw.split(":");
    if len(parts) not in (3, 4) or not parts[0] or not parts[1] {
        raise ValueError(
            "JAC_ORDER_PUSHDOWN malformed " f"(want 'Type:field:asc|desc[:N]'): {raw!r}"
        );
    }
    direction = parts[2].strip().lower();
    if direction not in ("asc", "desc") {
        raise ValueError(
            f"JAC_ORDER_PUSHDOWN malformed direction (want 'asc'/'desc'): {raw!r}"
        );
    }
    limit: (int | None) = None;
    if len(parts) == 4 {
        try {
            limit = int(parts[3]);
        } except ValueError {
            raise ValueError(
                f"JAC_ORDER_PUSHDOWN malformed limit (want positive int): {raw!r}"
            );
        }
        if limit <= 0 {
            raise ValueError(
                f"JAC_ORDER_PUSHDOWN malformed limit (want positive int): {raw!r}"
            );
        }
    }
    if parts[0] != node_type {
        return None;
    }
    return (parts[0], parts[1], direction.upper(), limit);
}


@lru_cache(maxsize=1)
def fast_build_enabled -> bool {
    env = os.environ.get("JAC_FAST_BUILD");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    return False;
}


def leaf_materialize_cfg -> set[str] {
    raw = os.environ.get("JAC_LEAF_MATERIALIZE");
    if not raw {
        return set();
    }
    return {
        t.strip()
        for t in raw.split(",")
        if t.strip()
    };
}


def read_only_enabled -> bool {
    env = os.environ.get("JAC_READ_ONLY");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    try {
        import from jaclang.project.config { get_config }
        cfg = get_config();
        return cfg is not None and cfg.run.read_only;
    } except Exception {
        return False;
    }
}


def _parse_ro_walkers -> frozenset {
    raw = os.environ.get("JAC_RO_WALKERS", "");
    return frozenset(
        t.strip()
        for t in raw.split(",")
        if t.strip()
    );
}


glob RO_WALKERS: frozenset = _parse_ro_walkers();


def request_read_only -> bool {
    if read_only_enabled() {
        return True;
    }
    if not RO_WALKERS {
        return False;
    }
    try {
        import from jaclang { JacRuntimeInterface as Jac }
        ctx = Jac.get_context();
        return bool(ctx.__dict__.get('_request_read_only', False));
    } except Exception {
        return False;
    }
}


def lean_response_enabled -> bool {
    env = os.environ.get("JAC_API_LEAN_RESPONSE");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    try {
        import from jaclang.project.config { get_config }
        cfg = get_config();
        return cfg is not None and cfg.run.api_lean_response;
    } except Exception {
        return False;
    }
}


def gti_cache_enabled -> bool {
    env = os.environ.get("JAC_GTI_CACHE");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    try {
        import from jaclang.project.config { get_config }
        cfg = get_config();
        return cfg is not None and cfg.run.gti_cache;
    } except Exception {
        return False;
    }
}


def read_autocommit_enabled -> bool {
    env = os.environ.get("JAC_READ_AUTOCOMMIT");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    return True;
}


def compiled_serializer_enabled -> bool {
    env = os.environ.get("JAC_COMPILED_SERIALIZER");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    return False;
}


def orjson_response_enabled -> bool {
    env = os.environ.get("JAC_ORJSON_RESPONSE") or os.environ.get("JAC_ORJSON");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    return False;
}


def lazy_hydration_enabled -> bool {
    env = os.environ.get("JAC_LAZY_HYDRATION");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    return False;
}


def mem_pool_enabled -> bool {
    env = os.environ.get("JAC_MEM_POOL");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    return False;
}


def release_arch(raw: str) -> str {
    m = raw.strip().lower();
    if m in ("arm64", "aarch64") {
        return "aarch64";
    }
    if m in ("amd64", "x86_64") {
        return "x86_64";
    }
    return m;
}


def host_arch -> str {
    return release_arch(platform.machine());
}


def triple_arch(triple: str) -> str {
    if "aarch64" in triple.lower() or "arm64" in triple.lower() {
        return "aarch64";
    }
    return "x86_64";
}

def get_name(target_path: (str | None) = None) -> (str | None);

def get_db_path(base_path: str, target_path: (str | None) = None) -> (str | None);
