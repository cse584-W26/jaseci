"""Manage only the processes started by this reproduction."""
import argparse,json,os,signal,subprocess,time,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'benchmark/snb/jaseci-pg'
PYTHON=Path(os.environ.get('REPRO_BASELINE_PYTHON', str(ROOT/'runtime/venv314/bin/python'))).expanduser().absolute()
def stop(name):
 p=ROOT/f'logs/{name}.pid'
 if p.exists():
  pid=int(p.read_text())
  try:
   command=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
   if str(ROOT) not in command:raise RuntimeError(f'PID {pid} not owned by reproduction: {command}')
   os.killpg(pid,signal.SIGTERM)
   for _ in range(150):
    try:
     state=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]
     if state=='Z':break
    except FileNotFoundError:break
    time.sleep(.1)
   else:raise RuntimeError(f'Owned service {name} did not exit after SIGTERM')
  except (ProcessLookupError,FileNotFoundError):pass
  p.unlink()
def start(name,variant):
 stop(name)
 env=os.environ.copy();env['PYTHONUNBUFFERED']='1'
 if name in ('jac','tpcc'):
  app=APP if name=='jac' else ROOT/'benchmark/tpcc/jaseci-pg'
  port=18109 if name=='jac' else 18108
  source=ROOT.parent/'jac-db/jac' if variant=='final' else ROOT/'runtime/baseline-source/jac'
  manifest=app/'jac.toml'
  s=manifest.read_text();import re
  s=re.sub(r'jaclang_source = ".*?"',f'jaclang_source = "{source}"',s);manifest.write_text(s)
  shutil.rmtree(app/'.jac/cache',ignore_errors=True)
  env.update(JAC_CACHE_HOME=str(ROOT/'dbcache'),JAC_PG_VERSION='18',JAC_PG_DIST='/home/baichuan/.cache/jac/pg/dist/linux-amd64-18.6.0',JAC_API_LEAN_RESPONSE='1',JAC_ACCESS_LOG='0',JAC_REPORT_ECHO='0',JAC_TIMING_HEADERS='1',JAC_PG_POOL='1',JAC_PG_ENSURE_CACHE='1',JAC_PG_DRIVER='psycopg',JAC_PROMOTED_PREDICATES='1',JAC_CTE_TRAVERSE='1',JAC_STICKY_DENY='1',JAC_RO_WALKERS='')
  for key in ('JAC_LAZY_TXN','JAC_EDGE_ONLY_DIRTY','JAC_DB_URL'):env.pop(key,None)
  cmd=[str(ROOT/'runtime/bin'/('jac314' if variant=='final' else 'jac314-baseline')),'start','main.jac','-p',str(port),'--no-client'];cwd=app;log=ROOT/f'logs/{name}-{variant}-boot.log';url=f'http://127.0.0.1:{port}/healthz'
 else:
  bench='snb' if name=='pg' else 'tpcc'
  port=18111 if name=='pg' else 18112
  env['SNB_DSN' if name=='pg' else 'TPCC_DSN']=f'postgresql://postgres@127.0.0.1:55436/{bench}'
  cmd=[str(PYTHON),'-m','uvicorn','app:app','--host','127.0.0.1','--port',str(port),'--no-access-log'];cwd=ROOT/f'benchmark/{bench}/postgres';log=ROOT/f'logs/{name}-http.log';url=f'http://127.0.0.1:{port}/docs'
 with log.open('w') as handle:p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
 (ROOT/f'logs/{name}.pid').write_text(str(p.pid))
 (ROOT/f'logs/{name}-launch.json').write_text(json.dumps({'variant':variant,'pid':p.pid,'command':cmd,'cwd':str(cwd),'environment':{k:v for k,v in env.items() if k.startswith('JAC_')}},indent=2))
 import urllib.request
 for _ in range(240):
  if p.poll() is not None:raise RuntimeError(f'{name} exited {p.returncode}; see {log}')
  try:
   with urllib.request.urlopen(url,timeout=2) as response:
    if response.status==200:print(f'{name} ready pid={p.pid} variant={variant}',flush=True);return
  except Exception:pass
  time.sleep(1)
 raise RuntimeError(f'HTTP startup timeout: {log}')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['start','stop']);ap.add_argument('service',choices=['jac','pg','tpcc','pg-tpcc']);ap.add_argument('--variant',choices=['final','baseline'],default='final');a=ap.parse_args()
 start(a.service,a.variant) if a.action=='start' else stop(a.service)
