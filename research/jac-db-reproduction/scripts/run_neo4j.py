"""Dedicated Neo4j SF1 load and original-size canonical read experiment."""
import json,os,socket,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=str(ROOT/'runtime/venv314/bin/python')
def stage(name,cmd):
 print('START '+name,flush=True);t=time.time()
 with (ROOT/f'logs/stage-{name}.log').open('w') as f:r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 progress.append({'stage':name,'started_unix':t,'seconds':time.time()-t,'exit':r.returncode})
 (ROOT/'results/neo4j-stage-progress.json').write_text(json.dumps(progress,indent=2))
 print(f'DONE {name} exit={r.returncode} seconds={time.time()-t:.1f}',flush=True)
 if r.returncode:raise SystemExit(r.returncode)
print('Waiting for SQLAlchemy comparisons and TTL diagnostic',flush=True)
for _ in range(360):
 p=ROOT/'results/optional-stage-progress.json';previous=json.loads(p.read_text()) if p.exists() else []
 if any(s['exit'] for s in previous):raise RuntimeError('Previous suite failed')
 if previous and previous[-1]['stage']=='ttl-probe-off':break
 time.sleep(5)
else:raise RuntimeError('Previous suite timeout')
progress=[]
stage('neo4j-up',['docker','compose','-f','optional-baselines/compose.yml','-p','jac-db-reproduction','up','-d'])
subprocess.run(['docker','inspect','jac-db-repro-snb-neo4j'],stdout=(ROOT/'logs/neo4j-container.json').open('w'),check=True)
from neo4j import GraphDatabase
with GraphDatabase.driver('bolt://127.0.0.1:17687',auth=('neo4j','snbpassword')) as driver:
 for _ in range(120):
  try:driver.verify_connectivity();break
  except Exception:time.sleep(1)
 else:raise RuntimeError('Neo4j startup timeout')
 with driver.session() as s:
  count=s.run('MATCH (n) RETURN count(n) AS n').single()['n']
  if count:raise RuntimeError(f'Dedicated Neo4j already contains {count} nodes; inspect before resetting')
stage('neo4j-load',[PY,'-u','scripts/load_snb_neo4j.py'])
with GraphDatabase.driver('bolt://127.0.0.1:17687',auth=('neo4j','snbpassword')) as driver:
 with driver.session() as s:
  nodes=s.run('MATCH (n) RETURN count(n) AS n').single()['n'];rels=s.run('MATCH ()-[r]->() RETURN count(r) AS n').single()['n']
  components=[dict(r) for r in s.run('CALL dbms.components()')]
 (ROOT/'results/neo4j-load-counts.json').write_text(json.dumps({'nodes':nodes,'relationships':rels,'components':components},indent=2))
 assert (nodes,rels)==(3157618,7913932),(nodes,rels)
with socket.socket() as sock:sock.bind(('127.0.0.1',18114))
cmd=[PY,'-m','uvicorn','scripts.snb_neo4j_app:app','--host','127.0.0.1','--port','18114','--no-access-log']
with (ROOT/'logs/neo4j-http.log').open('w') as f:app=subprocess.Popen(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(ROOT/'logs/neo4j-http.pid').write_text(str(app.pid))
for _ in range(60):
 if app.poll() is not None:raise RuntimeError('Neo4j HTTP app failed')
 try:
  with urllib.request.urlopen('http://127.0.0.1:18114/docs',timeout=2) as response:
   if response.status==200:break
 except Exception:time.sleep(1)
else:raise RuntimeError('Neo4j HTTP app startup timeout')
stage('neo4j-canonical',[PY,'scripts/snb_canonical.py','--arm','neo4j','--out-dir','results/snb-canonical/neo4j'])
import manage
manage.stop('neo4j-http')
print('Neo4j reproduction complete',flush=True)
