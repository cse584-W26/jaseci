import logging;
import os;
import threading;
import from collections.abc { Callable, Generator, Iterable }
import from typing { Any }
import from uuid { UUID }

import from jaclang.jac0core.archetype { Anchor, EdgeAnchor, NodeAnchor, Root }
import from jaclang.runtimelib.dbcatalog { DbKind, MAINTENANCE_DB, SCRATCH_PREFIX }
import from jaclang.runtimelib.pgembed { PgRuntime }
import from jaclang.runtimelib.exceptions { ReadOnlyWalkerError }
import from jaclang.runtimelib.store {
    AnchorRow,
    ConnInfo,
    PgStore,
    Store,
    TxnIsolation
}
import from jaclang.runtimelib.utils { request_read_only }

glob logger = logging.getLogger(__name__),
     MAX_RETRIES = 5,
     SCRATCH_ENV = 'JAC_DB_SCRATCH',
     RETENTION_ENV = 'JAC_DB_RETENTION_DAYS',
     __all__ = [
         'Session',
         'promotions_for',
         'conninfo_from_url',
         'shared_pg_data_dir',
         'project_db_name',
         'takeover_project',
         'mark_scratch_base',
         'scratch_requested',
         'scratch_lease',
         'drop_scratch_database',
         'retention_days_for',
         'runtime_for_base',
         'SCRATCH_ENV',
         'RETENTION_ENV'
     ];


class LazyEdges(list) {
    """A NodeAnchor's `edges` list that fetches its DB half on first read.

    Loading a node used to fetch its ENTIRE adjacency eagerly (PgStore.
    load_full's `string_agg` over anchors.src/dst) and turn every id into an
    EdgeAnchor stub, on every load, whether or not the walker ever traversed
    from that node. On TPC-C's Warehouse that is 100,064 edges rebuilt by
    100% of new_order/payment transactions, which only read `w_tax` off it.

    Why a list subclass and not an explicit `ensure_adjacency()` call at each
    traversal site: every remaining consumer of `.edges` lives in jac0core
    (JacGraph.disconnect, JacPersistence.save/destroy, NodeAnchor.remove_edge/
    __getstate__, osp_graph_sv.sv_register_hydrated) which this branch does
    not edit, and `NodeAnchor.is_populated()` is literally `'edges' in
    self.__dict__` - so the attribute must exist and must quack like a list
    from the moment the anchor is built. Subclassing `list` keeps
    isinstance(x, list), slicing, enumerate(), set(), pop() and friends
    working unchanged.

    Read-your-writes: `append` is the ONE list operation that does NOT
    trigger the fetch, because it is how JacGraph.build_edge attaches an
    edge created in this session. Those appended edges are held aside and
    re-appended after the DB half arrives, so a walker that creates an edge
    and then traverses from either endpoint sees it. Edges deleted in this
    session are dropped via Session._deleted at fill time.

    Snapshot consistency: the fetch goes through the session's own store,
    i.e. the same connection and open transaction as the rest of the
    request, so it can never see rows outside the caller's snapshot.
    """
    def __init__(self: LazyEdges, sess: Any, node_id: UUID) -> None {
        list.__init__(self);
        d = self.__dict__;
        d['_le_sess'] = sess;
        d['_le_id'] = node_id;
        d['_le_filled'] = False;
    }

    def _le_fill(self: LazyEdges) -> None {
        d = self.__dict__;
        if d['_le_filled'] {
            return;
        }
        # flip BEFORE fetching: _id_to_stub and the store call must not be
        # able to re-enter this method and fetch twice
        d['_le_filled'] = True;
        sess = d['_le_sess'];
        store = sess.store if sess is not None else None;
        if store is None {
            return;
        }
        import from jaclang.runtimelib.serializer { Serializer }
        # edges attached in THIS session (build_edge appends without
        # filling); they win over the DB row for the same id
        pending = list.copy(self);
        have: set = set(e.id for e in pending);
        stubs: list = [];
        for eid in store.load_adjacency(d['_le_id']) {
            if eid in have or eid in sess._deleted {
                continue;
            }
            have.add(eid);
            if (stub := Serializer._id_to_stub(EdgeAnchor, str(eid))) is not None
                and isinstance(stub, EdgeAnchor) {
                stubs.append(stub);
            }
        }
        # stored adjacency first (seq order, as load_full used to yield it),
        # session-local attachments after
        list.clear(self);
        list.extend(self, stubs + pending);
    }

