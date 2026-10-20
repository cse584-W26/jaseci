#!/usr/bin/env python3
"""Render the measured matrix and operation map as a reviewable report."""
import pathlib,json
R=pathlib.Path(__file__).resolve().parent;D=json.loads((R/'results.json').read_text())
assert D['complete'],'Wait for every timing cell or measured compilation failure'
queries=['is1','is2','is3','ic1','ic2','ic13'];names={'jac-baseline':'Jac original','jac-final':'Jac final','full-baseline':'Java full','full-sp':'WeBridge full','pruned-baseline':'Java pruned','pruned-sp':'WeBridge pruned','set-baseline':'Java set-oriented','set-sp':'WeBridge set-oriented'}
lines=['# Jac and WeBridge on seven existing SNB workloads','',
'The six-query extension covers IS1, IS2, IS3, IC1, IC2 and IC13, alongside the completed IC5 study. It measures eight configurations and distinguishes relational query combination from moving a database-access sequence inside a stored procedure.','',
'**Observed native result:** original and final Jac emit identical ordinary SQL sequences for all six new representative inputs. Their measured latencies remain close. IC5 is the observed case where the final runtime reduces the sequence from 38 to 14 SQL cycles.','',
'## Method and correctness','',
'Original twenty-row parameter collections and historical canonical hashes are frozen. All 240 native original/final, 240 full/pruned Java and 120 conventional SQL result gates pass. Generated procedures are validated on the declared original index0 input; direct-program gates cover twenty inputs. Timing uses original index0, with nonempty outputs for every query, ten warmups and thirty measured requests for fast cells at 0/2/10 ms added database response delay. Slow generated procedures receive three actual fifteen-second bounded attempts per condition, with censored durations and verified server-session cleanup. Actual returned result objects accompany completed timing rows.','',
'The query-complete matched fixture has 1,475,843 anchors: all Person/Knows records, the relevant authored messages and full ReplyOf ancestor/author closure, locations, endpoints and owner roots. Thirteen logical fields round-trip exactly through both loaders. All Java arms share the materialized adjacency/person/message relations and uniform UUID collation. The IC5 companion study uses its separate 460,984-anchor fixture.','',
'Jac runs on PostgreSQL and the Java/WeBridge configurations run on MySQL 5.7. Within each pair, source, engine and data stay fixed. Jac timing adds the server request and commit spans; Java timing measures its JDBC request span. HTTP client latency and Java thread CPU are retained separately. The delay proxy path is shared across the 0/2/10 conditions, with actual SELECT1 calibration. Instrumented protocol/P_S runs are separate from quiet timing.','',
'Full Java follows the ordinary native access sequence. IC13 also has an observed periodic PostgreSQL schema guard, retained separately in native profiles. Pruned Java removes the declared Jac identity/ACL/schema/hydration overhead. Conventional SQL expresses query-specific joins, projections and bounded topK/path work. IS2/IC2 already use explicit Jac database builtins; these source choices belong to the baseline.','',
'## Latency matrix','',
'Completed cells report median request milliseconds. Censored cells record three first requests beyond the fifteen-second bound, before SP warmup completes.','']
for q in queries:
 lines += ['### '+q.upper(),'','| Configuration | 0 ms | +2 ms | +10 ms | Actual sync cycles |','|---|---:|---:|---:|---|']
 for s,n in names.items():
  cells=[next(x for x in D['latency']if(x['query'],x['system'],x['delay_ms'])==(q,s,d))for d in [0,2,10]];values=[f"{x['median_ms']:.3f}"if x.get('median_ms')is not None else x['status']for x in cells];cycle=D['cycles'][q].get(s,{}).get('display','incomplete CALL'if q=='ic1'and s.endswith('-sp')else 'not captured');lines.append('| '+' | '.join([n,*values,cycle])+' |')
 lines+=['']
lines += ['## Which operations are combined?','',
'All native profiles match SQL against the request-owned backend log and prove the next command follows prior ReadyForQuery delivery. Ordinary counts are IS1 7, IS2 24, IS3 12, IC1 13, IC2 33 and IC13 14. In one +2ms profile per native variant, IC13 executes a schema TTL guard and reaches 15 cycles.','']
for q in queries:
 lines+=['### '+q.upper(),'',' '.join(D['query_analysis'][q].values()),'','| Native category | Actual executions per profiled request |','|---|---:|']
 for cat,x in D['native_operations'][q].items():lines.append('| '+cat+' | '+(str(x['min'])if x['min']==x['max']else f"{x['min']}–{x['max']}")+' |')
 lines+=['']
