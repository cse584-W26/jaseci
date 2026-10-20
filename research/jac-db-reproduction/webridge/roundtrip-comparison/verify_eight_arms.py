#!/usr/bin/env python3
"""Independently recompute every cell of both complete eight-configuration experiments."""
import json,pathlib,statistics,math,datetime,gzip,runpy,contextlib,io
R=pathlib.Path(__file__).resolve().parent;B=R.parent
read=lambda p:json.loads(p.read_text())
expected=read(B/'alignment/small-diagnostic/input.json')['expected'];pgexpected={'forums':[dict(zip(['forumId','title','postCount'],x))for x in expected]}
with contextlib.redirect_stdout(io.StringIO()):runpy.run_path(str(B/'latency-comparison/analyze.py'))
base=read(B/'latency-comparison/verified-six-arms.json');rows=list(base['rows']);main_requests=base['requests_checked'];reverse=[]
for reverse_order in [False,True]:
 root=B/'alignment/idiomatic'/('webridge-delay-reverse-results'if reverse_order else'webridge-delay-results')
 for delay in [0,2,10]:
  dest=root/f'delay-{delay}ms/idiomatic';raw=[json.loads(l)for l in(dest/'requests/rows.jsonl').read_text().splitlines()];assert len(raw)==80 and all(x['result']==expected and x['oracle_ok']for x in raw)
  assert read(root/f'delay-{delay}ms/proxy-cleanup.json')['stopped']and read(dest/'final-group-cleanup.json')['verified_empty']
  for phase in ['baseline','sp']:
   selected=[x for x in raw if x['phase']==phase];m=[x for x in selected if not x['warmup']];assert len(selected)==40 and len(m)==30
   assert all(x['questions']==4 and x['status_delta']['Com_call_procedure']==(phase=='sp')and(phase!='sp'or x['sp_enabled_at_end'])for x in m)
   ms=[x['ms']for x in m];item={'system':'Java set-oriented SQL'if phase=='baseline'else'WeBridge set-oriented SQL','delay_ms':delay,'median_ms':statistics.median(ms),'p95_ms':sorted(ms)[math.ceil(len(ms)*.95)-1],'commands':4,'n':30,'source':str((dest/'requests/rows.jsonl').relative_to(B))}
   (reverse if reverse_order else rows).append(item)
  if not reverse_order:main_requests+=len(raw)
# Exact protocol counts for every configuration; three measured requests for each MySQL arm.
protocol=[]
for dirname in ['mysql-results','mysql-idiomatic-results']:
 data=read(R/dirname/'protocol-analysis.json');assert data['all_checks_passed']
 for variant in sorted(set(x['variant']for x in data['requests'])):
  for phase in ['baseline','sp']:
   selected=[x for x in data['requests']if x['variant']==variant and x['phase']==phase and not x['warmup']];assert len(selected)==3
   keys=['command_response_cycles','server_response_frames','result_sets','server_response_wire_bytes','client_command_wire_bytes']
   assert all(all(x[k]==selected[0][k]for k in keys)for x in selected)
   item={'system':({'full':'Java full','pruned':'Java pruned','idiomatic':'Java set-oriented SQL'}if phase=='baseline'else{'full':'WeBridge full','pruned':'WeBridge pruned','idiomatic':'WeBridge set-oriented SQL'})[variant],'replicates':3,**{k:selected[0][k]for k in keys},'categories':selected[0]['categories'],'evidence':str((R/dirname/'protocol-analysis.json').relative_to(B))};protocol.append(item)
pg=read(B/'jac-comparison/roundtrip-profile/results/operation-map.json');flights=read(B/'jac-comparison/roundtrip-profile/results/flight-summary.json');assert pg['all_pass']and flights['all_pass']and len(flights['requests'])==12
for variant,name in [('baseline','Jac original'),('final','Jac SQL pushdown')]:
 data=pg['variants'][variant];matches=[x for x in flights['requests']if x['variant']==variant];assert len(matches)==6 and all(x['sql_executions']==data['sql_executions']and x['synchronization_flights']==data['sync_flights']for x in matches)
 protocol.append({'system':name,'replicates':6,'command_response_cycles':data['sync_flights'],'frontend_messages':data['frontend_messages'],'categories':data['categories'],'evidence':'jac-comparison/roundtrip-profile/results/operation-map.json'})
order=['Jac original','Jac SQL pushdown','Java full','WeBridge full','Java pruned','WeBridge pruned','Java set-oriented SQL','WeBridge set-oriented SQL'];rows.sort(key=lambda x:(order.index(x['system']),x['delay_ms']));protocol.sort(key=lambda x:order.index(x['system']));assert len(rows)==24 and len(protocol)==8 and main_requests==960
out={'all_checks_passed':True,'main_experiment_requests':main_requests,'additional_reverse_order_requests':240,'performance_rows':rows,'reverse_order_rows':reverse,'protocol_rows':protocol,'profile_measured_requests':30,'source':'Quiet timing and instrumented protocol profiles are separate experiments.'}
(R/'eight-arm-verification.json').write_text(json.dumps(out,indent=2)+'\n')
table='| Configuration | 0 ms | +2 ms | +10 ms | SQL / sync cycles |\n|---|---:|---:|---:|---:|\n'
for name in order:
 rr=[x for x in rows if x['system']==name];c=next(p['command_response_cycles']for p in protocol if p['system']==name);table+='| '+name+' | '+' | '.join(f"{x['median_ms']:.2f}"for x in rr)+f' | {c} |\n'
(R/'eight-arm-table.md').write_text(table);print(table);print('Main requests verified:',main_requests,'; reverse-order:',240,'; measured protocol:',30)
