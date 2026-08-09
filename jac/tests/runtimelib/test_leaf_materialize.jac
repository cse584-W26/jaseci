"""JAC_LEAF_MATERIALIZE: an expression read of a named node type returns
projected plain dicts instead of archetypes - but ONLY inside a request stamped
read-only. Runs against sqlite, which has no leaf_rows backend method, so this
covers the stock-materialize FALLBACK path; the mongo projected-row path is
covered live, not here."""

import os;
import from pathlib { Path }
import from tempfile { TemporaryDirectory }
import from uuid { UUID }
import from jaclang.jac0core.archetype { EdgeAnchor, NodeAnchor, Root }
import from jaclang.jac0core.runtime { JacRuntime }
import from jaclang.runtimelib { query_planner, utils }
import from jaclang.runtimelib.context { ExecutionContext }
import from jaclang.runtimelib.query_planner { _parse_leaf_types }

node LItem {
    has tag: str = "",
        votes: list[str] = [];
}

node LHub {
    has name: str = "";
}

edge LE {}


def _make_ctx(tmpdir: str) -> ExecutionContext {
    target = str(Path(tmpdir) / "leaf_app.jac");
    return ExecutionContext(base_path_dir=tmpdir, full_target_path=target);
}


def _link(ctx: ExecutionContext, src: NodeAnchor, tgt: NodeAnchor) -> None {
    e = EdgeAnchor(archetype=LE(), source=src, target=tgt, is_undirected=False);
    e.persistent = True;
    src.edges.append(e);
    tgt.edges.append(e);
    ctx.mem.put(tgt);
    ctx.mem.put(e);
}


"""root --> 4 LItem (even tags); root --> LHub --> 4 LItem (odd tags)."""
def _seed(ctx: ExecutionContext) -> UUID {
    ranch = Root().__jac__;
    ranch.persistent = True;
    ctx.mem.put(ranch);
    hub = LHub(name="h").__jac__;
    hub.persistent = True;
    _link(ctx, ranch, hub);
    for i in range(8) {
        item = LItem(tag=f"t{i:02d}", votes=[f"v{i}"]).__jac__;
        item.persistent = True;
        _link(ctx, ranch if i % 2 == 0 else hub, item);
    }
    return ranch.id;
}


test "leaf rows replace archetypes only under the read-only stamp" {
    with TemporaryDirectory() as td {
        old = JacRuntime.exec_ctx;
        root_id: UUID;
        ctx1 = _make_ctx(td);
        JacRuntime.exec_ctx = ctx1;
        try {
            root_id = _seed(ctx1);
            ctx1.mem.commit();
        } finally {
            JacRuntime.exec_ctx = old;
            ctx1.close();
        }

        # The globs are parsed at import for speed, so the test assigns them
        # directly (same trick as test_order_pushdown) instead of re-importing
        # the runtime under a new environment.
        saved_leaf = query_planner.LEAF_TYPES;
        saved_ro = utils.RO_WALKERS;
        baseline: list;

        # Flag off = stock: real LItem archetypes.
        ctx2 = _make_ctx(td);
        JacRuntime.exec_ctx = ctx2;
        try {
            query_planner.LEAF_TYPES = frozenset();
            origin = ctx2.mem.get(root_id).archetype;
            stock = [origin-->[?:LItem]];
            assert all(isinstance(x, LItem) for x in stock);
            baseline = [
                x.tag
                for x in stock
            ];
            assert sorted(baseline) == ["t00", "t02", "t04", "t06"] ,
                f"baseline={baseline}";
        } finally {
            JacRuntime.exec_ctx = old;
            ctx2.close();
        }

        # Flag on WITHOUT the read-only stamp: still archetypes. A write path
        # must never see a leaf row.
        ctx3 = _make_ctx(td);
        JacRuntime.exec_ctx = ctx3;
        try {
            query_planner.LEAF_TYPES = frozenset({"LItem"});
            utils.RO_WALKERS = frozenset({"ro_walker"});
            origin = ctx3.mem.get(root_id).archetype;
            unstamped = [origin-->[?:LItem]];
            assert all(isinstance(x, LItem) for x in unstamped);
            assert [x.tag for x in unstamped] == baseline;
        } finally {
            JacRuntime.exec_ctx = old;
            ctx3.close();
        }

        # Flag on WITH the stamp: projected dicts, same members, same order.
        ctx4 = _make_ctx(td);
        JacRuntime.exec_ctx = ctx4;
        try {
            ctx4.request_read_only = True;
            origin = ctx4.mem.get(root_id).archetype;
            # Cold: nothing resident and sqlite has no leaf_rows, so the rows
            # come from the stock-materialize fallback.
            cold = [origin-->[?:LItem]];
            assert all(isinstance(r, dict) for r in cold) , f"cold={cold}";
            assert [r['tag'] for r in cold] == baseline;
            assert all(set(r.keys()) == {"_jac_id", "tag", "votes"} for r in cold) ,
                f"keys={[sorted(r.keys()) for r in cold]}";
            assert len(UUID(cold[0]['_jac_id']).hex) == 32;
            # Non-scalar fields survive the projection intact.
            assert all(r['votes'] == [f"v{int(r['tag'][1:])}"] for r in cold);
            # Warm: the same anchors are resident now, so the rows are built
            # off the archetypes with no storage call. Same answer.
            assert [origin-->[?:LItem]] == cold;
            # Two hops: the hub is not a named type so it stays a real
            # archetype (and can still serve as the next origin); only the
            # final LItem hop goes leaf.
            hub = [origin-->[?:LHub]];
            assert isinstance(hub[0], LHub);
            odds = [
                r['tag']
                for r in [origin-->[?:LHub]-->[?:LItem]]
            ];
            assert sorted(odds) == ["t01", "t03", "t05", "t07"] , f"odds={odds}";
            # from_visit queries stay full-hydration even under the stamp: a
            # visit hands its nodes to walker abilities that may write them
            # (littleX like_tweet), so the gate must reject them. Asserted on
            # the gate itself - the same query with and without the flag.
            import from jaclang.jac0core.constant { EdgeDir }
            import from jaclang.jac0core.graph_query { GraphQuery, QHop }
            q = GraphQuery(origin, hops=[QHop(dir=EdgeDir.OUT.value, nd=LItem)]);
            assert query_planner._leaf_cls(q) is LItem;
            assert query_planner._leaf_cls(q.`visit()) is None;
        } finally {
            query_planner.LEAF_TYPES = saved_leaf;
            utils.RO_WALKERS = saved_ro;
            JacRuntime.exec_ctx = old;
            ctx4.close();
        }
    }
}


test "type list parses" {
    prev = os.environ.get('JAC_LEAF_MATERIALIZE');
    try {
        os.environ['JAC_LEAF_MATERIALIZE'] = '';
        assert _parse_leaf_types() == frozenset();
        os.environ['JAC_LEAF_MATERIALIZE'] = ' Tweet , Comment ,, ';
        assert _parse_leaf_types() == frozenset({"Tweet", "Comment"});
    } finally {
        if prev is None {
            os.environ.pop('JAC_LEAF_MATERIALIZE', None);
        } else {
            os.environ['JAC_LEAF_MATERIALIZE'] = prev;
        }
    }
}
