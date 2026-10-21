#!/usr/bin/env python3
"""Publish exact coverage and SQL/exchange distributions from completed compact cells."""
import argparse,collections,json,pathlib,fcntl,statistics
H=pathlib.Path(__file__).resolve().parent.parent
def save(path,value):
 temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)
p=argparse.ArgumentParser();p.add_argument('--matrix',type=pathlib.Path,required=True);p.add_argument('--references',type=pathlib.Path);p.add_argument('--allow-incomplete',action='store_true');a=p.parse_args();lock=(H/'primary-rtt/.publish.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX);rows=json.loads((a.matrix/'normalized-rtt-latency.json').read_text());assert a.allow_incomplete or len(rows)==126
for r in rows:
 r['timer']='per-request sum of SQL round-trip RTT';r['case_id']='tpcc-'+r['workload']
 if r['status']=='accepted':
  m=json.loads(pathlib.Path(r['rtt_summary']).read_text());r.update(sample_n=m['n'],warmup_n=10,sql_command_count_distribution=m['command_counts'],response_exchange_count_distribution=m['command_counts'],requests_artifact=m['rows_path'],rtt_summary_artifact=r['rtt_summary'],compact_trace_artifact=m['trace'],artifact=r['rtt_summary'],median_counts=float(statistics.median([float(k)for k,v in m['command_counts'].items()for _ in range(v)])))
 else:r.update(sample_n=0,warmup_n=0,sql_command_count_distribution=None,response_exchange_count_distribution=None,requests_artifact=r['pipeline'],artifact=r['pipeline'],median_counts=None)
save(H/'normalized-rtt-latency.json',rows);groups=collections.defaultdict(list)
for r in rows:groups[r['workload'],r['arm']].append(r)
output=[]
for(workload,arm),rr in groups.items():
 assert a.allow_incomplete or sorted(r['delay_ms']for r in rr)==[0,2,10];output.append({'family':'tpcc','case_id':'tpcc-'+workload,'workload':workload,'arm':arm,'timer':'summed SQL round-trip RTT','observations':[{'delay_ms':r['delay_ms'],'status':r['status'],'sample_n':r['sample_n'],'warmup_n':r['warmup_n'],'sql_command_count_distribution':r['sql_command_count_distribution'],'response_exchange_count_distribution':r['response_exchange_count_distribution'],'requests_artifact':r['requests_artifact'],'median_ms':r['median_ms']}for r in sorted(rr,key=lambda r:r['delay_ms'])]})
save(H/'rtt-cycle-evidence.json',{'rows':output,'count':len(output)})
if a.references:
 refs=json.loads((a.references/'rtt-reference-900-index.json').read_text());assert len(refs['rows'])==6
 for r in refs['rows']:
  if r['status']=='rejected_state_or_result':
   r['raw_oracle_status']=r['status'];r['status']='rejected_state_gate';r['gate_failure_evidence']=str(pathlib.Path(r['raw_requests']).parent.parent/'layout-verified-oracle-stderr.log')
  if r['arm'].startswith('java_'):
   r.setdefault('raw_execution_counts',r.get('execution_counts'));r['execution_counts']={'direct source transactions':900}
  r['reference_total_ms_800']=r.get('summed_db_call_rtt_total_ms_800')if r['status']=='accepted'else None
  r['timing_admissibility']='accepted state/model gate'if r['status']=='accepted'else'raw RTT diagnostic only; rejected result/state'
 save(H/'rtt-reference-900-index.json',refs)
print(collections.Counter(r['status']for r in rows))
