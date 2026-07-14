"""Unit tests for QueryPlan.projection and the JAC_PROJECTION declaration parser.

No database required. Covers: projection field default + needs() contribution
(spec Decision 1) and projection_cfg() env parsing (spec Decision 3.1).
"""

import os;
import from uuid { UUID }

import from jaclang.runtimelib.query_plan { QueryPlan }
import from jaclang.runtimelib.utils { projection_cfg }


test "plan_projection_default_none" {
    p = QueryPlan(id_in={UUID(int=1)});
    assert p.projection is None;
    assert 'projection' not in p.needs();
}

test "plan_projection_adds_need" {
    p = QueryPlan(
        id_in={UUID(int=1)},
        node_type_final="Tweet",
        projection={"content", "created_at"}
    );
    assert p.needs() == {'id_in', 'type_pushdown', 'projection'};
}

test "cfg_unset_empty" {
    os.environ.pop("JAC_PROJECTION", None);
    assert projection_cfg() == dict();
}

test "cfg_parses_types" {
    os.environ["JAC_PROJECTION"] = "Tweet:content,created_at;Profile:username";
    cfg = projection_cfg();
    assert cfg == {"Tweet": {"content", "created_at"}, "Profile": {"username"}};
    os.environ.pop("JAC_PROJECTION", None);
}

test "cfg_ignores_malformed" {
    os.environ["JAC_PROJECTION"] = "Tweet;:x;Bad:";
    assert projection_cfg() == dict();
    os.environ.pop("JAC_PROJECTION", None);
}
