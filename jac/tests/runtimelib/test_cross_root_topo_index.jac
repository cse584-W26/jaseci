"""Cross-root graph query tests for the topology-index optimizer.

The topology index lives on each root anchor and indexes the edges that
root *originated*. When a query crosses into another user's owned
subgraph, the index used to silently miss those edges -- the global
edge walk (with `JAC_TOPOLOGY_INDEX=0`) returns the right answer, but
the index path returned an empty / undercounted set.

These tests pin down both failure shapes against a real
`JacTestClient` (long-lived runtime context, the regime where the
optimizer actually runs):

  * a 2-hop forward chain that crosses into another user's edges, and
  * a 1-hop reverse query whose incoming edges are owned by other users.
"""

import os;
import from tests.support { JAC_ROOT }
import from tempfile { mkdtemp }
import jaclang;
import from jaclang.runtimelib.testing { JacTestClient }

glob FIXTURE = os.path.join(
         JAC_ROOT, "tests", "runtimelib", "fixtures", "cross_root_topo_index.jac"
     );

"""Force the topology-index optimizer on for the duration of `fn`."""
def with_topo_index(fn: callable) {
    prev = os.environ.get("JAC_TOPOLOGY_INDEX");
    os.environ["JAC_TOPOLOGY_INDEX"] = "1";
    try {
        fn();
    } finally {
        if prev is None {
            del os.environ["JAC_TOPOLOGY_INDEX"];
        } else {
            os.environ["JAC_TOPOLOGY_INDEX"] = prev;
        }
    }
}

"""Force both the topology-index optimizer and the cross-root fast path on
for the duration of `fn`."""
def with_cross_root(fn: callable) {
    keys = ["JAC_TOPOLOGY_INDEX", "JAC_CROSS_ROOT_RESOLVE"];
    prev = {k: os.environ.get(k) for k in keys};
    for k in keys {
        os.environ[k] = "1";
    }
    try {
        fn();
    } finally {
        for k in keys {
            if prev[k] is None {
                del os.environ[k];
            } else {
                os.environ[k] = prev[k];
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

test "cross-root forward chain returns followed user's tweets" {
    def _body {
        client = JacTestClient.from_file(FIXTURE, base_path=mkdtemp());
        try {
            # Bob registers, sets up a profile, posts a tweet.
            client.register_user("bob", "secret123");
            client.login("bob", "secret123");
            bob_profile_id = first_report(
                client.post("/walker/setup_profile_only", json={"username": "bob"})
            );
            client.post("/walker/post_tweet", json={"content": "hello world"});

            # Alice registers, sets up a profile, follows bob.
            client.register_user("alice", "secret123");
            client.login("alice", "secret123");
            client.post("/walker/setup_profile_only", json={"username": "alice"});
            client.post("/walker/follow_target", json={"target_id": bob_profile_id});

            # The chained query crosses alice's Follow edge into bob's
            # Post-edge subgraph; should reach bob's one tweet.
            count = first_report(client.post("/walker/query_follow_chain", json={}));
            assert count == 1 , f"Expected 1 reachable tweet, got {count!r}";
        } finally {
            client.close();
        }
    }
    with_topo_index(_body);
}

test "cross-root fast path matches the walk on the forward chain" {
    # Same graph and query as the walk test above, but with the whole-chain
    # cross-root fast path enabled (`resolve_chain_cross_root`). It must
    # return the identical answer: the fast path hops into bob's index instead
    # of walking his Post edges, and must not under- or over-count.
    def _body {
        client = JacTestClient.from_file(FIXTURE, base_path=mkdtemp());
        try {
            client.register_user("bob", "secret123");
            client.login("bob", "secret123");
            bob_profile_id = first_report(
                client.post("/walker/setup_profile_only", json={"username": "bob"})
            );
            client.post("/walker/post_tweet", json={"content": "hello world"});
            client.post("/walker/post_tweet", json={"content": "second tweet"});

            client.register_user("alice", "secret123");
            client.login("alice", "secret123");
            client.post("/walker/setup_profile_only", json={"username": "alice"});
            client.post("/walker/follow_target", json={"target_id": bob_profile_id});

            count = first_report(client.post("/walker/query_follow_chain", json={}));
            assert count == 2 , f"Expected 2 reachable tweets, got {count!r}";
        } finally {
            client.close();
        }
    }
    with_cross_root(_body);
}

test "cross-root fast path resolves a 3-hop chain through foreign roots" {
    # alice -Follow-> bob -Follow-> carol --> carol's tweets. Hop 2 resolves
    # inside bob's index and yields carol's profile -- a node alice's home
    # index has never seen, which is exactly where the per-hop cross-root
    # path bails to the edge walk. The whole-chain frontier keeps carol's
    # profile attached to its owner root's index and must match the walk's
    # answer. Run once with the plain index (walk fallback, the correctness
    # baseline) and once with the fast path on.
    def _build_and_query(client: any) -> any {
        carol_tweets = ["mesozoic", "cretaceous"];

        client.register_user("carol", "secret123");
        client.login("carol", "secret123");
        carol_profile_id = first_report(
            client.post("/walker/setup_profile_only", json={"username": "carol"})
        );
        for content in carol_tweets {
            client.post("/walker/post_tweet", json={"content": content});
        }

        client.register_user("bob", "secret123");
        client.login("bob", "secret123");
        bob_profile_id = first_report(
            client.post("/walker/setup_profile_only", json={"username": "bob"})
        );
        client.post("/walker/follow_target", json={"target_id": carol_profile_id});

        client.register_user("alice", "secret123");
        client.login("alice", "secret123");
        client.post("/walker/setup_profile_only", json={"username": "alice"});
        client.post("/walker/follow_target", json={"target_id": bob_profile_id});

        return first_report(client.post("/walker/query_follow_of_follow", json={}));
    }

    def _walk_body {
        client = JacTestClient.from_file(FIXTURE, base_path=mkdtemp());
        try {
            count = _build_and_query(client);
            assert count == 2 , f"Walk baseline: expected 2 tweets, got {count!r}";
        } finally {
            client.close();
        }
    }

    def _fast_body {
        client = JacTestClient.from_file(FIXTURE, base_path=mkdtemp());
        try {
            count = _build_and_query(client);
            assert count == 2 , f"Fast path: expected 2 tweets, got {count!r}";
        } finally {
            client.close();
        }
    }

    with_topo_index(_walk_body);
    with_cross_root(_fast_body);
}

test "cross-root reverse query counts members across roots" {
    def _body {
        client = JacTestClient.from_file(FIXTURE, base_path=mkdtemp());
        try {
            # Alice creates the channel.
            client.register_user("alice", "secret123");
            client.login("alice", "secret123");
            client.post("/walker/setup_profile_only", json={"username": "alice"});
            channel_id = first_report(
                client.post("/walker/create_channel", json={"name": "lounge"})
            );

            # Bob joins.
            client.register_user("bob", "secret123");
            client.login("bob", "secret123");
            client.post("/walker/setup_profile_only", json={"username": "bob"});
            client.post("/walker/join_channel", json={"channel_id": channel_id});

            # Reverse query [channel<-Member<-Profile] from alice must
            # see bob's Member edge (which bob owns).
            client.login("alice", "secret123");
            count = first_report(
                client.post(
                    "/walker/query_channel_members", json={"channel_id": channel_id}
                )
            );
            assert count == 2 , f"Expected 2 members, got {count!r}";
        } finally {
            client.close();
        }
    }
    with_topo_index(_body);
}
