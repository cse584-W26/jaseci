#!/usr/bin/env python3
"""Read existing measured IC13 evidence; never executes database requests."""
import pathlib,json,statistics
B=pathlib.Path(__file__).resolve().parent;W=B.parent
med=statistics.median
native=json.loads((W/'snb-extension/native/profiles/certified-requests.json').read_text());native=[r for r in native if r['query']=='ic13'];n=[]
for variant in ['baseline','final']:
 for delay in [0,2]:
  rr=[r for r in native if r['variant']==variant and r['delay_ms']==delay]
  n.append({'variant':variant,'delay_ms':delay,'requests':len(rr),'commands':sorted({r['sql_executions']for r in rr}),'server_execute_sum_median_ms':med([sum(o['execute_ms']for o in r['operations'])for r in rr]),'front_to_ready_delivery_sum_median_ms':med([sum((o['ready_delivery_mono_ns']-o['frontend_received_mono_ns'])/1e6 for o in r['operations'])for r in rr]),'categories':rr[0]['categories']})
cells=json.loads((W/'expansion/set-sql/timing/summary.json').read_text());manual=[r for r in cells if r['query']=='ic13'];profiles=[]
for f in (B/'mysql-profile/results/ic13').glob('*/analysis.json'):
 d=json.loads(f.read_text());rr=[r for r in d['requests']if not r['warmup']];groups=[]
 for phase in sorted({r['phase']for r in rr}):
  rs=[r for r in rr if r['phase']==phase];cats=sorted({o['category']for r in rs for o in r['operations']})
  groups.append({'phase':phase,'requests':len(rs),'request_median_ms':med([r['instrumented_request_ms']for r in rs]),'categories':{c:{'command_count':sorted({sum(o['category']==c for o in r['operations'])for r in rs}),'complete_received_sum_median_ms':med([sum(o['complete_received_ms']for o in r['operations']if o['category']==c)for r in rs]),'complete_delivered_sum_median_ms':med([sum(o['complete_delivered_ms']for o in r['operations']if o['category']==c)for r in rs]),'returned_rows':sorted({sum(o['returned_rows']for o in r['operations']if o['category']==c)for r in rs})}for c in cats},'CALL_P_S':[r['P_S_CALL']for r in rs if r['P_S_CALL']], 'CALL_parent_median_ms':med([r['P_S_CALL']['parent_inclusive_ms']for r in rs if r['P_S_CALL']])if any(r['P_S_CALL']for r in rs)else None,'CALL_direct_child_sum_median_ms':med([sum(r['P_S_CALL']['direct_child_timer_ms'].values())for r in rs if r['P_S_CALL']])if any(r['P_S_CALL']for r in rs)else None,'CALL_parent_minus_direct_children_median_ms':med([r['P_S_CALL']['parent_inclusive_ms']-sum(r['P_S_CALL']['direct_child_timer_ms'].values())for r in rs if r['P_S_CALL']])if any(r['P_S_CALL']for r in rs)else None})
 profiles.append({'path':str(f),'kind':d['case']['kind'],'groups':groups})
out={'query':'ic13','native_instrumented':n,'conventional_uninstrumented':manual,'mysql_profiles':profiles,'interpretation':['Native and access-equivalent Java evaluate a frontier BFS bounded at six levels.','Conventional SQL evaluates one CASE with ordered EXISTS tests for path lengths one through six; first success gives minimum distance, identical endpoints return zero, otherwise minus one.','The conventional reference passes all 20 canonical inputs; different SQL plans are part of this comparison.','Actual P_S events establish executed predicate and dispatch counts.','Per-stage measurements distinguish protocol latency and server computation.','Instrumented P_S and wire timing are diagnostic; quiet latency medians are from separate runs.']}
(B/'ic13-cost-breakdown.json').write_text(json.dumps(out,indent=2)+'\n')
lines=['# IC13 measured SQL-form and cost comparison','']+['- '+x for x in out['interpretation']]+['','## Conventional quiet medians','','| Delay ms | Direct ms | Generated SP ms |','|---:|---:|---:|']
for delay in [0,2,10]:
 r={x['phase']:x for x in manual if x['delay_ms']==delay};lines.append('| %s | %.3f | %.3f |'%(delay,r['baseline']['median_ms'],r['sp']['median_ms']))
lines+=['','## Instrumented generated-procedure scope','','| Form | Request median ms | Inclusive CALL ms | Direct instrumented children ms | Paired CALL minus children ms |','|---|---:|---:|---:|---:|']
for p in profiles:
 for g in p['groups']:
  if g['CALL_parent_median_ms']is not None:lines.append('| %s | %.3f | %.3f | %.3f | %.3f |'%(p['kind'],g['request_median_ms'],g['CALL_parent_median_ms'],g['CALL_direct_child_sum_median_ms'],g['CALL_parent_minus_direct_children_median_ms']))
lines+=['','Business-only P_S records the executed statement and cursor-open events. The paired inclusive-CALL-minus-direct-children quantity records the remaining procedure interval, including uninstrumented control/dispatch and other unassigned procedure work. Exact source guard counts describe generated code size; observed P_S categories provide executed database-work counts.','', 'Detailed per-category command completion intervals and native server execute timings are retained in `ic13-cost-breakdown.json`. A complete server-cost attribution additionally requires matching baseline P_S statements to request boundaries and distinguishing inclusive CALL timing from child statement timing.']
(B/'ic13-cost-breakdown.md').write_text('\n'.join(lines)+'\n')
