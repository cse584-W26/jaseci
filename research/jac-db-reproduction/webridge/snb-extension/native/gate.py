"""All original inputs on the unchanged Jac workload and matched PG graph."""
import argparse,pathlib,subprocess,sys,json,time,hashlib,shutil
import httpx
R=pathlib.Path(__file__).resolve().parent;J=R.parents[1]/'jac-comparison'
p=argparse.ArgumentParser();p.add_argument('--variant',required=True,choices=['baseline','final']);p.add_argument('--attempt',default='canonical');a=p.parse_args();out=R/'gates'/(a.variant+'-'+a.attempt);out.mkdir(parents=True,exist_ok=False);inputs=json.loads((R.parent/'inputs-all20.json').read_text());rows=[]
def service(action):
 cmd=[sys.executable,str(J/'service.py'),action,'--variant',a.variant,'--database','jac_webridge_matched_six_20261020'];r=subprocess.run(cmd,capture_output=True,text=True);(out/(action+'.stdout')).write_text(r.stdout);(out/(action+'.stderr')).write_text(r.stderr);assert r.returncode==0,r.stderr
try:
 service('start');shutil.copy2(J/a.variant/'launch.json',out/'launch.json');shutil.copy2(J/a.variant/'source.json',out/'source.json');token=json.loads((J/a.variant/'app/svc_token.json').read_text())['svc']
 with httpx.Client(base_url='http://127.0.0.1:18130',timeout=600)as c,(out/'rows.jsonl').open('w')as sink:
  for q in ['is1','is3','ic1','ic13','is2','ic2']:
   oracles=[]
   for x in inputs[q]:
    start=time.monotonic();r=c.post('/walker/'+x['walker'],json=x['body'],headers={'Authorization':'Bearer '+token});r.raise_for_status();data=r.json()['data'];result=data['reports'][0]if'reports'in data else data;sha=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest();row={'query':q,'idx':x['idx'],'variant':a.variant,'parity':sha==x['expected_canonical_sha256'],'canonical_sha256':sha,'expected_sha256':x['expected_canonical_sha256'],'result':result,'client_ms':(time.monotonic()-start)*1000,'headers':dict(r.headers)};rows.append(row);oracles.append(result);sink.write(json.dumps(row)+'\n');sink.flush();assert row['parity'],(q,x['idx'],result);print(json.dumps({'query':q,'idx':x['idx'],'parity':True}),flush=True)
   (out/(q+'-oracles.json')).write_text(json.dumps(oracles,indent=2))
finally:
 service('stop');shutil.copy2(J/a.variant/'server.log',out/'server.log');(out/'summary.json').write_text(json.dumps({'n':len(rows),'expected_n':120,'all_parity':len(rows)==120 and all(x['parity']for x in rows),'service_stopped':True},indent=2))
