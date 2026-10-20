import json,os,subprocess,sys,time,signal
from pathlib import Path
import httpx
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];app=ROOT/'benchmark/snb/jaseci-pg';trace=HERE/'identity-trace.jsonl'
if trace.exists():raise RuntimeError('Refuse overwrite identity trace')
subprocess.run([sys.executable,str(ROOT/'scripts/manage.py'),'stop','jac'],check=True)
env=os.environ.copy();env.update(json.loads((ROOT/'logs/jac-launch.json').read_text())['environment']);env.update(PYTHONPATH=str(ROOT/'runtime/baseline-source/jac'),JAC_NO_DEV_SOURCE='1',JAC_NO_PRECOMPILE='1',XDG_CACHE_HOME=str(ROOT/'runtime/cache314-baseline'),JAC_LLVM_SHIM=str(ROOT/'runtime/lib/libjacllvm.so'),ALIGN_IDENTITY_TRACE=str(trace))
f=(HERE/'identity-probe-server.log').open('w');p=subprocess.Popen(['taskset','-c','16-17',sys.executable,str(HERE/'identity_probe.py')],cwd=app,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);(HERE/'identity-probe-launch.json').write_text(json.dumps({'pid':p.pid,'command':p.args,'source':env['PYTHONPATH']},indent=2))
try:
 for _ in range(120):
  if p.poll()!=None:raise RuntimeError('Probe startup failed')
  try:
   if httpx.get('http://127.0.0.1:18109/healthz').status_code==200:break
  except Exception:pass
  time.sleep(.25)
 else:raise RuntimeError('Probe startup timeout')
 tok=json.loads((app/'svc_token.json').read_text())['svc'];targets=json.loads((app/'targets_person.json').read_text());x=json.loads((HERE.parent/'inputs.json').read_text())[0]
 with httpx.Client(base_url='http://127.0.0.1:18109',timeout=30) as c:
  for i in range(3):
   r=c.post('/walker/ic5_new_forums',headers={'Authorization':'Bearer '+tok},json={'person_jid':targets[str(x['pid'])],'min_date':x['min_date']});r.raise_for_status();print('probe',i,r.status_code,flush=True)
finally:
 os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=15);f.close()
 subprocess.run([sys.executable,str(ROOT/'scripts/manage.py'),'start','jac','--variant','baseline'],check=True)
