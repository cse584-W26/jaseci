"""Repeat baseline arms using the original shared benchmark dependency lock."""
import json,os,socket,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=str(ROOT/'runtime/venv314/bin/python');LOCKED=str(ROOT/'runtime/venv-benchmark-locked/bin/python')
env=os.environ.copy();env['REPRO_BASELINE_PYTHON']=LOCKED
progress=[]
def stage(name,args):
 print('START '+name,flush=True);t=time.time()
 with (ROOT/f'logs/stage-{name}.log').open('w') as f:r=subprocess.run([PY,*args],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
 progress.append({'stage':name,'started_unix':t,'seconds':time.time()-t,'exit':r.returncode})
 (ROOT/'results/locked-stage-progress.json').write_text(json.dumps(progress,indent=2))
 print(f'DONE {name} exit={r.returncode} seconds={time.time()-t:.1f}',flush=True)
 if r.returncode:raise SystemExit(r.returncode)
print('Waiting for Neo4j pilot to finish',flush=True)
for _ in range(360):
 p=ROOT/'results/neo4j-stage-progress.json';r=json.loads(p.read_text()) if p.exists() else []
 if any(s['exit'] for s in r):raise RuntimeError('Neo4j pilot failed')
 if r and r[-1]['stage']=='neo4j-canonical' and not (ROOT/'logs/neo4j-http.pid').exists():break
 time.sleep(5)
else:raise RuntimeError('Neo4j pilot timeout')
stage('locked-pg-start',['scripts/manage.py','start','pg'])
stage('locked-snb-pg',['scripts/snb_canonical.py','--arm','postgres','--out-dir','results/locked/snb-canonical/postgres'])
stage('locked-sqla-start',['scripts/manage_optional.py','start','snb'])
stage('locked-snb-sqla',['scripts/snb_canonical.py','--arm','sqlalchemy','--out-dir','results/locked/snb-canonical/sqlalchemy'])
stage('locked-sqla-stop',['scripts/manage_optional.py','stop','snb'])
with socket.socket() as sock:sock.bind(('127.0.0.1',18114))
cmd=[LOCKED,'-m','uvicorn','scripts.snb_neo4j_app:app','--host','127.0.0.1','--port','18114','--no-access-log']
with (ROOT/'logs/locked-neo4j-http.log').open('w') as f:app=subprocess.Popen(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(ROOT/'logs/neo4j-http.pid').write_text(str(app.pid))
for _ in range(60):
 if app.poll() is not None:raise RuntimeError('Locked Neo4j app failed')
 try:
  with urllib.request.urlopen('http://127.0.0.1:18114/docs',timeout=2) as response:
   if response.status==200:break
 except Exception:time.sleep(1)
else:raise RuntimeError('Locked Neo4j app timeout')
stage('locked-snb-neo4j',['scripts/snb_canonical.py','--arm','neo4j','--out-dir','results/locked/snb-canonical/neo4j'])
import manage;manage.stop('neo4j-http')
subprocess.run(['docker','stop','jac-db-repro-snb-neo4j'],check=True,stdout=(ROOT/'logs/neo4j-stop.log').open('w'))
for arm,service,port in [('postgres','pg-tpcc',18112),('sqlalchemy','tpcc',18115)]:
 stage('locked-reseed-'+arm,['scripts/load_tpcc_postgres.py','--admin-dsn','postgresql://postgres@127.0.0.1:55436/postgres','--dsn','postgresql://postgres@127.0.0.1:55436/tpcc'])
 manager='scripts/manage.py' if arm=='postgres' else 'scripts/manage_optional.py'
 stage('locked-tpcc-start-'+arm,[manager,'start',service])
 stage('locked-tpcc-'+arm,['scripts/tpcc_gate.py','--arm',arm,'--base-url',f'http://127.0.0.1:{port}','--dsn','postgresql://postgres@127.0.0.1:55436/tpcc','--out-dir',f'results/locked/tpcc-{arm}'])
 stage('locked-tpcc-stop-'+arm,[manager,'stop',service])
print('Locked baseline suite complete',flush=True)
