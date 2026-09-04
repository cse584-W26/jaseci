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
    # A read-only request runs its store transaction in SNAPSHOT_READ_ONLY
    # isolation and skips the commit funnel; any write attempt raises
    # ReadOnlyWalkerError (fail loud, never silently drop).
    # JAC_RO_WALKERS retired 0904: EffectPass stamps __jac_readonly__
    # (is2 parity 98/98, session0831), so this override list is now always
    # empty and request_read_only() below reads the stamp alone.
    raw = '';
    return frozenset(t.strip() for t in raw.split(',') if t.strip());
}


glob RO_WALKERS: frozenset = _parse_ro_walkers();


def request_read_only -> bool {
    # True only when this request was stamped read-only at spawn time -
    # either the walker's compiler-proved __jac_readonly__ stamp (EffectPass,
    # #26) or the JAC_RO_WALKERS env override list. No global read-only mode
    # on this runtime. Outside a request context: False (write context).
    # NOTE: no RO_WALKERS short-circuit here any more - the stamp path is
    # live even when the env list is empty.
    try {
        import from jaclang { JacRuntimeInterface as Jac }
        return bool(Jac.get_context().request_read_only);
    } except Exception {
        return False;
    }
}
