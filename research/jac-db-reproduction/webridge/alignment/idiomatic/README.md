# Idiomatic Java IC5 baseline

`IdiomaticIc5.java` uses standard Connector/J 5.1.46 and one member-driven SQL aggregate over the identical `jac_alignment_utf8` MySQL anchor fixture. The request performs `START TRANSACTION READ ONLY`, session timeout `SET`, the aggregate `SELECT`, and `COMMIT`. Trusted input supplies the person UUID; authentication, ACL interpretation, schema dispatch and object hydration are outside this conventional SQL request.

The query deduplicates friends, forum/friend memberships and counted post UUIDs. Its first-creator equivalence is checked against the fixture: no post has multiple distinct valid Person creators. Runtime gates also check directed relevant edges, self-only relevant graph types and unique forum external IDs. `gate-20261020` passes all 20 original expected outputs plus the selected small input. `reference-first-creator.sql` preserves the more general scalar first-creator expression for inspecting that alternative; the measured query is `ic5.sql`.

| Added response delay | SELECT 1 median (ms) | Request median (ms) | SQL commands |
|---|---:|---:|---:|
| 0 ms | 0.2640 | 9.5701 | 4 |
| 2 ms | 2.4394 | 18.6268 | 4 |
| 10 ms | 10.8939 | 56.8916 | 4 |

Each cell uses 10 warm requests and 30 measured requests, the original Server JVM, CPU affinity 9,19, System.nanoTime around all four commands and result consumption, and the shared deadline-based response-direction proxy. Per-request independent MySQL session Questions deltas are four after subtracting the status observer; Com_select=1, Com_commit=1 and Com_call_procedure=0. All 120 requests match the expected result. Raw rows, calibration samples, process commands, source hashes and stopped-proxy receipts are under `delay-results/`. The calibration immediately precedes each measured cell; this completed sweep has no after-calibration samples.

`explain-small.json` and `explain-original-idx1.json` are prepared EXPLAIN FORMAT=JSON outputs using the actual parameter values. Both show friend traversal using source_type/target_type indexes, membership using target_type, container/creator traversal using source_type, and node lookups using PRIMARY eq_ref. The ALL accesses are materialized friends/membership derived results. EXPLAIN row counts are optimizer estimates. These plans cover generic JSON anchors; Jac final's derived mirror access paths are a separate implementation choice.

Reproduce on the prepared fixture:

```sh
python reproduction/webridge/alignment/idiomatic/run.py gate --out /tmp/idiomatic-gate-new
python reproduction/webridge/alignment/idiomatic/sweep.py
python reproduction/webridge/alignment/idiomatic/verify.py
```

The sweep output directory must be absent before running. `run.py --url` changes the JDBC endpoint; `sweep.py` uses the shared proxy on 18537 targeting fixture port 55337. `verify.py` independently recomputes medians, exact results, command counts and proxy cleanup from preserved raw artifacts.
