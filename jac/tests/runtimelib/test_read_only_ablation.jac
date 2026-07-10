"""Parity + seam tests for the default-off `read_only` ablation flag.

`read_only` (env `JAC_READ_ONLY`) is an ABLATION knob: when ON it skips the
per-request write/persistence machinery (the end-of-request `acommit`, the
pass-2 per-field hash snapshot at load, and the pass-1 whole-anchor hash at
deserialize) so a pure-read benchmark can measure the read ceiling without
the persistence tax. Default OFF = zero behavior change. It must NEVER change
what a read returns -- only speed.

Three tests:

  * parity -- seed a graph with the flag OFF, then run the same read
    traversal (a follow-chain "feed") with `JAC_READ_ONLY` OFF and ON and
    assert identical results.
  * snapshot seam (pass 2) -- `snapshot_field_hashes` sets
    `__jac_field_hashes__` when the flag is OFF and early-returns (no
    snapshot) when it is ON.
  * deserialize seam (pass 1) -- a round-tripped anchor gets a non-zero
    `.hash` when the flag is OFF and keeps its default `0` when it is ON.
"""

import os;
import from tempfile { mkdtemp }
import jaclang;
import from tests.support { JAC_ROOT }
import from jaclang.runtimelib.testing { JacTestClient }
import from jaclang.runtimelib.changeset { snapshot_field_hashes }
import from jaclang.runtimelib.serializer { Serializer }

glob FIXTURE = os.path.join(
         JAC_ROOT, "tests", "runtimelib", "fixtures", "cross_root_topo_index.jac"
     );


node RoItem {
    has name: str = "";
}


"""Set (truthy) or clear an env flag."""
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


test "read_only OFF vs ON returns identical read results" {
    def _body {
        prev = os.environ.get("JAC_READ_ONLY");
        # Seed with the flag OFF so writes actually persist.
        _set_flag("JAC_READ_ONLY", False);
        client = JacTestClient.from_file(FIXTURE, base_path=mkdtemp());
        try {
            # Bob: profile + one tweet.
            client.register_user("bob", "secret123");
            client.login("bob", "secret123");
            bob_profile_id = first_report(
                client.post("/walker/setup_profile_only", json={"username": "bob"})
            );
            client.post("/walker/post_tweet", json={"content": "hello world"});

            # Alice: profile that follows bob.
            client.register_user("alice", "secret123");
            client.login("alice", "secret123");
            client.post("/walker/setup_profile_only", json={"username": "alice"});
            client.post("/walker/follow_target", json={"target_id": bob_profile_id});

            # The feed-equivalent read, run under the flag OFF then ON.
            counts: list = [];
            for ro in (False, True) {
                _set_flag("JAC_READ_ONLY", ro);
                counts.append(
                    first_report(client.post("/walker/query_follow_chain", json={}))
                );
            }
            assert counts == [1, 1] , (
                f"read parity broke under read_only flag: {counts}"
            );
        } finally {
            client.close();
            if prev is None {
                if "JAC_READ_ONLY" in os.environ {
                    del os.environ["JAC_READ_ONLY"];
                }
            } else {
                os.environ["JAC_READ_ONLY"] = prev;
            }
        }
    }
    # Topology index on for a realistic read path (matches sibling tests).
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


test "snapshot_field_hashes is skipped when read_only is on (pass 2)" {
    prev = os.environ.get("JAC_READ_ONLY");
    try {
        # OFF: snapshot populates __jac_field_hashes__.
        _set_flag("JAC_READ_ONLY", False);
        arch_off = RoItem(name="alpha");
        anchor_off = arch_off.__jac__;
        snapshot_field_hashes(anchor_off);
        assert "__jac_field_hashes__" in arch_off.__dict__ , (
            "expected snapshot to set __jac_field_hashes__ when flag is off"
        );

        # ON: snapshot early-returns, leaving no snapshot.
        _set_flag("JAC_READ_ONLY", True);
        arch_on = RoItem(name="beta");
        anchor_on = arch_on.__jac__;
        snapshot_field_hashes(anchor_on);
        assert "__jac_field_hashes__" not in arch_on.__dict__ , (
            "expected no snapshot to be written when flag is on"
        );
    } finally {
        if prev is None {
            if "JAC_READ_ONLY" in os.environ {
                del os.environ["JAC_READ_ONLY"];
            }
        } else {
            os.environ["JAC_READ_ONLY"] = prev;
        }
    }
}


test "deserialize skips whole-anchor hash when read_only is on (pass 1)" {
    prev = os.environ.get("JAC_READ_ONLY");
    try {
        data = Serializer.serialize(RoItem(name="gamma").__jac__, include_type=True);

        _set_flag("JAC_READ_ONLY", False);
        loaded_off = Serializer.deserialize(data);
        assert loaded_off is not None;
        assert loaded_off.hash != 0 , (
            f"expected computed hash when flag is off, got {loaded_off.hash}"
        );

        _set_flag("JAC_READ_ONLY", True);
        loaded_on = Serializer.deserialize(data);
        assert loaded_on is not None;
        assert loaded_on.hash == 0 , (
            f"expected default hash (0) when flag is on, got {loaded_on.hash}"
        );
    } finally {
        if prev is None {
            if "JAC_READ_ONLY" in os.environ {
                del os.environ["JAC_READ_ONLY"];
            }
        } else {
            os.environ["JAC_READ_ONLY"] = prev;
        }
    }
}