    # --- read surface: every one of these fills first --------------------
    # `append` is deliberately absent (see class docstring).
    def __iter__(self: LazyEdges) -> Any {
        self._le_fill();
        return list.__iter__(self);
    }

    def __len__(self: LazyEdges) -> int {
        self._le_fill();
        return list.__len__(self);
    }

    def __getitem__(self: LazyEdges, k: Any) -> Any {
        self._le_fill();
        return list.__getitem__(self, k);
    }

    def __contains__(self: LazyEdges, v: Any) -> bool {
        self._le_fill();
        return list.__contains__(self, v);
    }

    def __reversed__(self: LazyEdges) -> Any {
        self._le_fill();
        return list.__reversed__(self);
    }

    def __eq__(self: LazyEdges, other: Any) -> Any {
        self._le_fill();
        return list.__eq__(self, other);
    }

    def __ne__(self: LazyEdges, other: Any) -> Any {
        self._le_fill();
        return list.__ne__(self, other);
    }

    def __repr__(self: LazyEdges) -> str {
        if not self.__dict__['_le_filled'] {
            return '[<lazy adjacency, not fetched>]';
        }
        return list.__repr__(self);
    }

    def __setitem__(self: LazyEdges, k: Any, v: Any) -> None {
        self._le_fill();
        list.__setitem__(self, k, v);
    }

    def __delitem__(self: LazyEdges, k: Any) -> None {
        self._le_fill();
        list.__delitem__(self, k);
    }

    def __add__(self: LazyEdges, other: Any) -> Any {
        self._le_fill();
        return list.__add__(self, other);
    }

    def __iadd__(self: LazyEdges, other: Any) -> Any {
        self._le_fill();
        return list.__iadd__(self, other);
    }

    def __mul__(self: LazyEdges, n: Any) -> Any {
        self._le_fill();
        return list.__mul__(self, n);
    }

    def pop(self: LazyEdges, i: int = -1) -> Any {
        self._le_fill();
        return list.pop(self, i);
    }

    def remove(self: LazyEdges, v: Any) -> None {
        self._le_fill();
        list.remove(self, v);
    }

    def insert(self: LazyEdges, i: int, v: Any) -> None {
        self._le_fill();
        list.insert(self, i, v);
    }

    def index(self: LazyEdges, *a: Any) -> int {
        self._le_fill();
        return list.index(self, *a);
    }

    def count(self: LazyEdges, v: Any) -> int {
        self._le_fill();
        return list.count(self, v);
    }

    def sort(self: LazyEdges, **kw: Any) -> None {
        self._le_fill();
        list.sort(self, **kw);
    }

    def reverse(self: LazyEdges) -> None {
        self._le_fill();
        list.reverse(self);
    }

    def copy(self: LazyEdges) -> list {
        self._le_fill();
        return list.copy(self);
    }

    def clear(self: LazyEdges) -> None {
        # a clear() means "no edges", so the pending fetch is moot - mark it
        # done rather than fetching a list we are about to throw away
        self.__dict__['_le_filled'] = True;
        list.clear(self);
    }

    def extend(self: LazyEdges, it: Any) -> None {
        # same contract as append: attachment, not observation
        list.extend(self, it);
    }
}


obj ScratchLease {
    has database: str,
        reset: bool = False;
}


obj RuntimeLease {
    has runtime: PgRuntime,
        reset: bool = False;
}


