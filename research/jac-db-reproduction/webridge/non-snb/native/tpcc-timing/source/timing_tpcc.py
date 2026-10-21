"""Seven fixed original TPC-C classes, fresh initial state per quiet cell."""
import pathlib,json,sys,subprocess,time,os,signal,statistics,shutil,hashlib
import httpx,psycopg
R=pathlib.Path(__file__).resolve().parent;REPRO=R.parents[2];W=R.parents[1];sys.path[:0]=[str(R),str(R.parent),str(REPRO/'benchmark/scripts')]
from measurement_lease import lease
from tpcc_common import targets,state,reset
from tpcc_state import snapshot
import tpcc_run as T
DB='jac_non_snb_tpcc_work_20261020';PORT=18532;plan=json.loads((R.parent/'tpcc-plan-900.json').read_text());representatives=[('payment_name_GC',0),('new_order_rollback',1),('payment_id_GC',3),('new_order_5',28),('new_order_15',35),('payment_name_BC',50),('payment_id_BC',54)];cmd=[sys.executable,str(R/'service.py')]
O=R/'tpcc-timing';O.mkdir(exist_ok=True)
def cpu(pid):
 x=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split();return(int(x[11])+int(x[12]))*1000/os.sysconf('SC_CLK_TCK')
def calibration(host,port):
 with psycopg.connect(host=host,port=port,user='jac',dbname=DB,autocommit=True)as c:
  values=[]
  for i in range(40):
   start=time.monotonic_ns();assert c.execute('SELECT 1').fetchone()==(1,)
   if i>=10:values.append((time.monotonic_ns()-start)/1e6)
 return {'warm':10,'n':30,'samples_ms':values,'median_ms':statistics.median(values),'host':host,'port':port}
class Recorder:
 def __init__(self,c):self.c=c
 def post(self,*args,**kw):self.response=self.c.post(*args,**kw);return self.response
with lease('native TPC-C quiet seven-class delay sweep',O/'lease.json'):
 provenance=O/'source';provenance.mkdir(exist_ok=False);hashes={}
 for name in [pathlib.Path(__file__).name,'tpcc_common.py','tpcc_state.py','service.py']:
  original=R/name;shutil.copy2(original,provenance/name);hashes[name]=hashlib.sha256(original.read_bytes()).hexdigest()
 for name in ['app.jac','main.jac','import_data.jac','seed.py']:
  original=REPRO/'benchmark/tpcc/jaseci-pg'/name;shutil.copy2(original,provenance/name);hashes[name]=hashlib.sha256(original.read_bytes()).hexdigest()
 (provenance/'sha256.json').write_text(json.dumps(hashes,indent=2));summary=[]
 for delay in [0,2,10]:
  home=O/('delay-'+str(delay)+'ms');home.mkdir(exist_ok=False);pcmd=[sys.executable,str(W/'latency-comparison/proxy.py'),'--port',str(PORT),'--delay-ms',str(delay),'--unix','/tmp/jacpg-d6275e76eb/.s.PGSQL.5432','--receipt',str(home/'proxy.json')]
  handle=(home/'proxy.stdout').open('w');proxy=subprocess.Popen(pcmd,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   time.sleep(.5);assert proxy.poll()is None
   for variant in ['baseline','final']:
    for label,index in representatives:
     out=home/variant/label;out.mkdir(parents=True,exist_ok=False);assert shutil.disk_usage(R).free>15*1024**3;reset(DB);before=state(DB)
     if label==representatives[0][0]and variant=='baseline':(home/'calibration-before.json').write_text(json.dumps({'direct':calibration('/tmp/jacpg-d6275e76eb',5432),'proxy':calibration('127.0.0.1',PORT)},indent=2))
     with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname='postgres',autocommit=True)as admin:
      prior=admin.execute('SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=%s)AND setrole=0',(DB,)).fetchone();prior={}if not prior else dict(x.split('=',1)for x in prior[0]);(out/'settings-before.json').write_text(json.dumps(prior))
      for k,v in [('log_min_duration_statement','-1'),('log_statement','none'),('log_duration','off')]:admin.execute(psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(k),psycopg.sql.Literal(v)))
      rows=[]
      try:
       subprocess.run([*cmd,'start','--variant',variant,'--database',DB,'--db-host','127.0.0.1','--db-port',str(PORT)],check=True);jt=targets();pid=int((R/variant/'service.pid').read_text())
       for name in ['launch.json','source.json']:shutil.copy2(R/variant/name,out/name)
       with httpx.Client(base_url='http://127.0.0.1:18132',timeout=300)as c,(out/'rows.jsonl').open('w')as f:
        rc=Recorder(c)
        for iteration in range(40):
         if iteration==10:cpu_start=cpu(pid)
         start=time.monotonic_ns();wall=time.time_ns();ok,rollback,server_ms,result=T.one_txn(rc,'jaseci-pg',plan[index],{'Authorization':'Bearer '+jt.tokens['w1']},jt);row={'iteration':iteration,'warmup':iteration<10,'start_wall_ns':wall,'client_ms':(time.monotonic_ns()-start)/1e6,'server_ms':server_ms,'ok':ok,'rollback':rollback,'result':result,'status':rc.response.status_code,'headers':dict(rc.response.headers),'original_plan_index':index};rows.append(row);f.write(json.dumps(row)+'\n');f.flush();assert ok or(plan[index].get('invalid')and rollback)
       cpu_ms=cpu(pid)-cpu_start
      finally:
       try:subprocess.run([*cmd,'stop','--variant',variant],check=True)
       finally:
        for k in ['log_min_duration_statement','log_statement','log_duration']:
         sql=psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(k),psycopg.sql.Literal(prior[k]))if k in prior else psycopg.sql.SQL('ALTER DATABASE {} RESET {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(k));admin.execute(sql)
        restored=admin.execute('SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=%s)AND setrole=0',(DB,)).fetchone();restored={}if not restored else dict(x.split('=',1)for x in restored[0]);assert restored==prior;(out/'settings-restored.json').write_text(json.dumps({'exact_prior_restored':True,'before':prior,'after':restored},indent=2))
     after=state(DB);snapshot(DB,out/'after40-state');measured=rows[10:];entry={'label':label,'variant':variant,'delay_ms':delay,'warm':10,'n':len(measured),'server_median_ms':statistics.median(x['server_ms']for x in measured)if all(x['server_ms']is not None for x in measured)else None,'client_median_ms':statistics.median(x['client_ms']for x in measured),'app_cpu_total_ms':cpu_ms,'CPU_tick_ms':1000/os.sysconf('SC_CLK_TCK'),'path':str(out.relative_to(R)),'initial':before,'after40':after,'logging_restored':True,'service_stopped':True};(out/'summary.json').write_text(json.dumps(entry,indent=2));summary.append(entry);(O/'summary.json').write_text(json.dumps(summary,indent=2));print(label,variant,delay,entry['server_median_ms'],flush=True)
   (home/'calibration-after.json').write_text(json.dumps(calibration('127.0.0.1',PORT),indent=2))
  finally:
   if proxy.poll()is None:os.killpg(proxy.pid,signal.SIGTERM)
   try:proxy.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(proxy.pid,signal.SIGKILL);proxy.wait()
   handle.close();(home/'cleanup.json').write_text(json.dumps({'proxy_stopped':True,'returncode':proxy.returncode,'command':pcmd},indent=2))
