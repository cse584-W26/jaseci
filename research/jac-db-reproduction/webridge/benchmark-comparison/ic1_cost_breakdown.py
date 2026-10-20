#!/usr/bin/env python3
"""Offline IC1 baseline attribution; never connects to a database or runs a workload."""
import pathlib,json,statistics,collections,argparse,re
B=pathlib.Path(__file__).resolve().parent;W=B.parent
p=argparse.ArgumentParser();p.add_argument('--mysql-profile',type=pathlib.Path);a=p.parse_args()
def med(x):return statistics.median(x)if x else None
native=json.loads((W/'snb-extension/native/profiles/certified-requests.json').read_text());nr=[r for r in native if r['query']=='ic1'];ng=[]
for variant,delay in [(v,d)for v in ['baseline','final']for d in [0,2]]:
 rr=[r for r in nr if r['delay_ms']==delay and r['variant']==variant];categories=sorted({o['category']for r in rr for o in r['operations']});rows=json.loads((W/f'snb-extension/native/profiles/delay-{delay}ms/{variant}/requests/rows.json').read_text());rows=[r for r in rows if r['query']=='ic1'and not r['warmup']]
 ng.append({'variant':variant,'delay_ms':delay,'requests':len(rr),'median_client_ms':med([r['client_ms']for r in rows]),'median_application_server_ms':med([r['server_ms']for r in rows]),'median_server_execute_sum_ms':med([sum(o['execute_ms']for o in r['operations'])for r in rr]),'median_frontend_to_ready_delivery_sum_ms':med([sum((o['ready_delivery_mono_ns']-o['frontend_received_mono_ns'])/1e6 for o in r['operations'])for r in rr]),'categories':{c:{'commands_per_request':sorted({sum(o['category']==c for o in r['operations'])for r in rr}),'median_execute_sum_ms':med([sum(o['execute_ms']for o in r['operations']if o['category']==c)for r in rr])}for c in categories}})
quiet=[]
for delay in [0,2,10]:
 r=[json.loads(l)for l in(W/f'expansion/set-sql/timing/delay-{delay}ms/ic1/requests/rows.jsonl').read_text().splitlines()];r=[x for x in r if not x['warmup']and x['phase']=='baseline'];quiet.append({'delay_ms':delay,'n':len(r),'median_request_ms':med([x['ms']for x in r]),'median_thread_cpu_ms':med([x['thread_cpu_ms']for x in r]),'median_request_minus_thread_cpu_ms':med([x['ms']-x['thread_cpu_ms']for x in r]),'scope':'Request minus Java current-thread CPU combines database work, I/O, scheduling and other waits.'})
native_quiet=[r for r in json.loads((W/'snb-extension/native/latency/summary.json').read_text())if r['query']=='ic1']
out={'native_quiet':native_quiet,'status':'awaiting matched MySQL IC1 baseline protocol/P_S profile','native_instrumented':ng,'mysql_uninstrumented_request_cpu':quiet,'boundaries':['Native IC1 baseline and final both execute13 commands with the same SQL sequence. Quiet request timings differ materially from logging-on profiles; the controlled quiet and instrumented windows are reported separately.', 'Native execute timers come from PostgreSQL duration logs; they exclude Bind and application work.','MySQL P_S statement timer is inclusive server statement elapsed, not CPU.','Protocol complete_received and complete_delivered are separate boundaries; injected delay belongs only to the latter.','Java request thread CPU is directly measured; native quiet rows provide whole-process CPU per measured request.','Per-request paired quantities are aggregated before medians.','Native PostgreSQL and MySQL use different engines and SQL shapes; per-category timings describe their measured execution costs.']}
if a.mysql_profile:
 d=a.mysql_profile;profile=json.loads((d/'analysis.json').read_text());allrequests=[r for r in profile['requests']if r['phase']=='baseline'];pfs=[json.loads(l)for l in(d/'pfs.jsonl').read_text().splitlines()];top=[e for e in pfs if e['nest']is None and e.get('sql')];top.sort(key=lambda e:e['event']);cursor=0;matched=[]
 def norm(s):return ' '.join(s.split()).rstrip(';')
 def matches(e,sql):
  t=e['sql'];return norm(t)==norm(sql)or(len(t)==1024 and t.endswith('...')and sql.startswith(t[:-3]))
 rawrows=[json.loads(l)for l in(d/'run/requests/rows.jsonl').read_text().splitlines()]
 for r in allrequests:
  ops=[]
  for op in r['operations']:
   while cursor<len(top)and not matches(top[cursor],op['sql']):cursor+=1
   assert cursor<len(top),('No P_S exact SQL match',op['sql'][:150]);event=top[cursor];cursor+=1
   assert not event['error'];ops.append(dict(op,uuid_literal_count=len(re.findall(r"'[0-9a-f]{8}-[0-9a-f-]{27}'",op['sql'])),unique_uuid_literals=len(set(re.findall(r"'[0-9a-f]{8}-[0-9a-f-]{27}'",op['sql']))),pfs_event_id=event['event'],pfs_SQL_match=('exact'if norm(event['sql'])==norm(op['sql'])else'1024-character truncated SQL prefix plus ordered dedicated-thread event'),pfs_SQL_text=event['sql'],pfs_server_ms=event['timer_ps']/1e9,pfs_rows_examined=event['rows_examined'],pfs_rows_sent=event['rows_sent'],pfs_no_index_used=event.get('no_index',event.get('no_index_used')),pfs_no_good_index_used=event.get('no_good_index',event.get('no_good_index_used'))))
  if r['warmup']:continue
  raw=next(x for x in rawrows if x['phase']==r['phase']and x['iteration']==r['iteration']);wire=sum(o['complete_delivered_ms']for o in ops);matched.append({'iteration':r['iteration'],'request_ms':r['instrumented_request_ms'],'request_thread_cpu_ms':raw['thread_cpu_ms'],'protocol_received_sum_ms':sum(o['complete_received_ms']for o in ops),'protocol_delivered_sum_ms':wire,'server_stmt_sum_ms':sum(o['pfs_server_ms']for o in ops),'request_minus_delivered_spans_ms':r['instrumented_request_ms']-wire,'operations':ops})
 categories=sorted({o['category']for r in matched for o in r['operations']});agg={}
 for c in categories:
  agg[c]={'commands_per_request':sorted({sum(o['category']==c for o in r['operations'])for r in matched})}
  for key in ['pfs_server_ms','pfs_rows_examined','pfs_rows_sent','complete_received_ms','complete_delivered_ms','returned_rows','response_wire_bytes']:
   agg[c]['median_sum_'+key]=med([sum(o[key]for o in r['operations']if o['category']==c)for r in matched])
 out.update(mysql_profile_path=str(d),mysql_matched_requests=matched,mysql_categories=agg,status='Per-command dedicated-thread ordered SQL matching verified, with explicit truncated-prefix labels')
