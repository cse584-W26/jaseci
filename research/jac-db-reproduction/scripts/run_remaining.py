"""Serialize canonical SNB, richer profile, TPC-C and fixture validation."""
import json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=str(ROOT/'runtime/venv314/bin/python')
STAGES=[
 ('final-full-profile-on',['scripts/db_settings.py','duration']),
 ('final-full-profile',['scripts/profile_ic5_full.py','--tag','final-full-profile','--repeats','5','--warmups','2']),
 ('final-full-profile-off',['scripts/db_settings.py','off']),
 ('snb-canonical-jac',['scripts/snb_canonical.py','--arm','jaseci-pg','--out-dir','results/snb-canonical/jac']),
 ('snb-canonical-pg',['scripts/snb_canonical.py','--arm','postgres','--out-dir','results/snb-canonical/postgres']),
 ('tpcc-start',['scripts/manage.py','start','tpcc','--variant','final']),
 ('tpcc-jac',['scripts/tpcc_gate.py','--arm','jaseci-pg','--base-url','http://127.0.0.1:18108','--dsn','host=/tmp/jacpg-d6275e76eb user=jac dbname=jac_tpcc_bench_pg_7a18c172','--out-dir','results/tpcc-jac']),
 ('tpcc-stop',['scripts/manage.py','stop','tpcc']),
 ('fixture-smoke',['littlex/fixture_smoke.py','--execute']),
]
def main():
 print('Waiting for serialized SNB matrix completion',flush=True)
 for _ in range(360):
  p=ROOT/'results/snb-stage-progress.json'
  progress=json.loads(p.read_text()) if p.exists() else []
  if any(s['exit'] for s in progress):raise RuntimeError('SNB matrix failed')
  if progress and progress[-1]['stage']=='final-profile-off':break
  time.sleep(5)
 else:raise RuntimeError('SNB matrix completion timeout')
 progress=[]
 for name,args in STAGES:
  print('START '+name,flush=True);start=time.time()
  with (ROOT/f'logs/stage-{name}.log').open('w') as handle:r=subprocess.run([PY,*args],cwd=ROOT,stdout=handle,stderr=subprocess.STDOUT)
  progress.append({'stage':name,'started_unix':start,'seconds':time.time()-start,'exit':r.returncode})
  (ROOT/'results/remaining-stage-progress.json').write_text(json.dumps(progress,indent=2))
  print(f'DONE {name} exit={r.returncode} seconds={time.time()-start:.1f}',flush=True)
  if r.returncode:raise SystemExit(r.returncode)
if __name__=='__main__':main()
