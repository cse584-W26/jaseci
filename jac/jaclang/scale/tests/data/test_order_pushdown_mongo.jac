"""MongoBackend order pushdown (Route A final-hop tail).

execute_plan with plan.order set must sort in Mongo BEFORE skip/limit, so a
slice reflects post-sort positions -- proving the sort ran server-side, not
incidentally. Also covers the shared order_pushdown_cfg env parser.
Requires Docker (testcontainers), same as the other mongo suites.
"""

import atexit;
import os;
import from uuid { UUID }
import from pymongo { MongoClient }
import from testcontainers.mongodb { MongoDbContainer }

import from jaclang.jac0core.archetype { Root }
import from jaclang.runtimelib.query_plan { QueryPlan }
import from jaclang.runtimelib.utils { order_pushdown_cfg }
import from jaclang.scale.memory.memory_hierarchy { MongoBackend }

glob _shared: dict = {};


obj _OrdTweet(Root) {
    has content: str = "",
        created_at: str = "";
}


def _get_mongo -> tuple {
    if "mongo_client" not in _shared {
        container = MongoDbContainer("mongo:latest");
        container.start();
        uri = container.get_connection_url();
        _shared["mongo_container"] = container;
        _shared["mongo_uri"] = uri;
        _shared["mongo_client"] = MongoClient(uri);
        atexit.register(container.stop);
    }
    return (_shared["mongo_client"], _shared["mongo_uri"]);
}


def _seeded_backend -> tuple {
    (client, uri) = _get_mongo();
    client.drop_database("jac_test_order");
    be = MongoBackend(mongo_url=uri, db_name="jac_test_order");
    # Insertion order is deliberately scrambled vs sorted order, so a slice
    # that matched insertion order would give a different answer than a slice
    # that matched sort order -- that is what proves the DB did the sorting.
    ids: list = [];
    for ca in ["2026-01-03", "2026-01-01", "2026-01-05", "2026-01-02", "2026-01-04"] {
        t = _OrdTweet(content=ca, created_at=ca);
        a = t.__jac__;
        a.persistent = True;
        be._write_to_db(a);
        ids.append(a.id);
    }
    return (be, ids);
}


test "mongo capabilities include order_pushdown" {
    (client, uri) = _get_mongo();
    be = MongoBackend(mongo_url=uri, db_name="jac_test_order");
    assert 'order_pushdown' in be.capabilities();
    be.close();
}


test "order_pushdown_cfg parses JAC_ORDER_PUSHDOWN env" {
    prev = os.environ.get("JAC_ORDER_PUSHDOWN");
    os.environ["JAC_ORDER_PUSHDOWN"] = "_OrdTweet:created_at:desc";
    try {
        assert order_pushdown_cfg("_OrdTweet") == (
            "_OrdTweet",
            "created_at",
            "DESC",
            None
        );
        assert order_pushdown_cfg("Other") is None;
        os.environ["JAC_ORDER_PUSHDOWN"] = "_OrdTweet:created_at:desc:3";
        assert order_pushdown_cfg("_OrdTweet") == (
            "_OrdTweet",
            "created_at",
            "DESC",
            3
        );
    } finally {
        if prev is None {
            del os.environ["JAC_ORDER_PUSHDOWN"];
        } else {
            os.environ["JAC_ORDER_PUSHDOWN"] = prev;
        }
    }
}


test "mongo execute_plan sorts server-side before slicing" {
    (be, ids) = _seeded_backend();
    # desc sort by created_at -> [05, 04, 03, 02, 01]; slc[1:3] -> [04, 03].
    plan = QueryPlan(
        id_in=set(ids),
        node_type_final="_OrdTweet",
        order=("_OrdTweet", "created_at", "DESC"),
        slc=slice(1, 3)
    );
    res = list(be.execute_plan(plan));
    got = [r.archetype.created_at for r in res];
    assert got == ["2026-01-04", "2026-01-03"] , f"post-sort slice wrong: {got}";
    be.close();
}


test "mongo execute_plan without order unchanged" {
    (be, ids) = _seeded_backend();
    plan = QueryPlan(id_in=set(ids), node_type_final="_OrdTweet");
    res = list(be.execute_plan(plan));
    assert len(res) == 5;
    be.close();
}


