#!/usr/bin/env python3
"""Normalize the complete compact-RTT matrix and count evidence from the same requests."""
import argparse,collections,json,pathlib,subprocess,sys
H=pathlib.Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('--summary',required=True,type=pathlib.Path);p.add_argument('--allow-incomplete',action='store_true');a=p.parse_args();target=H/'normalized-rtt-results.json'
subprocess.run([sys.executable,str(H/'normalize_results.py'),str(a.summary),'--out',str(target),*([]if a.allow_incomplete else['--require-complete']),'--replacement-list',str(H/'clean-charset-replacement-inputs.json')],check=True)
data=json.loads(target.read_text());data.update(primary_metric='median of per-request summed complete SQL command RTT',timer='compact SQL round-trip sum',instrumentation='compact-protocol-rtt-v1');target.write_text(json.dumps(data,indent=2)+'\n')
for cell in data['cells']:
 cell.update(sample_n=cell['measured_count'],warmup_n=cell['warmup_count'],requests_artifact=cell['artifact'])
 if cell['status']=='accepted':
  measured=[json.loads(line)for line in pathlib.Path(cell['artifact']).read_text().splitlines()if line.strip()];measured=[r for r in measured if not r['warmup']]
  counts=dict(collections.Counter(r['command_count']for r in measured));rtt=json.loads(pathlib.Path(cell['primary_rtt']).read_text());cell.update(sql_command_count_distribution=counts,response_exchange_count_distribution=counts,rtt_summary_artifact=cell['primary_rtt'],compact_trace_artifact=rtt['trace'])
target.write_text(json.dumps(data,indent=2)+'\n')
index={}
for cell in data['cells']:
 if cell['method']!='latency':continue
 key='littlex-'+cell['workload']+'-t'+str(cell['tweets_per_user'])+('-w'+str(cell['write_percent'])if cell['workload']=='mixed'else'')
 arm=index.setdefault(key,{}).setdefault(cell['arm'],{'observations':[],'scope':'Complete-response wire cycles from the same compact-RTT measured requests at each declared delay; CALL is one outer command.'})
 obs={'delay_ms':cell['delay_ms'],'status':cell['status'],'artifact':cell['artifact'],'state_result_gate':cell.get('state_result_gate'),'result_gate':cell.get('source_result_oracle')}
 if cell['status']=='accepted':
  rows=[json.loads(s)for s in pathlib.Path(cell['artifact']).read_text().splitlines()];measured=[r for r in rows if not r['warmup']]
  obs.update(command_count_distribution=dict(collections.Counter(r['command_count']for r in measured)),sql_command_count_distribution=dict(collections.Counter(r['command_count']for r in measured)),response_exchange_count_distribution=dict(collections.Counter(r['command_count']for r in measured)),call_count_distribution=dict(collections.Counter(r['call_count']for r in measured)),sdk_enabled_at_end_requests=sum(bool(r['sdk_enabled_at_end'])for r in measured),measured_requests=len(measured),primary_rtt=cell['primary_rtt'])
 else:obs.update(failed_stage=cell.get('failed_stage'),pipeline_evidence=cell.get('pipeline_evidence'))
 arm['observations'].append(obs)
for case,arms in index.items():
 for arm,item in arms.items():
  counts=[int(n)for o in item['observations']for n in o.get('command_count_distribution',{})]
  item['display']=(str(min(counts))+('–'+str(max(counts))if min(counts)!=max(counts)else'')+' wire/request')if counts else next((o.get('failed_stage')for o in item['observations']if o.get('failed_stage')),'stage failure')
  item['display_by_delay_ms']={str(o['delay_ms']):(('/'.join(str(n)for n in sorted(int(k)for k in o.get('command_count_distribution',{})))+' wire/request')if o.get('command_count_distribution')else o.get('failed_stage','stage failure'))for o in item['observations']}
  item['artifact']=str(target)
assert a.allow_incomplete or sum(len(v)for v in index.values())==120
(H/'rtt-cycle-evidence.json').write_text(json.dumps(index,indent=2)+'\n')
