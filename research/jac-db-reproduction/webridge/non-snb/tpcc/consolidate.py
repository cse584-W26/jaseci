#!/usr/bin/env python3
"""Complete 168-cell grid; stage failures and pending work remain explicit."""
import json,pathlib,time
H=pathlib.Path(__file__).resolve().parent;N=H.parent/'native';cases=json.loads((H/'case-status.json').read_text());timing=H/'timing/summary.json';measured=json.loads(timing.read_text())if timing.exists()else[];lookup={(r['program'],r['variant'],r['workload'],r['phase'],r['delay_ms']):r for r in measured};rows=[]
for row in json.loads((N/'tpcc-timing/summary.json').read_text()):
 folder=N/row['path'];rows.append({'family':'tpcc','workload':row['label'],'program':'jac','variant':row['variant'],'phase':'native','system':'Jac '+row['variant'],'delay_ms':row['delay_ms'],'status':'measured','warmup_count':row['warm'],'n':row['n'],'median_ms':row['client_median_ms'],'server_median_ms':row['server_median_ms'],'app_cpu_total_ms':row['app_cpu_total_ms'],'cpu_tick_ms':row['CPU_tick_ms'],'rows_path':str(folder/'rows.jsonl'),'correctness':str(folder/'independent-model-verification.json'),'full_after40_state':str(folder/'after40-state'),'method':'Native HTTP client latency; fresh initial state per cell; same operation40times,10warm+30measured; full state independently verified','source_summary':str(N/'tpcc-timing/summary.json')})
for case in cases:
 for phase in ['baseline','sp']:
  for delay in [0,2,10]:
   key=(case['program'],case['variant'],case['workload'],phase,delay)
   if key in lookup:rows.append(lookup[key]);continue
   status='failed-stage'if phase=='sp'and case['status']=='failed-stage'else'pending'
   rows.append({'family':'tpcc','workload':case['workload'],'program':case['program'],'variant':case['variant'],'phase':phase,'system':case['system']+(' + WeBridge with compatibility'if phase=='sp'else''),'delay_ms':delay,'status':status,'n':0,'median_ms':None,'case':case.get('case'),'failure':case.get('failure')if status=='failed-stage'else None,'pipeline':case.get('pipeline'),'source_status':str(H/'case-status.json'),'method':'No latency assigned to a compiler/runtime stage failure'if status=='failed-stage'else'Awaiting coordinated quiet measurement'})
assert len(rows)==168,len(rows);keys={(r['program'],r['variant'],r['workload'],r['phase'],r['delay_ms'])for r in rows};assert len(keys)==168
(H/'summary.json').write_text(json.dumps(rows,indent=2));(H/'summary-manifest.json').write_text(json.dumps({'generated_wall_ns':time.time_ns(),'cells':168,'native_cells':42,'java_cells':126,'statuses':{status:sum(r['status']==status for r in rows)for status in sorted({r['status']for r in rows})},'terminal':all(r['status']!='pending'for r in rows)},indent=2));print((H/'summary-manifest.json').read_text())