# Seed two disjoint tweet streams (own + one followed/foreign source) with
# interleaved timestamps, like littleX load_feed's two dict streams.
def _two_stream_backend(n_per_stream: int) -> tuple {
    (client, uri) = _get_mongo();
    client.drop_database("jac_test_order2");
    be = MongoBackend(mongo_url=uri, db_name="jac_test_order2");
    own: list = [];
    followed: list = [];
    for i in range(n_per_stream) {
        a = _OrdTweet(
            content=f"own_{i}", created_at=f"2026-02-{(2 * i + 1):02d}"
        ).__jac__;
        a.persistent = True;
        be._write_to_db(a);
        own.append(a.id);
        b = _OrdTweet(
            content=f"fol_{i}", created_at=f"2026-02-{(2 * i + 2):02d}"
        ).__jac__;
        b.persistent = True;
        be._write_to_db(b);
        followed.append(b.id);
    }
    return (be, own, followed);
}


# The walker's role: fetch each stream through the plan path (order cfg
# picked up exactly as the resolver does), merge, dedup, sort desc, cap.
def _capped_feed(be: MongoBackend, own: list, followed: list, cap: int) -> list {
    ocfg = order_pushdown_cfg("_OrdTweet");
    seen: set = set();
    merged: list = [];
    for ids in (own, followed) {
        plan = QueryPlan(id_in=set(ids), node_type_final="_OrdTweet");
        if ocfg is not None {
            plan.order = ocfg;
        }
        for a in be.execute_plan(plan) {
            if a.id not in seen {
                seen.add(a.id);
                merged.append(a);
            }
        }
    }
    merged.sort(key=(lambda a: any : a.archetype.created_at), reverse=True);
    return [(a.archetype.created_at, a.archetype.content) for a in merged[:cap]];
}


test "capped two-stream feed: limit pushdown on == off, same set and order" {
    # 12 tweets per stream, cap 5: per-stream top-5 union (10 fetched) must
    # reproduce the exact top-5 the uncapped merge produces -- the soundness
    # contract from utils.order_pushdown_cfg, exercised end to end.
    (be, own, followed) = _two_stream_backend(12);
    prev = os.environ.pop("JAC_ORDER_PUSHDOWN", None);
    try {
        # flag OFF: no order, no limit -- full materialization + walker sort.
        baseline = _capped_feed(be, own, followed, 5);
        assert len(baseline) == 5;

        # flag ON with :N -- storage sorts and caps each stream at N=5.
        os.environ["JAC_ORDER_PUSHDOWN"] = "_OrdTweet:created_at:desc:5";
        pushed = _capped_feed(be, own, followed, 5);
        assert pushed == baseline , f"pushdown changed feed: {pushed} != {baseline}";

        # sort-only spec (no :N) must also agree -- uncapped reads unchanged.
        os.environ["JAC_ORDER_PUSHDOWN"] = "_OrdTweet:created_at:desc";
        sorted_only = _capped_feed(be, own, followed, 5);
        assert sorted_only == baseline;
    } finally {
        if prev is None {
            os.environ.pop("JAC_ORDER_PUSHDOWN", None);
        } else {
            os.environ["JAC_ORDER_PUSHDOWN"] = prev;
        }
    }
    be.close();
}


test "order limit does not override an explicit plan slice" {
    (be, ids) = _seeded_backend();
    # slice [1:3] with a stream cap of 1: the slice window must win (limit 1
    # would starve the skip), so result is identical to the no-cap slice test.
    plan = QueryPlan(
        id_in=set(ids),
        node_type_final="_OrdTweet",
        order=("_OrdTweet", "created_at", "DESC", 1),
        slc=slice(1, 3)
    );
    res = list(be.execute_plan(plan));
    got = [r.archetype.created_at for r in res];
    assert got == ["2026-01-04", "2026-01-03"] , f"slice clobbered by cap: {got}";
    be.close();
}


test "order limit caps sorted fetch when plan has no slice" {
    (be, ids) = _seeded_backend();
    plan = QueryPlan(
        id_in=set(ids),
        node_type_final="_OrdTweet",
        order=("_OrdTweet", "created_at", "DESC", 2)
    );
    res = list(be.execute_plan(plan));
    got = [r.archetype.created_at for r in res];
    assert got == ["2026-01-05", "2026-01-04"] , f"cap wrong: {got}";
    be.close();
}