lines += ['## Actual WeBridge pipeline and profiling','',
'Every selected procedure comes from the original record/replay/synthesis/install pipeline. The configured capture region is after the session SET and before COMMIT; START/SET/COMMIT remain three outer client commands. Cold callable-statement metadata queries remain in warmup records; measured requests check actual query counts, one CALL and procedure activation through the request end. Concrete compiler failures, compatibility overlays, graph/source/class hashes and selected cases are preserved.','',
'MySQL traces count command-to-complete-response cycles separately from frames, result sets and bytes. Performance Schema collection unions thread/event IDs and checks the observed CALL range before assigning nested operations. Business table SELECTs and cursor materializations, replay/result SELECTs and stored-program control events have separate categories. Parent CALL timers include descendants.','',
'## Measured IC1 procedure overhead','', 'The pruned IC1 generated procedure has cursor loops with 10, 2,750 and 9,009 independent row-dispatch IF branches. Each loop scans all branches for every counter value through its exit: sum N(N+1) = 88,736,450 equality checks. One instrumented CALL completed with the correct result, using 129.396 seconds inside MySQL (129.883 seconds at the JDBC request boundary). Raw Performance Schema counters and generated-source bounds support the explanation. A separate control with statement/sp instrumentation disabled exceeded the fifteen-second request bound and was terminated on its verified owned connection. The completed instrumented duration and quiet censored samples retain distinct labels.','', '## Reproduction and evidence','',
'Run `python benchmark-comparison/verify_results.py --java-timing`, then `python benchmark-comparison/collect_results.py` and `python benchmark-comparison/build_pdf.py`. The independent receipts rehash actual outputs against `historical-hashes.json` and recompute reported values from raw data. See [artifact guide](README.md), [results JSON](results.json), [new-query PDF](jac-webridge-snb-comparison.pdf), and the [IC5 companion report](../roundtrip-comparison/REPORT.md).','',
'`archive-manifest.json` in the parent directory records included SHA256 values. Query source snapshots, generated procedures, actual timing rows, payload-free framing, SQL catalogs, failure logs, calibration and cleanup receipts accompany this report.','']
cost_lines=['## IC1: actual query work on the same MySQL fixture','',
'Full/pruned Java first selects twenty first-name candidate IDs, expands three frontiers, then projects eighteen matching people. The conventional reference expands the same frontiers and applies its final predicate over 9,036 visited UUIDs. Its last query examines 9,932 Person rows and returns eighteen. The raw P_S query flag records NO_INDEX_USED=1 for that conventional projection.','',
'| Java variant | Quiet 0ms request median | Profile frontier statements | Profile final projection | Final rows examined |',
'|---|---:|---:|---:|---:|']
matched=json.loads((R/'ic1-same-engine-comparison.json').read_text())
for variant,key in [('full','full'),('pruned','pruned'),('conventional','set')]:
 cats=matched[variant]['categories'];front=cats['closure.frontier_adjacency'];proj=cats['person.filter_or_projection'if variant=='conventional'else'anchor.projection'];quiet=next(x['median_ms']for x in D['latency']if(x['query'],x['system'],x['delay_ms'])==('ic1',key+'-baseline',0))
 cost_lines.append(f"| {variant} | {quiet:.3f}ms | {front['median_sum_pfs_server_ms']:.3f}ms | {proj['median_sum_pfs_server_ms']:.3f}ms | {proj['median_sum_pfs_rows_examined']} |")
cost_lines+=['','These columns retain separate quiet and instrumented windows. Each profiled frontier sequence examines 175,262 rows and returns 11,769 rows. Native original/final quiet IC1 medians are about 37 ms, while their logging/protocol profiles have materially larger timings; the measured same-engine SQL contrast above isolates a different per-query work choice. See ic1-cost-breakdown.json and ic1-same-engine-comparison.json for paired per-request quantities and exact SQL hashes.','',
'## IC13: actual remaining procedure interval','',
'| Variant | Profile CALL median | Instrumented child statements | Paired remaining CALL interval |',
'|---|---:|---:|---:|']
cost=json.loads((R/'ic13-cost-breakdown.json').read_text())
for variant in ['full','pruned','conventional']:
 profile=next(x for x in cost['mysql_profiles']if x['kind']==variant);g=next(x for x in profile['groups']if x['phase']=='sp');cost_lines.append(f"| {variant} | {g['CALL_parent_median_ms']:.3f}ms | {g['CALL_direct_child_sum_median_ms']:.3f}ms | {g['CALL_parent_minus_direct_children_median_ms']:.3f}ms |")
cost_lines+=['','Full/pruned profiles observe actual table statements and cursor opens with stored-program control events disabled. Their remaining approximately 2.1 seconds include uninstrumented cursor/control and other procedure runtime work. The generated source has approximately 4.85 million row-index checks at recorded cursor sizes. The conventional CASE/EXISTS query instead performs bounded path tests inside one scalar-returning SQL statement. Exact observed operations, instrument settings and per-request residual calculations are in ic13-cost-breakdown.json.','']
position=lines.index('## Reproduction and evidence');lines[position:position]=cost_lines

(R/'REPORT.md').write_text('\n'.join(lines))
