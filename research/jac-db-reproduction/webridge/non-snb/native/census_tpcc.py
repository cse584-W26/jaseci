"""Actual native TPC-C request/ordered SQL census on a fresh template clone."""
import pathlib,json,sys,time,subprocess,gzip,types,hashlib
import psycopg,httpx
R=pathlib.Path(__file__).resolve().parent;REPRO=R.parents[2];sys.path[:0]=[str(R.parent),str(REPRO/'benchmark/scripts')]
from measurement_lease import lease
import tpcc_run as T
DB='jac_non_snb_tpcc_census_20261020';SNAP='jac_non_snb_tpcc_initial_20261020';log=REPRO/'dbcache/pg/main/server.log';plan=json.loads((R.parent/'tpcc-plan-900.json').read_text());selected=[{'label':label,'plan_idx':idx,'transaction':plan[idx]}for label,idx in [('payment_name_GC',0),('new_order_rollback',1),('payment_id_GC',3),('new_order_5',28),('new_order_15',35),('payment_name_BC',50),('payment_id_BC',54)]]
from tpcc_common import targets,state,reset
from tpcc_state import snapshot
with lease('native TPC-C operation census',R/'tpcc-census-lease.json'):
 out=R/'tpcc-census';out.mkdir(exist_ok=False);rows=[];jt=targets();cmd=[sys.executable,str(R/'service.py')]
 class Recorder:
  def __init__(self,c):self.c=c
  def post(self,path,**kw):
   self.path=path;self.body=kw['json'];self.response=self.c.post(path,**kw);return self.response
 for item in selected:
  reset(DB);folder=out/item['label'];folder.mkdir()
  admin=psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname='postgres',autocommit=True)
  admin.execute(psycopg.sql.SQL('ALTER DATABASE {} SET log_min_duration_statement=0').format(psycopg.sql.Identifier(DB)))
  initial=state(DB)
  try:
   subprocess.run([*cmd,'start','--variant','baseline','--database',DB],check=True)
   with httpx.Client(base_url='http://127.0.0.1:18132',timeout=300)as c:
    rc=Recorder(c)
    for iteration in range(3):
     before=state(DB);pids=admin.execute('SELECT pid FROM pg_stat_activity WHERE datname=%s',(DB,)).fetchall();offset=log.stat().st_size;t=time.monotonic_ns();wall=time.time_ns();result=T.one_txn(rc,'jaseci-pg',item['transaction'],{'Authorization':'Bearer '+jt.tokens['w1']},jt);end=time.monotonic_ns();time.sleep(.1)
     with log.open('rb')as f:f.seek(offset);raw=f.read()
     gzip.open(folder/(str(iteration)+'.sql.log.gz'),'wb').write(raw)
     after=state(DB);row=item|{'iteration':iteration,'cold':iteration==0,'state_before':before,'state_after':after,'backend_pids':pids,'start_wall_ns':wall,'client_ms':(end-t)/1e6,'path':rc.path,'body':rc.body,'status':rc.response.status_code,'headers':dict(rc.response.headers),'response':rc.response.json(),'driver_result':result};rows.append(row);(out/'rows.json').write_text(json.dumps(rows,indent=2));print(item['label'],iteration,rc.response.status_code,flush=True)
  finally:
   subprocess.run([*cmd,'stop','--variant','baseline'],check=True)
   admin.execute(psycopg.sql.SQL('ALTER DATABASE {} RESET log_min_duration_statement').format(psycopg.sql.Identifier(DB)));admin.close()
  final=state(DB);manifest=snapshot(DB,folder/'after-three-state');(folder/'state.json').write_text(json.dumps({'initial':initial,'after_three':final,'scope':'Fresh initial clone per class; same input executed three times; all mutations retained.','normalized_state':manifest},indent=2))
 (out/'cleanup.json').write_text(json.dumps({'service_stopped':True,'database_logging_restored':True,'fresh_clone_per_class':DB,'initial_snapshot':SNAP},indent=2))
