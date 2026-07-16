"""MongoBackend projection pushdown (spec Engine specifics, Mongo side).

execute_plan with plan.projection set must fetch a native-projected document
and build a slim marked anchor; without projection the full _load_anchor path
stays byte-identical. Requires Docker (testcontainers), same as the other
mongo suites.
"""

import atexit;
import from uuid { UUID }
import from pymongo { MongoClient }
import from testcontainers.mongodb { MongoDbContainer }

import from jaclang.jac0core.archetype { Root }
import from jaclang.runtimelib.query_plan { QueryPlan }
import from jaclang.scale.memory.memory_hierarchy { MongoBackend }

glob _shared: dict = {};


obj _ProjTweet(Root) {
    has content: str = "",
        created_at: str = "",
        likes: list[str] = [];
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
    client.drop_database("jac_test_proj");
    be = MongoBackend(mongo_url=uri, db_name="jac_test_proj");
    t = _ProjTweet(content="hello", created_at="2026-01-01", likes=["u1"]);
    a = t.__jac__;
    a.persistent = True;
    be._write_to_db(a);
    return (be, a);
}


test "mongo capabilities include projection" {
    (client, uri) = _get_mongo();
    be = MongoBackend(mongo_url=uri, db_name="jac_test_proj");
    assert 'projection' in be.capabilities();
    be.close();
}


test "mongo execute_plan with projection returns slim marked anchor" {
    (be, a) = _seeded_backend();
    plan = QueryPlan(
        id_in={a.id}, node_type_final="_ProjTweet", projection={"content"}
    );
    res = list(be.execute_plan(plan));
    assert len(res) == 1;
    assert res[0].id == a.id;
    assert res[0]._projected_fields == {"content"};
    assert res[0].archetype.content == "hello";
    assert res[0].edges == [];
    assert be.projection_count == 1;
    ok = False;
    try {
        _ = res[0].archetype.likes;
    } except AttributeError {
        ok = True;
    }
    assert ok , "unprojected factory field must be unset on slim anchor";
    be.close();
}


test "mongo execute_plan without projection unchanged full anchor" {
    (be, a) = _seeded_backend();
    plan = QueryPlan(id_in={a.id}, node_type_final="_ProjTweet");
    res = list(be.execute_plan(plan));
    assert len(res) == 1;
    assert res[0]?._projected_fields is None;
    assert res[0].archetype.likes == ["u1"];
    assert be.projection_count == 0;
    be.close();
}
