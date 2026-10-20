# Page-query branch selection and warmup timing

The two retained `load_feed_page` diagnostics selected different runtime SQL
branches. The inspected ad469 source has no frontier-size/user-count threshold
for selecting global_topk. It requires an available endpoint projection and
order index, in addition to the same pipeline/query flags.

## Source conditions

`ad469-source/jac/jaclang/runtimelib/impl/query_planner.impl.jac:1130–1197`:

1. A three-element sort/limit pipeline, clean session, no explicit query slice,
   and no final-hop `only` predicate.
2. Final hop is outbound, with no edge predicates.
3. `ensure_mirror_endpoint` returns a usable endpoint column.
4. `JAC_FUSED_FEED=1`, at least two hops, and successful
   `ensure_mirror_order_index` set `mirror_spec['global_topk']=True`.

`sqlcompile.impl.jac:437` directly reads that stamp. If false, a usable endpoint
and STREAM_LATERAL allow the LATERAL branch; otherwise the ordinary mirror join
is emitted with the bounded `_topk` wrapper.

`store.impl.jac:1098–1120` refuses a memo while monotonic time is before its
retry_at. A first retryable failure sets retry_at to now+2 seconds.

## Retained timing evidence

| Observation |10-warm fixed-user diagnostic|110-warm round-robin diagnostic|
|---|---|---|
| Run directory |20261019T195241Z/t200-feed_page-ad469-control|20261019T195758Z/t200-page-ad-control-rr|
| Tweet endpoint lock-timeout warning, tries1 |19:53:25.099874Z|19:58:12.299766Z|
| First profiled SQL UTC |19:53:25.421|19:58:15.603|
| Delay from refusal to first profile |~0.321s|~3.303s|
| Final early-profile SQL UTC |19:53:26.356, call9|Not needed for the first-call boundary|
| SQL branch observed |All10 calls ordinary mirror `_topk`|All50 calls global_topk|
| Main two-hop SQL text length |1748 characters|1206 characters|
| First main-query execute duration |26.906ms|0.328ms|

The early capture's final call ended only~1.256s after the warning, within the
first2s refusal interval. Its ensure path therefore remained gated throughout
that profile. The round-robin capture began~3.303s after its corresponding
warning; its generated SQL explicitly references the now-usable endpoint and
uses the global Top-K branch.

This provides a concrete warmup-readiness explanation for these page SQL
shapes. The causal input is elapsed retry readiness, not an explicit rule on
number of users or frontier length. It is distinct from the uncapped W1
new-fixture/old-fixture latency comparison, which needs its own SQL/plan evidence.

## Artifact locations

- Warning logs:
  littlex/diagnostics/<run directory>/server.log, line33 in each capture.
- Request windows and retained protocol SQL:
  results/littlex-diagnostics/<run directory>/postgres-00.log and subsequent
  numbered logs; profile.json retains each execute text/duration.
- Early last window: postgres-09.log.

Analysis uses retained warning/protocol logs.
