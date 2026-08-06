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

def access_log_enabled -> bool {
    # JAC_ACCESS_LOG=0 silences the per-request console line. Default ON =
    # stock behavior. Resolved once at server boot (restart to change).
    import os;
    env_val = os.environ.get('JAC_ACCESS_LOG');
    if env_val is not None and env_val.strip() != '' {
        return env_val.strip().lower() not in ('0', 'false', 'no', 'off');
    }
    return True;
}

def lean_response_enabled -> bool {
    # JAC_API_LEAN_RESPONSE=1: walker responses drop the result echo and the
    # _jac_type/_jac_archetype envelope fields; a lone dict report is returned
    # as the bare response body. Default off = stock envelope. Env-only.
    import os;
    return os.environ.get('JAC_API_LEAN_RESPONSE', '').strip().lower()
        in ('1', 'true', 'yes', 'on');
}

def get_name(target_path: (str | None) = None) -> (str | None);

def get_db_path(base_path: str, target_path: (str | None) = None) -> (str | None);
