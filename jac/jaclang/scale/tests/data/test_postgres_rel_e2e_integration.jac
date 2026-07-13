"""E2e gate for postgres-rel: a real node+edge graph persists across a COLD
server restart WITH THE GTI FULLY OFF.

Drives `jac start` on a free port with JAC_SCALE_BACKEND=postgres-rel and
JAC_TOPOLOGY_INDEX=0 over real HTTP: register+login, AddPerson writes a 2-hop
graph (Root->Person->Pet) through apply(), assert rows land in BOTH the
anchors table AND the edges table. Then the server is killed and started COLD
again -- re-login and ListFamily must read the same graph back. With the GTI
flag off there are no topology blobs at all, so the 2-hop traversal resolving
proves the resolver's topology_sql dispatch + the edges table end to end.

Uses database jactest_rel (POSTGRESQL_REL_URI override), disjoint from the KV
suites' jactest. Truncates working tables before AND after."""

import contextlib;
import gc;
import os;
import shutil;
import socket;
import subprocess;
import sys;
import time;
import psycopg;
import requests;
import from pathlib { Path }
import from typing { cast }

glob FIXTURES_DIR = Path(cast(str, __file__)).parent / "fixtures",
     JAC_FILE = FIXTURES_DIR / "graph_app.jac",
     PG_DSN = os.environ.get('POSTGRESQL_REL_URI', 'postgresql:///jactest_rel'),
     USER = "pgrel_e2e_user",
     PASS = "pass123e2e";

def _get_free_port -> int {
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s {
        s.bind(("", 0));
        return cast(int, s.getsockname()[1]);
    }
}

"""Truncate working tables if the backend has created them yet."""
def _truncate_tables {
    conn = psycopg.connect(PG_DSN, autocommit=True);
    try {
        for tbl in ("anchors", "edges") {
            row = conn.execute(f"SELECT to_regclass('public.{tbl}')").fetchone();
            if row is not None and row[0] is not None {
                conn.execute(f"TRUNCATE {tbl}");
            }
        }
    } finally {
        conn.close();
    }
}

def _table_count(tbl: str) -> int {
    conn = psycopg.connect(PG_DSN, autocommit=True);
    try {
        cur = conn.execute(f"SELECT count(*) FROM {tbl}");
        return cast(int, cur.fetchone()[0]);
    } finally {
        conn.close();
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

"""Start `jac start` on `port` with postgres-rel and the GTI OFF."""
def _start_server(port: int) -> subprocess.Popen {
    jac_executable = Path(sys.executable).parent / "jac";
    cmd = [str(jac_executable), "start", str(JAC_FILE.name), "--port", str(port)];
    env = os.environ.copy();
    env["POSTGRESQL_URI"] = PG_DSN;
    env["JAC_SCALE_BACKEND"] = "postgres-rel";
    env["JAC_TOPOLOGY_INDEX"] = "0";
    env.pop("JAC_TOPOLOGY_SQL", None);
    env.pop("MONGODB_URI", None);
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

"""Register (idempotent) + login; return a bearer token for USER."""
def _login(base_url: str) -> str {
    reg_body: dict = {
        "identities": [{"type": "username", "value": USER}],
        "credential": {"type": "password", "password": PASS}
    };
    reg = requests.post(f"{base_url}/user/register", json=reg_body, timeout=5);
    assert reg.status_code in (201, 400, 409) , f"register failed: {reg.status_code} - {reg.text}";
    login_body: dict = {
        "identity": {"type": "username", "value": USER},
        "credential": {"type": "password", "password": PASS}
    };
    res = requests.post(f"{base_url}/user/login", json=login_body, timeout=5);
    assert res.status_code == 200 , f"login failed: {res.status_code} - {res.text}";
    login_data = cast(dict[str, any], _extract(res.json()));
    return cast(str, login_data["token"]);
}

test "backend=postgres-rel persists graph across cold restart with GTI off" {
    if not JAC_FILE.exists() {
        raise FileNotFoundError(f"Missing fixture: {JAC_FILE}");
    }
    data_dir = FIXTURES_DIR / ".jac";
    if data_dir.exists() {
        shutil.rmtree(data_dir);
    }
    _truncate_tables();

    port = _get_free_port();
    base_url = f"http://localhost:{port}";
    server: (subprocess.Popen | None) = None;
    try {
        # --- server 1: write the graph -------------------------------------
        server = _start_server(port);
        token = _login(base_url);
        auth: dict = {"Authorization": f"Bearer {token}"};

        add_body: dict = {"name": "Alice", "pets": ["Rex", "Milo"]};
        res = requests.post(
            f"{base_url}/walker/AddPerson", json=add_body, headers=auth, timeout=5
        );
        assert res.status_code == 200 , f"AddPerson failed: {res.status_code} - {res.text}";

        assert _table_count("anchors") > 0 , "no rows in anchors table after write";
        # THE rel assertion: edge rows landed (root->person, person->pet x2).
        edge_rows = _table_count("edges");
        assert edge_rows >= 3 , f"expected >=3 edge rows, got {edge_rows}";
        # GTI is off: no anchor may carry a topology blob.
        conn = psycopg.connect(PG_DSN, autocommit=True);
        try {
            blob_row = conn.execute(
                "SELECT count(*) FROM anchors " "WHERE data ? 'topology_index_data'"
            ).fetchone();
            assert blob_row[0] == 0 , f"{blob_row[
                0
            ]} anchors carry GTI blobs with flag off";
        } finally {
            conn.close();
        }

        _stop_server(server);
        server = None;

        # --- server 2: COLD read the graph back ----------------------------
        # New process, empty caches, zero GTI blobs: the 2-hop ListFamily
        # traversal can only resolve through the edges table via topology_sql.
        server = _start_server(port);
        token = _login(base_url);
        auth = {"Authorization": f"Bearer {token}"};

        empty_body: dict = {};
        res = requests.post(
            f"{base_url}/walker/ListFamily", json=empty_body, headers=auth, timeout=5
        );
        assert res.status_code == 200 , f"ListFamily failed: {res.status_code} - {res.text}";
        data = cast(dict[str, any], _extract(res.json()));
        family = cast(list, data["reports"][0]);
        assert len(family) == 1 , f"expected 1 person after restart, got {family}";
        alice = cast(dict[str, any], family[0]);
        assert alice["name"] == "Alice";
        pets = sorted(cast(list, alice["pets"]));
        assert pets == ["Milo", "Rex"] , f"pets lost across restart: {alice}";
    } finally {
        _stop_server(server);
        _truncate_tables();
        if data_dir.exists() {
            shutil.rmtree(data_dir);
        }
    }
}
