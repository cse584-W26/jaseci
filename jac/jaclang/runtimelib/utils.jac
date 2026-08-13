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


def host_os -> str {
    sysname = platform.system().strip().lower();
    if sysname == "darwin" {
        return "macos";
    }
    return sysname;
}


def triple_arch(triple: str) -> str {
    if "aarch64" in triple.lower() or "arm64" in triple.lower() {
        return "aarch64";
    }
    return "x86_64";
}

def get_name(target_path: (str | None) = None) -> (str | None);

def get_db_path(base_path: str, target_path: (str | None) = None) -> (str | None);


def _parse_ro_walkers -> frozenset {
    # JAC_RO_WALKERS="load_feed,load_feed_chain": walkers declared read-only.
    # A request spawning one of them runs its store transaction in
    # SNAPSHOT_READ_ONLY isolation and skips the commit funnel; any write
    # attempt raises ReadOnlyWalkerError (fail loud, never silently drop).
    # Parsed once at boot. Empty/unset = feature off (stock).
    import os;
    raw = os.environ.get('JAC_RO_WALKERS', '');
    return frozenset(t.strip() for t in raw.split(',') if t.strip());
}


glob RO_WALKERS: frozenset = _parse_ro_walkers();


def request_read_only -> bool {
    # True only when this request was stamped read-only (walker name listed
    # in JAC_RO_WALKERS at spawn time). No global read-only mode on this
    # runtime. Outside a request context: False (treated as a write context).
    if not RO_WALKERS {
        return False;
    }
    try {
        import from jaclang { JacRuntimeInterface as Jac }
        return bool(Jac.get_context().request_read_only);
    } except Exception {
        return False;
    }
}
