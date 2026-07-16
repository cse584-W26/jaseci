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
        assert order_pushdown_cfg("_OrdTweet") == ("_OrdTweet", "created_at", "DESC");
        assert order_pushdown_cfg("Other") is None;
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
