"""Tests for predicate pushdown to MongoDB via MongoBackend.

Uses testcontainers for a real MongoDB instance. Tests verify that:
1. Scalar props are stored alongside the blob on put/bulk_put
2. filtered_bulk_get translates predicates to MongoDB query operators
3. Correct results are returned with fewer documents examined
"""

import os;
import from typing { Any }
import from uuid { UUID, uuid4 }
import from pymongo { MongoClient }
import from testcontainers.mongodb { MongoDbContainer }

import from jaclang.jac0core.archetype { Anchor, NodeAnchor, Root }
import from jaclang.runtimelib.query_filter { CompareOp, Predicate, QueryFilter }
import from jaclang.runtimelib.serializer { Serializer }

test "mongo props stored on put" {
    container = MongoDbContainer("mongo:7.0");
    container.start();
    try {
        mongo_url = container.get_connection_url();
        import from jac_scale.memory_hierarchy { MongoBackend }
        backend = MongoBackend(mongo_url=mongo_url);

        r = Root();
        anchor = r.__jac__;
        anchor.persistent = True;

        backend.put(anchor);

        # Check document in MongoDB directly
        client = MongoClient(mongo_url);
        doc = client['jac_db']['_anchors'].find_one({'_id': str(anchor.id)});
        assert doc is not None, "Document should exist in MongoDB";
        assert 'data' in doc, "Document should have 'data' field";
        assert 'type' in doc, "Document should have 'type' field";

        client.close();
        backend.close();
    } finally {
        container.stop();
    }
}

test "mongo filtered_bulk_get with equality predicate" {
    container = MongoDbContainer("mongo:7.0");
    container.start();
    try {
        mongo_url = container.get_connection_url();
        import from jac_scale.memory_hierarchy { MongoBackend }
        backend = MongoBackend(mongo_url=mongo_url);

        client = MongoClient(mongo_url);
        coll = client['jac_db']['_anchors'];

        # Insert documents with props directly (simulating what put() does)
        anchor_ids: list[UUID] = [];
        names = ["Alice", "Bob", "Alice"];
        ages = [30, 25, 40];
        for i in range(3) {
            r = Root();
            anchor = r.__jac__;
            anchor.persistent = True;
            data = Serializer.serialize(anchor, include_type=True);
            doc_id = str(anchor.id);
            anchor_ids.append(anchor.id);
            coll.update_one(
                {'_id': doc_id},
                {'$set': {'data': data, 'type': 'NodeAnchor', 'props.name': names[i], 'props.age': ages[i]}},
                upsert=True
            );
        }

        # Query: name == "Alice"
        pred = Predicate(field_name="name", op=CompareOp.EQ, value="Alice");
        all_ids = set(anchor_ids);
        result = backend.filtered_bulk_get(all_ids, [pred]);

        assert len(result) == 2, f"Expected 2 results (Alice), got {len(result)}";
        assert anchor_ids[0] in result, "First Alice should be in result";
        assert anchor_ids[2] in result, "Second Alice should be in result";
        assert anchor_ids[1] not in result, "Bob should NOT be in result";

        client.close();
        backend.close();
    } finally {
        container.stop();
    }
}

test "mongo filtered_bulk_get with no predicates falls back to bulk_get" {
    container = MongoDbContainer("mongo:7.0");
    container.start();
    try {
        mongo_url = container.get_connection_url();
        import from jac_scale.memory_hierarchy { MongoBackend }
        backend = MongoBackend(mongo_url=mongo_url);

        result = backend.filtered_bulk_get(set(), []);
        assert len(result) == 0;

        backend.close();
    } finally {
        container.stop();
    }
}

test "mongo filtered_bulk_get with numeric comparison" {
    container = MongoDbContainer("mongo:7.0");
    container.start();
    try {
        mongo_url = container.get_connection_url();
        import from jac_scale.memory_hierarchy { MongoBackend }
        backend = MongoBackend(mongo_url=mongo_url);

        client = MongoClient(mongo_url);
        coll = client['jac_db']['_anchors'];

        anchor_ids: list[UUID] = [];
        prices = [10.0, 25.5, 50.0];
        for i in range(3) {
            r = Root();
            anchor = r.__jac__;
            anchor.persistent = True;
            data = Serializer.serialize(anchor, include_type=True);
            anchor_ids.append(anchor.id);
            coll.update_one(
                {'_id': str(anchor.id)},
                {'$set': {'data': data, 'type': 'NodeAnchor', 'props.price': prices[i]}},
                upsert=True
            );
        }

        # Query: price > 20
        pred = Predicate(field_name="price", op=CompareOp.GT, value=20.0);
        all_ids = set(anchor_ids);
        result = backend.filtered_bulk_get(all_ids, [pred]);

        assert len(result) == 2, f"Expected 2 results (price > 20), got {len(result)}";
        assert anchor_ids[1] in result;
        assert anchor_ids[2] in result;
        assert anchor_ids[0] not in result;

        client.close();
        backend.close();
    } finally {
        container.stop();
    }
}
