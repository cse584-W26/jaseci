"""Tests for the default-off `api_lean_response` flag (env `JAC_API_LEAN_RESPONSE`).

When ON, the walker-API response path gets three changes:

  * `Serializer` api_mode drops the per-object `_jac_*` envelope fields.
  * `ExecutionManager._finalize_call_response` unwraps a single dict
    report to a bare body (no `result`/`reports` wrapper); multiple
    reports or a non-dict single report keep the envelope.
  * `_convert_transport_response_to_json_response` lifts a body-level
    `server_total_ms` into an `x-server-total-ms` response header.

Default OFF must be byte-identical to the current behavior.
"""

import json;
import os;
import from tempfile { mkdtemp }
import from tests.support { JAC_ROOT }
import from jaclang.runtimelib.testing { JacTestClient }
import from jaclang.runtimelib.transport { TransportResponse }
import from jaclang.scale.jserver.jfast_api {
    _convert_transport_response_to_json_response
}

glob FLAG = "JAC_API_LEAN_RESPONSE",
     FIXTURE = os.path.join(
         JAC_ROOT, "tests", "runtimelib", "fixtures", "lean_response.jac"
     );


"""Set (truthy) or clear the lean-response env flag."""
def _set_flag(on: bool) {
    if on {
        os.environ[FLAG] = "1";
    } elif FLAG in os.environ {
        del os.environ[FLAG];
    }
}


"""Restore the env flag to its pre-test value."""
def _restore_flag(prev: (str | None)) {
    if prev is None {
        if FLAG in os.environ {
            del os.environ[FLAG];
        }
    } else {
        os.environ[FLAG] = prev;
    }
}


"""Fresh client with a registered, logged-in user (flag OFF during setup)."""
def _client -> JacTestClient {
    client = JacTestClient.from_file(FIXTURE, base_path=mkdtemp());
    client.register_user("lena", "secret123");
    client.login("lena", "secret123");
    return client;
}


test "flag off: envelope and _jac_* fields unchanged" {
    prev = os.environ.get(FLAG);
    _set_flag(False);
    client = _client();
    try {
        data = client.post("/walker/one_report", json={}).data;
        assert "result" in data and "reports" in data , (
            f"flag off must keep the result/reports envelope: {data}"
        );
        payload = data["reports"][0];
        assert payload["server_total_ms"] == 12.5;
        item = payload["feed"][0];
        for key in ("_jac_type", "_jac_id", "_jac_archetype") {
            assert key in item , f"flag off must keep {key}: {item}";
        }
    } finally {
        client.close();
        _restore_flag(prev);
    }
}


test "flag on: single dict report unwraps bare with clean objects" {
    prev = os.environ.get(FLAG);
    _set_flag(False);
    client = _client();
    try {
        _set_flag(True);
        body = client.post("/walker/one_report", json={}).data;
        assert "result" not in body and "reports" not in body , (
            f"flag on must unwrap the single-report envelope: {body}"
        );
        # Timing stays in the body here: the header lift lives in the
        # scale/jserver JSON conversion, not in JacAPIServer.
        assert body["server_total_ms"] == 12.5;
        item = body["feed"][0];
        assert item["name"] == "solo";
        # Lean keeps `_jac_id` (identity for dedup/clients, per
        # feat(lean) 01b4d59eb) but still drops the type envelope.
        for key in ("_jac_type", "_jac_archetype") {
            assert key not in item , (
                f"flag on must drop {key}: {item}"
            );
        }
    } finally {
        client.close();
        _restore_flag(prev);
    }
}


test "flag on: multiple reports keep the envelope" {
    prev = os.environ.get(FLAG);
    _set_flag(False);
    client = _client();
    try {
        _set_flag(True);
        data = client.post("/walker/two_reports", json={}).data;
        assert "reports" in data , f"multi-report must keep envelope: {data}";
        assert data["reports"] == [{"first": 1}, {"second": 2}];
    } finally {
        client.close();
        _restore_flag(prev);
    }
}


test "flag on: non-dict single report keeps the envelope" {
    prev = os.environ.get(FLAG);
    _set_flag(False);
    client = _client();
    try {
        _set_flag(True);
        data = client.post("/walker/scalar_report", json={}).data;
        assert "reports" in data , f"non-dict report must keep envelope: {data}";
        assert data["reports"] == [42];
    } finally {
        client.close();
        _restore_flag(prev);
    }
}


test "flag on: server_total_ms lifts to x-server-total-ms header" {
    prev = os.environ.get(FLAG);
    try {
        _set_flag(True);
        tr = TransportResponse(ok=True, data={"server_total_ms": 12.3456, "feed": []});
        jr = _convert_transport_response_to_json_response(tr);
        assert jr.status_code == 200;
        assert jr.headers["x-server-total-ms"] == "12.346";
        assert json.loads(jr.body) == {"feed": []} , (
            f"lean body must be the bare report: {jr.body}"
        );
    } finally {
        _restore_flag(prev);
    }
}


test "flag off: JSON conversion keeps wrapper, no timing header" {
    prev = os.environ.get(FLAG);
    try {
        _set_flag(False);
        tr = TransportResponse(ok=True, data={"server_total_ms": 12.3456, "feed": []});
        jr = _convert_transport_response_to_json_response(tr);
        body = json.loads(jr.body);
        assert body["ok"] is True;
        assert body["data"] == {"server_total_ms": 12.3456, "feed": []};
        assert "x-server-total-ms" not in jr.headers , (
            "flag off must not add the timing header"
        );
    } finally {
        _restore_flag(prev);
    }
}
