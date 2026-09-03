import logging;
import os;
import from typing { Any }
import from uuid { UUID }
import from jaclang.jac0core.archetype { Anchor, EdgeAnchor, NodeAnchor }
import from jaclang.jac0core.graph_query { GraphQuery, QHop, QPred }
import from jaclang.runtimelib.session { Session }
import from jaclang.runtimelib.sqlcompile { compile_query }

glob logger = logging.getLogger(__name__),
     __all__ = [
         'resolve_query',
         'resolve_query_edges',
         'resolve_query_prefix',
         'prefetch_adjacency',
         'hydrate_projected'
     ],
     # T3: JAC_LOOP_PREFETCH=1 arms the compiler-emitted `jadj_prefetch` hint
     # (one adjacency statement per loop LEVEL instead of one per node) and
     # the per-request memo it fills. Default off = stock behaviour, and the
     # hint call itself becomes a no-op, so nothing changes for any walker.
     LOOP_PREFETCH: bool = os.environ.get(
         'JAC_LOOP_PREFETCH', ''
     ).strip().lower() in ('1', 'true', 'yes', 'on');

# JAC_PREFETCH_DEBUG=1: one stderr line per hint telling you whether it filled
# the memo and why not, plus one per memo miss. This is T3's runnable check -
# a hint that silently does nothing looks exactly like a hint that works.
glob PREFETCH_DEBUG: bool = bool(os.environ.get('JAC_PREFETCH_DEBUG', '').strip());

# T6: JAC_PROJECT_HYDRATE=0 disarms the compiler-stamped `_proj` keyword on
# jobj/jobj_many (mirror-column hydration in read-only walkers); default ON.
# JAC_PROJECT_DEBUG=1 prints one PROJECT-RT line per projected batch.
glob PROJECT_HYDRATE: bool = os.environ.get(
    'JAC_PROJECT_HYDRATE', '1'
).strip().lower() not in ('0', 'false', 'no', 'off');
glob PROJECT_DEBUG: bool = bool(os.environ.get('JAC_PROJECT_DEBUG', '').strip());


def _pf_dbg(msg: str) -> None;


def _origin_anchors(q: GraphQuery) -> list[Anchor];


def _sql_pairs(
    mem: Session, origin_ids: list[UUID], q: GraphQuery, upto: int
) -> list[tuple[(UUID | None), (UUID | None)]];


def _edge_pair_for(e: EdgeAnchor, cur: Anchor, hop: QHop) -> (Anchor | None);


def _walk_memory(
    origins: list[Anchor], q: GraphQuery, upto: int
) -> list[tuple[Anchor, (EdgeAnchor | None)]];


def _hop_matches_node(anchor: Anchor, hop: QHop) -> bool;


def resolve_query_prefix(mem: Session, q: GraphQuery, upto: int) -> list[UUID];


def _acl_gated -> bool;


def _acl_read_ok(anchor: Anchor) -> bool;


def _prefetch_acl_roots(mem: Session, anchors: list[Anchor]) -> None;


def _try_stream_fused(
    mem: Session, q: GraphQuery, use_pipe: bool = True
) -> (list[Anchor] | None);


def _try_stream(
    mem: Session, q: GraphQuery, ids: list[UUID], local: dict[UUID, Anchor]
) -> (list[Anchor] | None);


def _adj_memo(mem: Session) -> (dict | None);


def _memo_key(q: GraphQuery) -> (tuple | None);


def _memo_pairs(
    mem: Session, q: GraphQuery
) -> (tuple[list[tuple[(UUID | None), (UUID | None)]], dict[UUID, Anchor]] | None);


def prefetch_adjacency(
    mem: Session,
    origins: list,
    dir: int,
    edge_type: any = None,
    node_type: any = None
) -> None;


def hydrate_projected(
    mem: Session, cls: type, ids: list[UUID], fields: tuple
) -> tuple;


def resolve_query(mem: Session, q: GraphQuery) -> list[Anchor];


def resolve_query_edges(mem: Session, q: GraphQuery) -> list[Anchor];
