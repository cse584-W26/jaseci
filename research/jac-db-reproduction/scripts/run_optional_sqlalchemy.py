"""Run ORM comparisons and IC5 TTL diagnostic after the preceding suite."""
import json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=str(ROOT/'runtime/venv314/bin/python')
STAGES=[
 ('sqla-snb-start',['scripts/manage_optional.py','start','snb']),
 ('sqla-snb',['scripts/snb_canonical.py','--arm','sqlalchemy','--out-dir','results/snb-canonical/sqlalchemy']),
 ('sqla-snb-stop',['scripts/manage_optional.py','stop','snb']),
 ('pg-tpcc-stop',['scripts/manage.py','stop','pg-tpcc']),
 ('sqla-tpcc-reseed',['scripts/load_tpcc_postgres.py','--admin-dsn','postgresql://postgres@127.0.0.1:55436/postgres','--dsn','postgresql://postgres@127.0.0.1:55436/tpcc']),
 ('sqla-tpcc-start',['scripts/manage_optional.py','start','tpcc']),
 ('sqla-tpcc',['scripts/tpcc_gate.py','--arm','sqlalchemy','--base-url','http://127.0.0.1:18115','--dsn','postgresql://postgres@127.0.0.1:55436/tpcc','--out-dir','results/tpcc-sqlalchemy']),
 ('sqla-tpcc-stop',['scripts/manage_optional.py','stop','tpcc']),
 ('ttl-probe-on',['scripts/db_settings.py','duration']),
 ('ttl-probe',['scripts/ic5_ttl_probe.py']),
 ('ttl-probe-off',['scripts/db_settings.py','off']),
]
def main():
 print('Waiting for full suite and fixture smoke',flush=True)
 for _ in range(360):
  p=ROOT/'results/remaining-stage-progress.json';progress=json.loads(p.read_text()) if p.exists() else []
  if any(s['exit'] for s in progress):raise RuntimeError('Previous suite failed')
  if progress and progress[-1]['stage']=='fixture-smoke':break
  time.sleep(5)
 else:raise RuntimeError('Previous suite timeout')
 progress=[]
 for name,args in STAGES:
  print('START '+name,flush=True);start=time.time()
  with (ROOT/f'logs/stage-{name}.log').open('w') as f:r=subprocess.run([PY,*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  progress.append({'stage':name,'started_unix':start,'seconds':time.time()-start,'exit':r.returncode})
  (ROOT/'results/optional-stage-progress.json').write_text(json.dumps(progress,indent=2))
  print(f'DONE {name} exit={r.returncode} seconds={time.time()-start:.1f}',flush=True)
  if r.returncode:raise SystemExit(r.returncode)
if __name__=='__main__':main()
