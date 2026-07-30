"""Staleness guard for the topology index (GTI).

`JAC_TOPOLOGY_INDEX` gates only the GTI *write* hooks; reads always trust
whatever index blob exists on the root anchor. Before this guard, a write
performed while the hooks were off left the stored index silently stale, and
every index-backed read path (local, per-hop cross-root, whole-chain frontier)
kept returning answers from the rotten blob.

The guard: when an edge mutation is skipped because the hooks are off, the
affected roots' `topology_index_data` is overwritten with a 1-byte stale
sentinel. Every reader treats the sentinel as "no usable index" and falls back
to the (correct) edge walk; the incremental hooks refuse to resume on a stale
blob, so only an explicit rebuild can clear it.

Also pins the frontier origin guard: `resolve_chain_cross_root` must bail to
None (-> caller falls back) for origin ids the home index has never seen or
does not own, instead of silently resolving to an empty set.
"""

import os;
import from uuid { uuid4 }
import from tests.support { JAC_ROOT }
import from tempfile { mkdtemp }
import jaclang;
import from jaclang.runtimelib.testing { JacTestClient }
import from jaclang.runtimelib.topology_index {
    TopologyIndex,
    TOPO_STALE_BLOB,
    is_stale_index_blob
}

glob FIXTURE = os.path.join(
         JAC_ROOT, "tests", "runtimelib", "fixtures", "cross_root_topo_index.jac"
     );

"""Set env flags, run `fn`, restore previous values."""
def with_flags(flags: dict, fn: callable) {
    prev = {k: os.environ.get(k) for k in flags};
    for (k, v) in flags.items() {
        if v is None {
            if k in os.environ {
                del os.environ[k];
            }
        } else {
            os.environ[k] = v;
        }
    }
    try {
        fn();
    } finally {
        for (k, pv) in prev.items() {
            if pv is None {
                if k in os.environ {
                    del os.environ[k];
                }
            } else {
                os.environ[k] = pv;
            }
        }
    }
}

"""Pull the first report value from a JacTestClient response."""
def first_report(response: any) -> any {
    data = response.data;
    if data and "reports" in data {
        reports = data["reports"];
        return reports[0] if reports else None;
    }
    return None;
}

test "stale sentinel round-trips through the blob helpers" {
    assert is_stale_index_blob(TOPO_STALE_BLOB);
    assert not is_stale_index_blob(None);
    assert not is_stale_index_blob(b"");
    idx = TopologyIndex();
    idx.add_node(uuid4(), "T");
    assert not is_stale_index_blob(idx.encode());
}

test "frontier bails on origins the home index does not own" {
    a = uuid4();
    b = uuid4();
    foreign_owner = uuid4();
    c = uuid4();
    idx = TopologyIndex();
    idx.add_node(a, "T");
    idx.add_node(b, "T");
    idx.add_node(c, "T", None, foreign_owner);
    idx.add_edge(a, b, "E");
    triple = [(None, None, 2)];

    # Known, self-owned origin resolves normally.
    assert idx.resolve_chain_cross_root(None, {a}, triple) == {b};
    # Unknown origin: bail to None (caller falls back), never a silent empty.
    assert idx.resolve_chain_cross_root(None, {uuid4()}, triple) is None;
    # Foreign-owned origin: its outbound edges live in the owner root's
    # index, so resolving it here would undercount -- bail.
    assert idx.resolve_chain_cross_root(None, {c}, triple) is None;
}

test "write with hooks off marks the index stale and reads fall back to walk" {
    def _body {
        client = JacTestClient.from_file(FIXTURE, base_path=mkdtemp());
        try {
            # Indexed era: bob posts tweet1, alice follows him.
            client.register_user("bob", "secret123");
            client.login("bob", "secret123");
            bob_profile_id = first_report(
                client.post("/walker/setup_profile_only", json={"username": "bob"})
            );
            client.post("/walker/post_tweet", json={"content": "t1"});

            client.register_user("alice", "secret123");
            client.login("alice", "secret123");
            client.post("/walker/setup_profile_only", json={"username": "alice"});
            client.post(
                "/walker/follow_target", json={"target_id": bob_profile_id}
            );
            count = first_report(
                client.post("/walker/query_follow_chain", json={})
            );
            assert count == 1 , f"Indexed era: expected 1 tweet, got {count!r}";

            # Dark era: hooks off, bob posts tweet2. The write must mark
            # bob's index stale instead of silently rotting it.
            os.environ["JAC_TOPOLOGY_INDEX"] = "0";
            client.login("bob", "secret123");
            client.post("/walker/post_tweet", json={"content": "t2"});
            os.environ["JAC_TOPOLOGY_INDEX"] = "1";

            # Hooks back on: the fast paths must refuse the stale index and
            # walk. Without the guard this returns 1 (the rotten blob).
            client.login("alice", "secret123");
            count = first_report(
                client.post("/walker/query_follow_chain", json={})
            );
            assert count == 2 , f"After stale write: expected 2 tweets, got {count!r}";

            # A flag-on write must NOT resurrect the stale index with a
            # partial rebuild -- staleness only clears via explicit rebuild.
            client.login("bob", "secret123");
            client.post("/walker/post_tweet", json={"content": "t3"});
            client.login("alice", "secret123");
            count = first_report(
                client.post("/walker/query_follow_chain", json={})
            );
            assert count == 3 , f"After indexed write on stale root: expected 3, got {count!r}";
        } finally {
            client.close();
        }
    }
    with_flags(
        {"JAC_TOPOLOGY_INDEX": "1", "JAC_CROSS_ROOT_RESOLVE": "1"}, _body
    );
}

test "stale guard also covers the reverse cross-root query" {
    def _body {
        client = JacTestClient.from_file(FIXTURE, base_path=mkdtemp());
        try {
            client.register_user("alice", "secret123");
            client.login("alice", "secret123");
            client.post("/walker/setup_profile_only", json={"username": "alice"});
            channel_id = first_report(
                client.post("/walker/create_channel", json={"name": "lounge"})
            );

            client.register_user("bob", "secret123");
            client.login("bob", "secret123");
            client.post("/walker/setup_profile_only", json={"username": "bob"});
            # Bob joins during the dark era: his Member edge never reaches
            # any index, and both touched roots go stale.
            os.environ["JAC_TOPOLOGY_INDEX"] = "0";
            client.post("/walker/join_channel", json={"channel_id": channel_id});
            os.environ["JAC_TOPOLOGY_INDEX"] = "1";

            client.login("alice", "secret123");
            count = first_report(
                client.post(
                    "/walker/query_channel_members", json={"channel_id": channel_id}
                )
            );
            assert count == 2 , f"Expected 2 members via walk, got {count!r}";
        } finally {
            client.close();
        }
    }
    with_flags(
        {"JAC_TOPOLOGY_INDEX": "1", "JAC_CROSS_ROOT_RESOLVE": "1"}, _body
    );
}
