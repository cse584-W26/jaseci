import os;
import platform;
import from collections.abc { Callable }
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
    if len(parts) != 3 or not parts[0] or not parts[1] {
        raise ValueError(
            f"JAC_ORDER_PUSHDOWN malformed (want 'Type:field:asc|desc'): {raw!r}"
        );
    }
    direction = parts[2].strip().lower();
    if direction not in ("asc", "desc") {
        raise ValueError(
            f"JAC_ORDER_PUSHDOWN malformed direction (want 'asc'/'desc'): {raw!r}"
        );
    }
    if parts[0] != node_type {
        return None;
    }
    return (parts[0], parts[1], direction.upper());
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


def read_autocommit_enabled -> bool {
    env = os.environ.get("JAC_READ_AUTOCOMMIT");
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    return True;
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
