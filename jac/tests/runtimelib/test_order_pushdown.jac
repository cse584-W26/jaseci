"""JAC_ORDER_PUSHDOWN: a per-stream sort+limit must be invisible to a capped
consumer. Two streams (own items, hub items) are merged, sorted desc and
sliced to K; with the flag off and with the flag on at N > K the consumer must
see byte-identical output. Runs against sqlite, so this exercises the
materialize-all FALLBACK (cold) and the resident fast path (warm) - the mongo
order_keys path is covered live, not here."""

import os;
import from pathlib { Path }
import from tempfile { TemporaryDirectory }
import from uuid { UUID }
import from jaclang.jac0core.archetype { EdgeAnchor, NodeAnchor, Root }
import from jaclang.jac0core.runtime { JacRuntime }
import from jaclang.runtimelib { query_planner }
import from jaclang.runtimelib.context { ExecutionContext }
import from jaclang.runtimelib.query_planner { _parse_order_pushdown }

node OItem {
    has stamp: str = "";
}

node OHub {
    has name: str = "";
}

edge OE {}


def _make_ctx(tmpdir: str) -> ExecutionContext {
    target = str(Path(tmpdir) / "order_app.jac");
    return ExecutionContext(base_path_dir=tmpdir, full_target_path=target);
}


def _link(ctx: ExecutionContext, src: NodeAnchor, tgt: NodeAnchor) -> None {
    e = EdgeAnchor(archetype=OE(), source=src, target=tgt, is_undirected=False);
    e.persistent = True;
    src.edges.append(e);
    tgt.edges.append(e);
    ctx.mem.put(tgt);
    ctx.mem.put(e);
}


"""root --> 8 OItem (even stamps); root --> OHub --> 8 OItem (odd stamps).

Stamps are UNIQUE and zero-padded: ties would make the slice boundary
nondeterministic (the sort is stable, so equal keys fall back to candidate
order, which differs between the pushed-down and stock plans). Interleaving
even/odd across the two streams forces the global top-K to draw from both.
"""
def _seed(ctx: ExecutionContext) -> UUID {
    ranch = Root().__jac__;
    ranch.persistent = True;
    ctx.mem.put(ranch);
    hub = OHub(name="h").__jac__;
    hub.persistent = True;
    _link(ctx, ranch, hub);
    for i in range(16) {
        item = OItem(stamp=f"s{i:02d}").__jac__;
        item.persistent = True;
        _link(ctx, ranch if i % 2 == 0 else hub, item);
    }
    return ranch.id;
}


def _stamps(nodes: list) -> list {
    return [
        t.stamp
        for t in nodes
    ];
}


"""The capped consumer: merge both streams, sort desc on the same field, take K."""
def _top_k(origin: any, k: int) -> list {
    merged = [origin-->[?:OItem]] + [origin-->[?:OHub]-->[?:OItem]];
    merged.sort(key=lambda (t: OItem) { t.stamp; }, reverse=True);
    return _stamps(merged[:k]);
}


test "capped consumer sees identical top-K with the limit pushed down" {
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

        # Flag off: the reference answer. Forced off rather than asserted off,
        # so the suite is also green under a boot that exports the flag.
        saved = query_planner.ORDER_PUSHDOWN;
        ctx2 = _make_ctx(td);
        JacRuntime.exec_ctx = ctx2;
        baseline: list;
        try {
            query_planner.ORDER_PUSHDOWN = None;
            origin = ctx2.mem.get(root_id).archetype;
            baseline = _top_k(origin, 3);
            assert baseline == ["s15", "s14", "s13"] , f"baseline = {baseline}";
        } finally {
            JacRuntime.exec_ctx = old;
            ctx2.close();
        }

        # Flag on, N=5 > K=3. The glob is parsed at import for speed, so the
        # test assigns it directly (module globs from impl files are reachable
        # as module attributes) instead of re-importing under a new env.
        ctx3 = _make_ctx(td);
        JacRuntime.exec_ctx = ctx3;
        try {
            query_planner.ORDER_PUSHDOWN = ("OItem", "stamp", True, 5);
            origin = ctx3.mem.get(root_id).archetype;
            # Cold: nothing resident, sqlite cannot sort -> materialize-all
            # fallback, sorted and capped in the planner.
            assert _top_k(origin, 3) == baseline;
            # Warm: same anchors resident -> keys read straight off the
            # archetypes, no storage call at all.
            assert _top_k(origin, 3) == baseline;

            # The documented truncation semantic: an UNCAPPED reader of the
            # named type gets N per stream, not the whole stream. This is also
            # the proof that the pushdown actually engaged above.
            assert len([origin-->[?:OItem]]) == 5;
            assert len([origin-->[?:OHub]-->[?:OItem]]) == 5;
        } finally {
            query_planner.ORDER_PUSHDOWN = None;
            JacRuntime.exec_ctx = old;
            ctx3.close();
        }

        # Sort-only spec (no limit): full streams, ordered.
        ctx4 = _make_ctx(td);
        JacRuntime.exec_ctx = ctx4;
        try {
            query_planner.ORDER_PUSHDOWN = ("OItem", "stamp", True, None);
            origin = ctx4.mem.get(root_id).archetype;
            stream = [origin-->[?:OItem]];
            # ('own' is a Jac keyword - do not name a local that.)
            ordered = _stamps(stream);
            assert len(ordered) == 8;
            assert ordered == sorted(ordered, reverse=True);
            assert _top_k(origin, 3) == baseline;

            # A type the spec does not name takes the stock path untouched.
            assert len([origin-->[?:OHub]]) == 1;
        } finally {
            query_planner.ORDER_PUSHDOWN = saved;
            JacRuntime.exec_ctx = old;
            ctx4.close();
        }
    }
}


test "malformed specs are rejected at parse time" {
    prev = os.environ.get('JAC_ORDER_PUSHDOWN');
    try {
        for bad in [
            'Tweet:created_at',
            'Tweet:created_at:sideways',
            'Tweet::desc',
            ':created_at:desc',
            'Tweet:created_at:desc:zero',
            'Tweet:created_at:desc:0',
            'Tweet:created_at:desc:-1',
            'Tweet:created_at:desc:20:extra'
        ] {
            os.environ['JAC_ORDER_PUSHDOWN'] = bad;
            blew = False;
            try {
                _parse_order_pushdown();
            } except ValueError {
                blew = True;
            }
            assert blew , f"{bad!r} should not parse";
        }
        os.environ['JAC_ORDER_PUSHDOWN'] = 'Tweet:created_at:desc';
        assert _parse_order_pushdown() == ("Tweet", "created_at", True, None);
        os.environ['JAC_ORDER_PUSHDOWN'] = ' Tweet : created_at : ASC : 20 ';
        assert _parse_order_pushdown() == ("Tweet", "created_at", False, 20);
        os.environ['JAC_ORDER_PUSHDOWN'] = '';
        assert _parse_order_pushdown() is None;
    } finally {
        if prev is None {
            os.environ.pop('JAC_ORDER_PUSHDOWN', None);
        } else {
            os.environ['JAC_ORDER_PUSHDOWN'] = prev;
        }
    }
}
