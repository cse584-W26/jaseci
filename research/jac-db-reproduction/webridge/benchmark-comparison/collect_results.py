#!/usr/bin/env python3
"""Assemble the six-query matrix from measured files; reject unfinished cells."""
import argparse,json,pathlib,csv
R=pathlib.Path(__file__).resolve().parent;W=R.parent
P=argparse.ArgumentParser();P.add_argument('--allow-incomplete',action='store_true');a=P.parse_args()
read=lambda p:json.loads(p.read_text())
queries=['is1','is2','is3','ic1','ic2','ic13'];systems=['jac-baseline','jac-final','full-baseline','full-sp','pruned-baseline','pruned-sp','set-baseline','set-sp']
latency=[]
for x in read(W/'snb-extension/native/latency/summary.json'):
 latency.append({'query':x['query'],'system':'jac-'+x['variant'],'delay_ms':x['added_response_delay_ms'],'median_ms':x['server_median_ms'],'n':x['n'],'status':'measured','source':'snb-extension/native/latency/summary.json'})
coverage={q:{}for q in queries}
for path in ['snb-extension/java/case-status.json','expansion/set-sql/case-status.json']:
 for x in read(W/path):
  success=x['status']in ['success','selected-input-genuine-pipeline-passed'];coverage[x['query']][x['variant']]={'label':'Passed'if success else x.get('failed_stage')or x['status'],'status':x['status'],'source':path,'case':x.get('selected_case')or x.get('case_path'),'observations':x}
for path in ['snb-extension/java/timing/summary.json','expansion/set-sql/timing/summary.json']:
 if not(W/path).exists():continue
 for x in read(W/path):
  variant=x.get('variant','set');delay=x.get('delay_ms',x.get('added_response_delay_ms'));median=x.get('median_ms');assert median is not None or x.get('status')and(x.get('attempts')or x.get('failed_stage')),x
  latency.append({'query':x['query'],'system':variant+'-'+x['phase'],'delay_ms':delay,'median_ms':median,'n':x['n'],'status':'measured'if median is not None else x['status'],'attempts':x.get('attempts'),'timeout_paths':x.get('timeout_paths'),'source':path,'raw':x.get('rows_path')})
missing=[]
for q in queries:
 for s in systems:
  for d in [0,2,10]:
   found=[x for x in latency if(x['query'],x['system'],x['delay_ms'])==(q,s,d)];assert len(found)<=1,(q,s,d)
   if found:continue
   c=coverage[q].get(s.split('-')[0],{});label=c.get('label','pending')
   finalfailure=s.endswith('-sp')and c.get('status')in ['failed','failure','unsupported','failed-stage','runtime-timeout']
   item={'query':q,'system':s,'delay_ms':d,'median_ms':None,'status':label if finalfailure else 'pending','source':c.get('source')};latency.append(item)
   if not finalfailure:missing.append([q,s,d])
for q in queries:
 for v in ['full','pruned','set']:
  cells=[x for x in latency if x['query']==q and x['system']==v+'-sp']
  if cells and all(x.get('median_ms')is not None for x in cells):coverage[q][v]['label']='CALL verified'
  elif cells and all('timeout'in x['status'].lower()for x in cells):coverage[q][v]['label']='Generated; CALL >15s'
native=read(W/'snb-extension/native/profiles/operation-map.json');ops={x['query']:x['variants']['final']['categories']for x in native};cycles={q:{}for q in queries}
for x in native:
 q=x['query']
 for v,y in x['variants'].items():
  vals=sum(y['actual_flight_counts_by_delay'].values(),[]);cycles[q]['jac-'+v]={'display':str(min(vals))if min(vals)==max(vals)else f'{min(vals)}–{max(vals)}','actual_counts':vals,'replicates':len(vals),'source':'snb-extension/native/profiles/operation-map.json'}
profile=R/'mysql-profile/summary.json'
profile_data=read(profile)if profile.exists()else None
if profile_data:
 for cell in profile_data['cells']:
  v='set'if cell['variant']=='conventional'else cell['variant'];vs=cell['actual_cycles'];assert cell['measured_requests']==len(vs)==3
  cycles[cell['query']][v+'-'+cell['phase']]={'display':str(min(vs))if min(vs)==max(vs)else f'{min(vs)}–{max(vs)}','actual_counts':vs,'replicates':len(vs),'source':'benchmark-comparison/mysql-profile/'+cell['profile_path'],'wire_categories':cell['wire_categories'],'frames':cell['response_frames'],'response_wire_bytes':cell['response_wire_bytes'],'result_sets':cell['result_sets'],'P_S_CALL':cell['P_S_CALL']}
missing_profiles=[]
for q in queries:
 for v in ['full','pruned','set']:
  for phase in ['baseline','sp']:
   system=v+'-'+phase
   timed=all(x.get('median_ms')is not None for x in latency if x['query']==q and x['system']==system)
   if phase=='sp'and not timed:continue
   if system not in cycles[q]:missing_profiles.append([q,system])
# The profiler summary carries its own per-request evidence and operation map.
result={'scope':'Six additional SNB queries, original index0 timing, eight configurations','complete':not missing and not missing_profiles,'timing_complete':not missing,'missing_profiles':missing_profiles,'missing_cells':missing,'latency':latency,'coverage':coverage,'native_operations':ops,'cycles':cycles,'query_analysis':read(R/'query-analysis.json'),'mysql_profile':profile_data}
(R/'results.json').write_text(json.dumps(result,indent=2)+'\n')
with(R/'results.csv').open('w')as f:
 writer=csv.DictWriter(f,fieldnames=['query','system','delay_ms','median_ms','n','status','attempts','sync_cycles','source']);writer.writeheader()
 for x in latency:writer.writerow({k:x.get(k)for k in ['query','system','delay_ms','median_ms','n','status','attempts','source']}|{'sync_cycles':cycles[x['query']].get(x['system'],{}).get('display','')})
print(json.dumps({'timing_cells':len(latency),'measured':sum(x['status']=='measured'for x in latency),'pending':len(missing)}))
if(missing or missing_profiles)and not a.allow_incomplete:raise SystemExit('Unfinished timing or protocol cells; results.json retains explicit pending status')
