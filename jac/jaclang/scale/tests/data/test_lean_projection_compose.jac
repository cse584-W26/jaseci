"""Coverage gap: `JAC_API_LEAN_RESPONSE` and `JAC_PROJECTION` were tested in
fully disjoint suites -- neither ever ran with the other ON. This drives a
real walker endpoint (fixtures/lean_projection.jac) that reports a node
fetched through a genuine projection round-trip (PostgresRelBackend.
execute_plan, not a manually-stamped marker) with lean-response ON, and
asserts the composed response body: only the projected field survives
(post-T5: no leaked defaults for the un-projected `age` field), and the
lean envelope-unwrap + `_jac_*` stripping still apply on top.

Requires local Postgres (jactest_rel), same as test_postgres_rel_backend.jac.
"""

import os;
import from tempfile { mkdtemp }
import from jaclang.runtimelib.testing { JacTestClient }

glob FLAG = "JAC_API_LEAN_RESPONSE",
     FIXTURE = os.path.join(
         os.path.dirname(__file__), "fixtures", "lean_projection.jac"
     );


"""Set (truthy) or clear an env flag."""
def _set_flag(name: str, on: bool) {
    if on {
        os.environ[name] = "1";
    } elif name in os.environ {
        del os.environ[name];
    }
}


test "lean x projection: bare body carries only the projected field" {
    prior_lean: any = os.environ.get(FLAG);
    prior_proj: any = os.environ.pop('JAC_PROJECTION', None);
    prior_ro: any = os.environ.pop('JAC_READ_ONLY', None);
    _set_flag(FLAG, False);
    client = JacTestClient.from_file(FIXTURE, base_path=mkdtemp());
    client.register_user("pia", "secret123");
    client.login("pia", "secret123");
    try {
        # The composed configuration a real deployment would run with; the
        # walker fetches via execute_plan directly (see fixture docstring)
        # so these don't gate the fetch itself, but they must coexist
        # without changing the composed response shape.
        os.environ['JAC_PROJECTION'] = 'ProjItem:name';
        os.environ['JAC_READ_ONLY'] = '1';
        _set_flag(FLAG, True);

        body = client.post("/walker/projected_report", json={}).data;
        assert "result" not in body and "reports" not in body , (
            f"lean must unwrap the single-report envelope: {body}"
        );
        item = body["feed"][0];
        assert item == {"name": "ann"} , (
            f"only the projected field must survive, no leaked defaults: {item}"
        );
        for key in item.keys() {
            assert not key.startswith("_jac_") , (
                f"lean must drop _jac_* fields, found {key}: {item}"
            );
        }
    } finally {
        client.close();
        os.environ.pop('JAC_PROJECTION', None);
        os.environ.pop('JAC_READ_ONLY', None);
        if prior_proj is not None {
            os.environ['JAC_PROJECTION'] = prior_proj;
        }
        if prior_ro is not None {
            os.environ['JAC_READ_ONLY'] = prior_ro;
        }
        if prior_lean is None {
            os.environ.pop(FLAG, None);
        } else {
            os.environ[FLAG] = prior_lean;
        }
    }
}
