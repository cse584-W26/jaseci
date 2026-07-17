"""GTI-cache e2e gate on the mongo backend: parity, engagement, freshness.

Drives `jac start` (backend=mongo, testcontainer) over real HTTP with a
two-user cross-root graph (alice follows bob), twice:

  * boot 1 -- JAC_GTI_CACHE=0: build the graph, capture the baseline counts
    and a rough per-request timing sample.
  * boot 2 -- JAC_GTI_CACHE=1, same mongo data: the same queries must return
    the baseline (parity), the server-side cache counters must move
    (engagement, via the gti_cache_probe walker), and a foreign-root write
    (bob's new tweet) must be visible on the next cached read (freshness --
    the content-addressed key changes with the blob).

Timing numbers are a smoke signal only (tiny graph, cross-boot comparison);
the citable A/B lives in the bench harness, not here. Idiom mirrors
test_postgres_e2e_integration.jac (subprocess `jac start`, requests, bearer
auth) with the testcontainer mongo from test_mongo_layer123.jac.
"""

import atexit;
import contextlib;
import gc;
import os;
import shutil;
import socket;
import subprocess;
import sys;
import time;
import requests;
import from pathlib { Path }
import from statistics { median }
import from typing { cast }
import from testcontainers.mongodb { MongoDbContainer }

glob FIXTURES_DIR = Path(cast(str, __file__)).parent / "fixtures",
     JAC_FILE = FIXTURES_DIR / "gti_cache_app.jac",
     _shared: dict = {};


def _get_mongo_uri -> str {
    if "mongo_uri" not in _shared {
        container = MongoDbContainer("mongo:latest");
        container.start();
        _shared["mongo_container"] = container;
        _shared["mongo_uri"] = container.get_connection_url();
        atexit.register(container.stop);
    }
    return cast(str, _shared["mongo_uri"]);
}


def _get_free_port -> int {
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s {
        s.bind(("", 0));
        return cast(int, s.getsockname()[1]);
    }
}


"""Unwrap the TransportResponse envelope (dict {ok,data} or [status, body])."""
def _extract(payload: any) -> any {
    body = payload;
    if isinstance(body, list) and len(body) == 2 {
        body = body[1];
    }
    if isinstance(body, dict) and "ok" in body and "data" in body {
        if body.get("ok") and body.get("data") is not None {
            return body["data"];
        }
    }
    return body;
}


"""Start `jac start` on `port` with the mongo backend; wait until it serves."""
def _start_server(port: int, gti_cache_on: bool) -> subprocess.Popen {
    jac_executable = Path(sys.executable).parent / "jac";
    cmd = [str(jac_executable), "start", str(JAC_FILE.name), "--port", str(port)];
    env = os.environ.copy();
    env["MONGODB_URI"] = _get_mongo_uri();
    env["JAC_SCALE_BACKEND"] = "mongodb";
    env["JAC_TOPOLOGY_INDEX"] = "1";
    env["JAC_CROSS_ROOT_RESOLVE"] = "1";
    env["JAC_GTI_CACHE"] = "1" if gti_cache_on else "0";
    env.pop("POSTGRESQL_URI", None);
    env.pop("REDIS_URL", None);
    server = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(FIXTURES_DIR),
        env=env
    );
    base_url = f"http://localhost:{port}";
    for _ in range(30) {
        if server.poll() is not None {
            (out, err) = server.communicate();
            raise RuntimeError(
                f"jac start exited early\nSTDOUT:\n{out}\nSTDERR:\n{err}"
            );
        }
        try {
            r = requests.get(f"{base_url}/healthz", timeout=1);
            if r.status_code == 200 {
                return server;
            }
        } except Exception {
            time.sleep(1);
        }
    }
    (out, err) = server.communicate(timeout=2);
    raise RuntimeError(f"jac start never became ready\nSTDOUT:\n{out}\nSTDERR:\n{err}");
}


def _stop_server(server: (subprocess.Popen | None)) {
    if server is not None {
        server.terminate();
        with contextlib.suppress(Exception) {
            server.wait(timeout=5);
        }
    }
    time.sleep(0.5);
    gc.collect();
}


