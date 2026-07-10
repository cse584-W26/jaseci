"""Parity + batching tests for the `cross_root_resolve` and `batch_l3` flags.

Both flags default OFF and must never change *results* -- only speed. Two
independent, default-off flags give a 2x2 ablation matrix:

  * `cross_root_resolve` (`JAC_CROSS_ROOT_RESOLVE`) -- resolve a foreign-root
    traversal hop via the owning roots' own topology indexes instead of the
    naive grant-checked edge walk.
  * `batch_l3` (`JAC_BATCH_L3`) -- fetch tiered-memory L3 misses via one
    batched `l3.batch_get()` instead of looping `l3.get()` per miss.

The matrix test reuses the multi-root `cross_root_topo_index` fixture (the
same graph the existing cross-root topology test exercises) and asserts all
four flag combinations return identical counts -- the parity invariant.

The batching test drives `TieredMemory.batch_get` directly with a counting
fake L3 to prove the flag-on path issues ONE `batch_get` round-trip where the
flag-off path issues one `get` per miss (the countable seam), while both
return the same anchors.
"""

import os;
import from uuid { uuid4 }
import from tests.support { JAC_ROOT }
import from tempfile { mkdtemp }
import jaclang;
import from jaclang.runtimelib.testing { JacTestClient }
import from jaclang.runtimelib.memory { TieredMemory }

glob FIXTURE = os.path.join(
         JAC_ROOT, "tests", "runtimelib", "fixtures", "cross_root_topo_index.jac"
     );

"""Set (or clear) an env flag to a truthy/absent value."""
def _set_flag(name: str, on: bool) {
    if on {
        os.environ[name] = "1";
    } elif name in os.environ {
        del os.environ[name];
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

test "2x2 flag matrix returns identical cross-root results" {
    def _body {
        # Topology index must be on for either flag to matter; capture the
        # cross_root/batch flags so we can restore them afterwards.
        prev = {
            k: os.environ.get(k) for k in ("JAC_CROSS_ROOT_RESOLVE", "JAC_BATCH_L3")
        };
        client = JacTestClient.from_file(FIXTURE, base_path=mkdtemp());
        try {
            # Bob: profile + one tweet.
            client.register_user("bob", "secret123");
            client.login("bob", "secret123");
            bob_profile_id = first_report(
                client.post("/walker/setup_profile_only", json={"username": "bob"})
            );
            client.post("/walker/post_tweet", json={"content": "hello world"});

            # Alice: profile, follows bob, owns a channel.
            client.register_user("alice", "secret123");
            client.login("alice", "secret123");
            client.post("/walker/setup_profile_only", json={"username": "alice"});
            client.post("/walker/follow_target", json={"target_id": bob_profile_id});
            channel_id = first_report(
                client.post("/walker/create_channel", json={"name": "lounge"})
            );

            # Bob joins alice's channel (his Member edge is foreign-owned).
            client.login("bob", "secret123");
            client.post("/walker/join_channel", json={"channel_id": channel_id});

            # Alice runs both cross-root queries under every flag combo.
            client.login("alice", "secret123");
            follow_counts: list = [];
            member_counts: list = [];
            for cross in (False, True) {
                for batch in (False, True) {
                    _set_flag("JAC_CROSS_ROOT_RESOLVE", cross);
                    _set_flag("JAC_BATCH_L3", batch);
                    follow_counts.append(
                        first_report(client.post("/walker/query_follow_chain", json={}))
                    );
                    member_counts.append(
                        first_report(
                            client.post(
                                "/walker/query_channel_members",
                                json={"channel_id": channel_id}
                            )
                        )
                    );
                }
            }
            # Forward chain reaches bob's 1 tweet; channel has 2 members.
            assert follow_counts == [1, 1, 1, 1] , (
                f"follow-chain parity broke across flag matrix: {follow_counts}"
            );
            assert member_counts == [2, 2, 2, 2] , (
                f"channel-members parity broke across flag matrix: {member_counts}"
            );
        } finally {
            client.close();
            for (k, v) in prev.items() {
                if v is None {
                    if k in os.environ {
                        del os.environ[k];
                    }
                } else {
                    os.environ[k] = v;
                }
            }
        }
    }
    # Reuse the existing topo-index guard.
    prev_topo = os.environ.get("JAC_TOPOLOGY_INDEX");
    os.environ["JAC_TOPOLOGY_INDEX"] = "1";
    try {
        _body();
    } finally {
        if prev_topo is None {
            del os.environ["JAC_TOPOLOGY_INDEX"];
        } else {
            os.environ["JAC_TOPOLOGY_INDEX"] = prev_topo;
        }
    }
}


obj _FakeAnchor {
    has id: any;
}

"""A stand-in L3 that counts per-id `get` calls vs batched `batch_get` calls."""
obj _CountingL3 {
    has store: dict = {},
        get_calls: int = 0,
        batch_calls: int = 0;

    def get(id: any) -> any {
        self.get_calls += 1;
        return self.store.get(id);
    }

    def batch_get(ids: list) -> dict {
        self.batch_calls += 1;
        return {
            i: self.store[i]
            for i in ids
            if i in self.store
        };
    }
}

def _seed_tm -> tuple {
    tm = TieredMemory(base_path=None);
    fake = _CountingL3();
    ids = [uuid4(), uuid4(), uuid4()];
    for i in ids {
        fake.store[i] = _FakeAnchor(id=i);
    }
    tm.l3 = fake;
    return (tm, fake, ids);
}

test "batch_l3 off loops l3.get per miss" {
    prev = os.environ.get("JAC_BATCH_L3");
    if "JAC_BATCH_L3" in os.environ {
        del os.environ["JAC_BATCH_L3"];
    }
    try {
        (tm, fake, ids) = _seed_tm();
        result = tm.batch_get(ids);
        assert set(result.keys()) == set(ids);
        assert fake.get_calls == 3 , f"expected 3 get() calls, got {fake.get_calls}";
        assert fake.batch_calls == 0 , f"expected 0 batch_get(), got {fake.batch_calls}";
    } finally {
        if prev is not None {
            os.environ["JAC_BATCH_L3"] = prev;
        }
    }
}

test "batch_l3 on issues one batch_get and matches" {
    prev = os.environ.get("JAC_BATCH_L3");
    os.environ["JAC_BATCH_L3"] = "1";
    try {
        (tm, fake, ids) = _seed_tm();
        result = tm.batch_get(ids);
        assert set(result.keys()) == set(ids);
        assert fake.batch_calls == 1 , f"expected 1 batch_get(), got {fake.batch_calls}";
        assert fake.get_calls == 0 , f"expected 0 get() calls, got {fake.get_calls}";
    } finally {
        if prev is None {
            del os.environ["JAC_BATCH_L3"];
        } else {
            os.environ["JAC_BATCH_L3"] = prev;
        }
    }
}