obj ScratchState {
    has database: str,
        base_path: str;
}


def promotions_for(base_path: (str | None)) -> dict[str, list[str]];
def shared_pg_data_dir -> str;
def project_db_name(base_path: str, target_path: (str | None)) -> str;
def conninfo_from_url(url: str) -> ConnInfo;
def takeover_project(base_path: str, target_path: (str | None) = None) -> int;
def mark_scratch_base(base_path: str) -> None;
def scratch_requested(base_path: (str | None)) -> bool;
def scratch_lease(base_path: str) -> ScratchLease;
def drop_scratch_database -> None;
def retention_days_for(base_path: (str | None)) -> int;
def runtime_for_base(base_path: str, target_path: (str | None) = None) -> RuntimeLease;


obj Session {
    has store: (Store | None) = None,
        base_path: (str | None) = None,
        target_path: (str | None) = None,
        __mem__: dict[UUID, Anchor] postinit,
        _dirty: dict[UUID, None] postinit,
        _deleted: set[UUID] postinit,
        _flushed_hash: dict[UUID, int] postinit,
        _clean: set[UUID] postinit,
        _on_commit: list[Callable] postinit,
        _txn_changed: set[UUID] postinit,
        _runtime: (Any | None) postinit,
        _lock: threading.RLock postinit,
        _fetch_count: int postinit,
        _active_units: int postinit,
        _flushing: (int | None) postinit,
        _read_scopes: int postinit,
        _snapshot_reads: set[UUID] postinit;

    def postinit -> None;
    def data_location -> (str | None);
    def is_available -> bool;
    def get(id: UUID) -> (Anchor | None);
    def put(anchor: Anchor) -> None;
    def mark_dirty(anchor: Anchor) -> None;
    def delete(id: UUID) -> None;
    def close -> None;
    def `has(id: UUID) -> bool;
    def query(
        filter: (Callable[[Anchor], bool] | None) = None
    ) -> Generator[Anchor, None, None];

    def get_roots -> Generator[Root, None, None];
    def find(
        ids: (UUID | Iterable[UUID]), filter: (Callable[[Anchor], Anchor] | None) = None
    ) -> Generator[Anchor, None, None];

    def find_one(
        ids: (UUID | Iterable[UUID]), filter: (Callable[[Anchor], Anchor] | None) = None
    ) -> (Anchor | None);

    def commit(anchor: (Anchor | None) = None) -> None;
    def abort -> None;
    def get_mem -> dict[UUID, Anchor];
    def batch_get(ids: list[UUID]) -> dict[UUID, Anchor];
    def quarantine_ref(referrer: (Anchor | None), stub: Anchor) -> None;
    def is_recoverable_quarantine(id: UUID) -> bool;
    async def aget(id: UUID) -> (Anchor | None);
    async def aput(anchor: Anchor) -> None;
    async def adelete(id: UUID) -> None;
    async def ahas(id: UUID) -> bool;
    async def acommit(anchor: (Anchor | None) = None) -> None;
    def run_request(body: Callable) -> Any;
    def reset_fetch_count -> None;
    def get_fetch_count -> int;
    def unit_enter -> None;
    def unit_exit -> None;
    def read_scope_enter -> None;
    def read_scope_exit -> None;
    def on_commit(callback: Callable) -> None;
    def flush(full: bool = False) -> None;
    def _flush_locked(full: bool) -> None;
    def read_barrier -> None;
    def _recover_conflict -> None;
    def _ensure_txn -> None;
    def _txn_isolation -> TxnIsolation;
    def _drop_snapshot_reads -> None;
    def _materialize(
        row: AnchorRow, edge_ids: (list[UUID] | None) = None
    ) -> (Anchor | None);

    def _serialize(anchor: Anchor) -> AnchorRow;
    def _fire_on_commit -> None;
    def _evict_uncommitted -> None;
}