(B/'ic1-cost-breakdown.json').write_text(json.dumps(out,indent=2)+'\n')
md=['# IC1 measured cost breakdown','',out['status'],'','## Existing evidence','', '| Delay | MySQL direct median ms | Current-thread CPU ms | Paired elapsed minus thread CPU ms |','|---:|---:|---:|---:|']
for r in quiet:md.append('| %s | %.3f | %.3f | %.3f |'%(r['delay_ms'],r['median_request_ms'],r['median_thread_cpu_ms'],r['median_request_minus_thread_cpu_ms']))

if a.mysql_profile:
 md+=['','## Instrumented MySQL per-category medians','','| Category | Commands | Server statement ms | Rows examined | Rows sent | Complete received ms | Complete delivered ms |','|---|---:|---:|---:|---:|---:|---:|']
 for c,r in out['mysql_categories'].items():md.append('| %s | %s | %.3f | %s | %s | %.3f | %.3f |'%(c,r['commands_per_request'],r['median_sum_pfs_server_ms'],r['median_sum_pfs_rows_examined'],r['median_sum_pfs_rows_sent'],r['median_sum_complete_received_ms'],r['median_sum_complete_delivered_ms']))
 md+=['','Statement matches use exact normalized SQL or the explicitly labeled 1024-character truncated prefix in dedicated-thread event order; warmup events are matched before selecting measured requests. Per-request raw sums and residuals are retained in JSON.']
md+=['','## Measurement boundaries','']+['- '+x for x in out['boundaries']]
md+=['','## Native PostgreSQL instrumented request medians','','| Variant | Delay ms | HTTP client ms | Application server ms | Execute sum ms | Frontend to Ready delivery sum ms |','|---|---:|---:|---:|---:|---:|']
for r in ng:md.append('| %s | %s | %.3f | %.3f | %.3f | %.3f |'%(r['variant'],r['delay_ms'],r['median_client_ms'],r['median_application_server_ms'],r['median_server_execute_sum_ms'],r['median_frontend_to_ready_delivery_sum_ms']))
md+=['','## Attribution scope','','Each measured MySQL request’s seven commands are matched to dedicated-thread P_S events in execution order. The three adjacency reads and final Person projection dominate measured server elapsed. Their row metrics and completion intervals appear above. Native13-command BFS includes an early first-name endpoint filter and later projection of candidate matches; the conventional7-command reference applies its named-person projection after building the BFS frontiers. These are distinct SQL forms over the shared logical graph. Request elapsed outside measured protocol spans is recorded as an unassigned application/driver gap.','', 'Elapsed minus thread CPU combines server execution, blocking and scheduling. Existing PostgreSQL duration logging supplies execution elapsed; native quiet receipts supply process-level CPU.']
(B/'ic1-cost-breakdown.md').write_text('\n'.join(md)+'\n')
