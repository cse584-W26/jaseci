"""End-to-end: value predicates in filter comprehensions are pushed down to
MongoDB server-side, not post-filtered in Python.

Exercises the production stack (ScaleTieredMemory with MongoDB L3 + Redis L2)
via real testcontainers. Proves the full chain: the compiler tags the filter
lambda with its lifted predicates -> the planner's `_try_field_pushdown` puts
them on the `QueryPlan.field_predicates` -> `MongoBackend.execute_plan`
translates them to a `data.archetype.<f>` filter -> MongoDB applies it
server-side. Runs in CI; skips locally when Docker is unavailable.
"""

import atexit;
import os;
import from pymongo { MongoClient }
import from testcontainers.mongodb { MongoDbContainer }
import from testcontainers.redis { RedisContainer }

import from jaclang { JacRuntimeInterface as Jac }
import from jaclang.jac0core.runtime { JacRuntime }
import from jaclang.runtimelib.context { ExecutionContext }
import from jaclang.project.config { JacConfig, set_config }
import from jaclang.scale.memory.memory_hierarchy { MongoBackend, RedisBackend, ScaleTieredMemory }

node Person {
    has name: str = "",
        age: int = 0;
}

edge Link {}

glob _shared: dict = {},
     recorded: list = [];


"""Lazily start a shared MongoDB container; return uri."""
def _get_mongo_uri -> str {
    if "mongo" not in _shared {
        c = MongoDbContainer("mongo:latest");
        c.start();
        _shared["mongo"] = c;
        _shared["mongo_uri"] = c.get_connection_url();
        atexit.register(c.stop);
    }
    return _shared["mongo_uri"];
}


"""Lazily start a shared Redis container; return url."""
def _get_redis_url -> str {
    if "redis" not in _shared {
        c = RedisContainer("redis:latest", port=6379);
        c.start();
        host = c.get_container_host_ip();
        port = c.get_exposed_port(6379);
        _shared["redis"] = c;
        _shared["redis_url"] = f"redis://{host}:{port}/0";
        atexit.register(c.stop);
    }
    return _shared["redis_url"];
}


"""Build a ScaleTieredMemory bound to the test containers (fresh DB)."""
def _make_scale_memory(db_name: str) -> tuple {
    mongo_uri = _get_mongo_uri();
    redis_url = _get_redis_url();
    MongoClient(mongo_uri).drop_database(db_name);
    mongo = MongoBackend(mongo_url=mongo_uri, db_name=db_name);
    redis_be = RedisBackend(redis_url=redis_url);
    mem = ScaleTieredMemory();
    mem.l2 = redis_be;
    mem.l3 = mongo;
    mem._cache_available = True;
    return (mem, mongo);
}


test "value predicate is pushed down to MongoDB server-side" {
    recorded.clear();
    cfg = JacConfig();
    cfg.run.topology_index = True;
    set_config(cfg);

    (mem, mongo) = _make_scale_memory("jac_fp_test");
    ctx = ExecutionContext();
    ctx.mem = mem;
    JacRuntime.set_context(ctx);
    try {
        r = root;
        Jac.save(r);
        for i in range(20) {
            r +>:Link:+> Person(name=f"p{i}", age=i);
        }
        Jac.save(r);
        mem.commit();

        # Capture the plan the Mongo backend actually receives, then run it.
        real_ep = mongo.execute_plan;
        def spy_ep(plan: any) {
            recorded.append(dict(plan.field_predicates));
            for a in real_ep(plan) {
                yield a;
            }
        }
        mongo.execute_plan = spy_ep;

        result = [r->:Link:->[?:Person, age > 5]];
        ages = sorted([n.age for n in result]);

        # 1. Correct results: ages 6..19 survive.
        assert ages == list(range(6, 20)) , f"ages={ages}";
        # 2. The planner pushed the lifted predicate down to the Mongo backend
        #    (only `_try_field_pushdown` adds `field_predicates` to the plan).
        assert {'age': {'$gt': 5}} in recorded , f"field_predicates not pushed: {recorded}";
        # 3. MongoDB honors that exact filter shape server-side.
        server_count = mongo.collection.count_documents(
            {
                'type': 'NodeAnchor',
                'arch_type': 'Person',
                'data.archetype.age': {'$gt': 5}
            }
        );
        assert server_count == 14 , f"server-side count={server_count}";
    } finally {
        mongo.client.drop_database("jac_fp_test");
        ctx.close();
        set_config(JacConfig());
    }
}
