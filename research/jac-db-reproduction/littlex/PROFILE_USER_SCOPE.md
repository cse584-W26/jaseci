# Fixed-user diagnostics versus formal warm/user schedule

The diagnostic and formal schedules differ in directly inspectable ways:

| Dimension | Read profile helper | Formal littleX driver |
|---|---|---|
| Warm requests |10 by default|110 in the current recipe|
| User selection |One `--user`, default seed profiles[0].username|sorted token usernames, round-robin|
| Timed selection |Same fixed user|round-robin across all token users|
| W3 read route |feed_page → load_feed_page by default|mix_run.FEED_WALKER default load_feed_page|
| W3 state |Read-only snapshot diagnostic|Scheduled writes can change tweets/follows/likes|

Source anchors:
- scripts/littlex_profile.py: fixed user and warm/profile loops.
- littlex/harness/run.py:203+ defines sorted tokens, warm rotation and timed
  rotation. Warm indices are negative and timed indices restart at0.
- littlex/harness/mix_run.py:49+ selects load_feed_page by default; its
  run_engine_mix rotates users and operations across the warm and timed loops.
- littlex/harness/oracle.py:53 expected_feeds and95 expected_pages derive each
  user's full-feed membership and top20 from the seed.

## Direct checks before explaining a difference

1. Compare actual username/token-key selection, not only tier. Derive full
   membership count and top20 IDs for the fixed user and the formal user set
   from the same seed. Fixed-user output size can be20 while its upstream
   frontier/candidate counts differ across users. This is a question for seed
   and per-request SQL, not a conclusion from output size.
2. Compare exact route, source hash, flags, fixture hash and mutation history.
   A fresh read-only page capture is not automatically a W3 post-write capture.
3. Use retained SQL windows to compare statement shapes, bound origin IDs and
   returned row counts where recorded. Source prefetch/stream selection is
   conditional on query shape, type/subtype metadata and projection readiness;
   readiness cannot be inferred from10 versus110 alone.
4. Check prepared-statement names and bind durations across the early/late
   requests. vendor/pgpsycopg.py:454+ respects JAC_PG_PREPARE_THRESHOLD, otherwise
   leaves psycopg's default policy; the process's pool is reused. Different
   parameter history may be testable in plans, but no plan change is established
   by differing warmup counts alone.
5. Separate periodic statements by shape and PID. store.impl.jac:_memo_check
   adds a five-second schema-existence guard. Authentication may add an
   identity_users lookup; raw logs can identify it. These add request work
   independently of graph-output cardinality.
6. Use the stage reconciliation in PROFILING_PLAN.md: stage_sum minus
   x-server-ser-ms, not stage_sum itself, matches the original driver headline.

A controlled follow-up uses the same restored fixture and same route, first
fixed-user and then full round-robin with the original110 warm requests,
recording per-user outputs and SQL/stage evidence. Scheduled diagnostics and
formal runs stay serialized. No source change is required to compare scopes.