"""Register (idempotent) + login `user`; return a bearer-auth header dict."""
def _login(base_url: str, user: str) -> dict {
    reg_body: dict = {
        "identities": [{"type": "username", "value": user}],
        "credential": {"type": "password", "password": "pass123e2e"}
    };
    reg = requests.post(f"{base_url}/user/register", json=reg_body, timeout=5);
    assert reg.status_code in (201, 400, 409) , (
        f"register failed: {reg.status_code} - {reg.text}"
    );
    login_body: dict = {
        "identity": {"type": "username", "value": user},
        "credential": {"type": "password", "password": "pass123e2e"}
    };
    res = requests.post(f"{base_url}/user/login", json=login_body, timeout=5);
    assert res.status_code == 200 , f"login failed: {res.status_code} - {res.text}";
    login_data = cast(dict[str, any], _extract(res.json()));
    return {"Authorization": f"Bearer {login_data['token']}"};
}


"""POST a walker and return its first report value."""
def _walk(base_url: str, auth: dict, name: str, body: dict) -> any {
    res = requests.post(
        f"{base_url}/walker/{name}", json=body, headers=auth, timeout=10
    );
    assert res.status_code == 200 , f"{name} failed: {res.status_code} - {res.text}";
    data = cast(dict[str, any], _extract(res.json()));
    reports = cast(list, data.get("reports") or []);
    return reports[0] if reports else None;
}


"""Median latency (ms) of `n` query_follow_chain requests."""
def _sample_ms(base_url: str, auth: dict, n: int) -> float {
    samples: list = [];
    for _ in range(n) {
        t0 = time.perf_counter();
        _walk(base_url, auth, "query_follow_chain", {});
        samples.append((time.perf_counter() - t0) * 1000.0);
    }
    return median(samples);
}


test "gti_cache on mongo: parity, server-side engagement, freshness" {
    if not JAC_FILE.exists() {
        raise FileNotFoundError(f"Missing fixture: {JAC_FILE}");
    }
    data_dir = FIXTURES_DIR / ".jac";
    if data_dir.exists() {
        shutil.rmtree(data_dir);
    }

    port = _get_free_port();
    base_url = f"http://localhost:{port}";
    server: (subprocess.Popen | None) = None;
    try {
        # --- boot 1: flag OFF -- build graph, capture baseline --------------
        server = _start_server(port, gti_cache_on=False);
        bob = _login(base_url, "gti_bob");
        bob_profile_id = _walk(
            base_url, bob, "setup_profile_only", {"username": "bob"}
        );
        _walk(base_url, bob, "post_tweet", {"content": "hello world"});

        alice = _login(base_url, "gti_alice");
        _walk(base_url, alice, "setup_profile_only", {"username": "alice"});
        _walk(base_url, alice, "follow_target", {"target_id": bob_profile_id});

        baseline = _walk(base_url, alice, "query_follow_chain", {});
        assert baseline == 1 , f"expected 1 tweet through follow chain: {baseline}";
        off_ms = _sample_ms(base_url, alice, 20);
        _stop_server(server);
        server = None;

        # --- boot 2: flag ON, same mongo data -------------------------------
        server = _start_server(port, gti_cache_on=True);
        bob = _login(base_url, "gti_bob");
        alice = _login(base_url, "gti_alice");

        r1 = _walk(base_url, alice, "query_follow_chain", {});
        assert r1 == baseline , f"cache-on parity broke on mongo: {r1} != {baseline}";
        r2 = _walk(base_url, alice, "query_follow_chain", {});
        assert r2 == baseline , f"warm-cache parity broke on mongo: {r2}";

        stats = cast(dict[str, any], _walk(base_url, alice, "gti_cache_probe", {}));
        assert stats["misses"] >= 1 , f"cache never engaged server-side: {stats}";
        assert stats["hits"] >= 1 , f"repeat read never hit server-side: {stats}";

        on_ms = _sample_ms(base_url, alice, 20);
        # Smoke signal only -- tiny graph, cross-boot; no threshold assert.
        print(
            f"gti_cache smoke: off={off_ms:.2f}ms on={on_ms:.2f}ms "
            f"(UNVERIFIED, non-citable)"
        );

        # Freshness: bob's new tweet rewrites bob's root GTI blob; alice's
        # next cached read must see it (new blob -> new key -> fresh decode).
        _walk(base_url, bob, "post_tweet", {"content": "second tweet"});
        r3 = _walk(base_url, alice, "query_follow_chain", {});
        assert r3 == baseline + 1 , (
            f"cached read served stale foreign GTI on mongo: {r3}"
        );
    } finally {
        _stop_server(server);
        if data_dir.exists() {
            shutil.rmtree(data_dir);
        }
    }
}
