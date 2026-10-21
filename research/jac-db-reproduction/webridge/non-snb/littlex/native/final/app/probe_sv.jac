"""Server-side runtime probe + no-op floor walker.

`runtime_probe` reports which jaclang the SERVER process actually runs and
the EFFECTIVE ablation-flag values, resolved with the same precedence the
runtime uses (env var -> jac.toml [run] -> default) but via PUBLIC API only
(the runtime's own _enabled helpers are impl-private and not importable).
`noop` returns [] and is the fixed per-request-tax floor (auth + context +
commit, zero graph work) for the ablation analysis.
"""

import os;
import time;
import jaclang;
import from jaclang.project.config { get_config }
import from jaclang.lib { GraphQuery, QHop, QPred, refs }
import from app { Profile, Tweet, Follow, Post }

def _effective(env_name: str, cfg_value: bool) -> bool {
    env = os.environ.get(env_name);
    if env is not None {
        return env.lower() in ("1", "true", "yes", "on");
    }
    return cfg_value;
}

walker:pub runtime_probe {
    can run with Root entry {
        cfg = get_config();
        run_cfg = cfg.run if cfg is not None else None;
        report {
            "jaclang_file": str(jaclang.__file__),
            "gti_effective": _effective(
                "JAC_TOPOLOGY_INDEX",
                run_cfg.topology_index if run_cfg else True
            ),
            "cross_root_effective": _effective(
                "JAC_CROSS_ROOT_RESOLVE",
                run_cfg.cross_root_resolve if run_cfg else False
            ),
            "batch_l3_effective": _effective(
                "JAC_BATCH_L3",
                run_cfg.batch_l3 if run_cfg else False
            ),
            "read_only_effective": _effective(
                "JAC_READ_ONLY",
                run_cfg.read_only if run_cfg else False
            ),
            "env_JAC_TOPOLOGY_INDEX": os.environ.get("JAC_TOPOLOGY_INDEX"),
            "env_JAC_CROSS_ROOT_RESOLVE": os.environ.get("JAC_CROSS_ROOT_RESOLVE"),
            "env_JAC_BATCH_L3": os.environ.get("JAC_BATCH_L3"),
            "env_JAC_READ_ONLY": os.environ.get("JAC_READ_ONLY")
        };
    }
}

walker:pub noop {
    can run with Root entry {
        report [];
    }
}

# --- CP-M Task 1: JAC_PROMOTED_PREDICATES microbench ---------------------
# Two shapes, same predicate ('author_username == X' against the 20k-row
# Tweet set), because the EXPLAIN audit found the promoted-column win is
# origin-set-size dependent: postgres only flips from nested-loop-by-pkey
# to a hash/bitmap-index plan on the promoted column once the join's
# candidate-row count is large enough to be worth it.
#
# probe_filtered_read: NARROW shape - the caller's own Follow-graph fan-out
# (~50-60 followed profiles => ~12k candidate tweet rows via one profile
# per iteration). Mirrors app.load_feed's join exactly.
walker:pub probe_filtered_read {
    has target_username: str = "";

    can run with Root entry {
        t0 = time.perf_counter();
        mine = [-->[?:Profile]];
        hits: list = [];
        if mine {
            me = mine[0];
            hits = [
                me->:Follow:->[?:Profile]
                -->[?:Tweet, author_username == self.target_username]
            ];
        }
        server_total_ms = (time.perf_counter() - t0) * 1000;
        report {"server_total_ms": server_total_ms, "count": len(hits)};
    }
}

# probe_filtered_read_wide: WIDE shape - origin is every seeded Profile
# (~100, passed in by id since no single user's root reaches other users'
# profiles without a Follow edge), single Post hop straight to Tweet. This
# is the TPC-C-Payment-shaped access pattern (a broad, index-eligible
# equality lookup with no narrowing graph context) - library-mode
# GraphQuery/refs() used directly (jaclang.lib) so the origin set isn't
# bottlenecked by walker-visit/Follow-graph reachability, but the query
# still compiles through the SAME compile_query()/sqlcompile path a normal
# walker traversal uses.
walker:pub probe_filtered_read_wide {
    has target_ids: list[str] = [], target_username: str = "";

    can run with Root entry {
        # origin resolution (100x jobj() round trips) is walker-setup cost,
        # not the compile_query()/SQL cost this flag changes - timed span
        # starts after it so the delta isolates the actual query, same as
        # the raw EXPLAIN comparison.
        origins = [jobj(i) for i in self.target_ids];
        t0 = time.perf_counter();
        q = GraphQuery(
            origins,
            hops=[
                QHop(
                    dir=2,
                    `edge=Post,
                    nd=Tweet,
                    preds=[
                        QPred(field="author_username", op="==", value=self.target_username)
                    ]
                )
            ]
        );
        hits = refs(q);
        server_total_ms = (time.perf_counter() - t0) * 1000;
        report {"server_total_ms": server_total_ms, "count": len(hits)};
    }
}

# --- CP-M Task 2: JAC_BATCH_UPSERT round-trip / write-latency probe -------
# Mirrors a TPC-C New-Order transaction's shape: one parent (Order) plus N
# children (OrderLine) connected to it, all created in a single request/
# commit. Scratch-only types (ProbeOrder/ProbeLine/ProbeItem) - never used
# by app.jac or other arms.
node ProbeOrder {
    has seq: int = 0;
}

edge ProbeLine {}

node ProbeItem {
    has seq: int = 0,
        val: str = "";
}

walker:pub probe_write_n {
    has n: int = 10,
        fail: bool = False;

    can run with Root entry {
        t0 = time.perf_counter();
        parent = root ++> ProbeOrder(seq=0);
        for i in range(self.n) {
            parent +>:ProbeLine():+> ProbeItem(seq=i, val=f"line-{i}");
        }
        if self.fail {
            raise Exception("probe_write_n: injected failure after N creates");
        }
        server_total_ms = (time.perf_counter() - t0) * 1000;
        report {"server_total_ms": server_total_ms, "n": self.n};
    }
}
