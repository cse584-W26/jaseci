# Final-defaults comparison against the original littleX boot

The fresh-cell comparison uses final Jac32c5d1dbb. Historical0904littleX CONTROL
used ad469c988. Original chain: `91-night-run.sh` → `boot_arm` →
`PERF=1 harness/profiling/start_pg.sh`; the CONTROL wrapper additionally
set STREAM_LATERAL,SQL_ACL,FUSED_FEED,STICKY_DENY to1 before flag retirement.

| Setting | Original boot | Current collection | Source-level effective result |
|---|---|---|---|
| JAC_PG_DRIVER | psycopg | psycopg | same |
| JAC_PG_POOL | 1 | 1 | same |
| JAC_PG_ENSURE_CACHE | 1 | 1 | same |
| JAC_API_LEAN_RESPONSE | 1 | 1 | same |
| JAC_TIMING_HEADERS | 1 | 1 | same |
| JAC_ACCESS_LOG | 0 | 0 | same |
| JAC_REPORT_ECHO | 0 | 0 | same |
| JAC_PROMOTED_PREDICATES | 1 | 1 | same |
| JAC_STREAM_LATERAL | 1 | unset | default1 in final |
| JAC_SQL_ACL | 1 | unset | default1 in final |
| JAC_FUSED_FEED | 1 | unset | default1 in final |
| JAC_STICKY_DENY | 1 | unset | constant True in final |
| JAC_EDGE_ONLY_DIRTY | unset on CONTROL | unset | native-PG branch active; env retired |
| JAC_RO_WALKERS | empty string | unset | parser raw value constant empty in final; EffectPass stamps apply |
| JAC_LAZY_TXN | unset, original default off | unset | final default on from c12ba889d |
| PERF | 1, shell configuration selector | unset | runtime has no PERF read site |

The LAZY_TXN default changes between the historical and final runtime, as
recorded by `session0904/flags/RESULT.md` and
`runtimelib/impl/context.impl.jac`. It is part of the selected final-runtime
configuration. The comparison table retains historical CONTROL as its named
reference; timings need not be equal across the different runtime versions.

W3 uses native `load_feed_page` (original PG arm leaves PF_FEED_WALKER empty).
W1 uses `load_feed_chain`, matching the original PG read walker selection.
Each cell restarts a fresh app process, checks100-user seed-derived correctness,
then executes the original110warm and500/1000timed requests.

## Primary historical-recipe group

`original_recipe.py` selects actual sourcead469c988 through `jac314-ad469`,
restores the original app89366720 and main module before leaf removal,
sets STREAM_LATERAL/SQL_ACL/FUSED_FEED/STICKY_DENY to1 and RO_WALKERS empty,
and leaves LAZY_TXN/EDGE_ONLY_DIRTY unset. In this historical source,
LAZY_TXN unset is off and EDGE_ONLY_DIRTY unset is on for PgStore.
The source revision and actual environment are recorded in each result.
