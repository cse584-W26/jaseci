"""Checkpointed serial20-input gates for each cumulative overhead removal."""
import argparse,datetime,hashlib,json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXPERIMENT=HERE.parent
CONFIGS={'full':[],'no_auth':['auth'],'no_auth_acl':['auth','acl'],'no_auth_acl_schema':['auth','acl','schema'],'no_auth_acl_schema_hydration':['auth','acl','schema','hydration']}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--resume',type=Path);ap.add_argument('--order',default=','.join(CONFIGS));a=ap.parse_args();order=a.order.split(',')
 if set(order)!=set(CONFIGS) or len(order)!=len(CONFIGS):raise RuntimeError('Order must contain all five configurations once')
 out=a.resume.resolve() if a.resume else HERE/'ablations'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 if not a.resume:out.mkdir(parents=True,exist_ok=False)
 sha=hashlib.sha256((HERE/'PrunedIc5.java').read_bytes()).hexdigest();previous=json.loads((out/'summary.json').read_text()) if (out/'summary.json').exists() else {}
 if previous and previous['source_sha256']!=sha:raise RuntimeError('Resume source differs from recorded source')
 baseline=[json.loads(x) for x in (HERE/'java-all20-context-aligned.jsonl').read_text().splitlines()];base={(r['round'],r['idx']):r for r in baseline}
 summary={'source_sha256':sha,'configs':[],'execution_order':order,'interpretation':'Single diagnostic pass per configuration, with interleaved compiler CPU on9,19 and coordination pauses. Count/result gates; timings are not a randomized performance comparison.'}
 for name in order:
  flags=CONFIGS[name];folder=out/name;gate_path=folder/'gate.json'
  if gate_path.exists():
   entry=json.loads(gate_path.read_text())
   if not entry['gate_pass']:raise RuntimeError('Refuse resuming failed gate:'+name)
   summary['configs'].append(entry);continue
  t=time.monotonic();existing=folder.exists()
  if existing:
   exit_path=folder/'completed-child-exit.json'
   if not exit_path.exists():raise RuntimeError('Existing unfinished configuration requires explicit child completion receipt:'+name)
   receipt=json.loads(exit_path.read_text());code=receipt['returncode'];elapsed=receipt.get('elapsed_seconds')
  else:
   folder.mkdir();cmd=['taskset','-c','9,19',str(EXPERIMENT/'boot-jdk8/bin/java'),'-Dalignment.dir='+str(HERE),'-Dalignment.finalRepeatFirst=true',*['-Dpruned.'+flag+'=true' for flag in flags],'-cp',str(HERE/'classes')+':'+str(EXPERIMENT/'deps/*'),'PrunedIc5','0','19','1'];(folder/'launch.json').write_text(json.dumps({'command':cmd,'start_unix':time.time(),'flags':flags,'source_sha256':sha},indent=2))
   with (folder/'rows.jsonl').open('w') as stdout,(folder/'stderr.log').open('w') as stderr:p=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=900)
   code=p.returncode;elapsed=time.monotonic()-t
  rows=[json.loads(x) for x in (folder/'rows.jsonl').read_text().splitlines()];gate=[]
  for r in rows:
   ref=base[r['round'],r['idx']];hops={k:v for k,v in r['categories'].items() if k.startswith('hop:')};expected_hops={k:v for k,v in ref['categories'].items() if k.startswith('hop:')};gate.append({'round':r['round'],'idx':r['idx'],'parity':r['parity'],'independent_count':r['jdbc_calls']==r['server_questions'],'same_domain_hops':hops==expected_hops,'statements':r['jdbc_calls'],'categories':r['categories']})
  ok=code==0 and len(rows)==21 and all(r['parity'] and r['independent_count'] and r['same_domain_hops'] for r in gate)
  entry={'name':name,'flags':flags,'exit':code,'seconds':elapsed,'gate_pass':ok,'requests':len(rows),'observed_prefix_statements':sum(r['jdbc_calls'] for r in rows),'cold20_statements':sum(r['jdbc_calls'] for r in rows if r['round']==0) if sum(r['round']==0 for r in rows)==20 else None,'warm_repeat0_statements':next((r['jdbc_calls'] for r in rows if r['round']==1 and r['idx']==0),None),'rows':gate};summary['configs'].append(entry);gate_path.write_text(json.dumps(entry,indent=2));(out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in entry.items() if k!='rows'}),flush=True)
  if not ok:raise RuntimeError('Ablation gate failed:'+name)
 summary['all_pass']=all(c['gate_pass'] for c in summary['configs']);(out/'summary.json').write_text(json.dumps(summary,indent=2));(HERE/'latest-ablation.json').write_text(json.dumps({'directory':str(out),'summary':str(out/'summary.json')},indent=2));print('ALL ABLATIONS PASS',out,flush=True)
if __name__=='__main__':main()
