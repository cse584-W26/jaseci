"""Quiet native six-query measurements, or separate instrumented protocol profiles."""
import argparse,pathlib,subprocess,sys,json,time,hashlib,shutil,os,gzip
import httpx,psycopg
R=pathlib.Path(__file__).resolve().parent;J=R.parents[1]/'jac-comparison';REPRO=J.parents[1];DB='jac_webridge_matched_six_20261020'
p=argparse.ArgumentParser();p.add_argument('--variant',required=True,choices=['baseline','final']);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--profile-control',type=pathlib.Path);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);inputs=json.loads((R.parent/'inputs-representative.json').read_text());rows=[];log=REPRO/'dbcache/pg/main/server.log';ctl=psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname='postgres',autocommit=True);old=ctl.execute('SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=%s)AND setrole=0',(DB,)).fetchone();prior={}if not old else dict(x.split('=',1)for x in old[0]);(out/'database-settings-before.json').write_text(json.dumps(prior));settings=['log_min_duration_statement','log_statement','log_duration']
def service(action):
 cmd=[sys.executable,str(J/'service.py'),action,'--variant',a.variant,'--database',DB,'--db-host','127.0.0.1','--db-port','18532'];r=subprocess.run(cmd,capture_output=True,text=True);(out/(action+'.stdout')).write_text(r.stdout);(out/(action+'.stderr')).write_text(r.stderr);assert r.returncode==0,r.stderr

def cpu(pid):
 x=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split();return(int(x[11])+int(x[12]))*1000/os.sysconf('SC_CLK_TCK')
try:
 for k,v in zip(settings,['0'if a.profile_control else'-1','none','off']):ctl.execute(psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(k),psycopg.sql.Literal(v)))
 service('start');shutil.copy2(J/a.variant/'launch.json',out/'launch.json');shutil.copy2(J/a.variant/'source.json',out/'source.json');token=json.loads((J/a.variant/'app/svc_token.json').read_text())['svc'];pid=int((J/a.variant/'service.pid').read_text());cpurows=[]
 with httpx.Client(base_url='http://127.0.0.1:18130',timeout=300)as c,(out/'rows.jsonl').open('w')as sink:
  for q,x in inputs.items():
   d=out/q;d.mkdir();n=13 if a.profile_control else 40
   for i in range(n):
    if i==10:cpustart=cpu(pid)
    tag='warmup-'+q if i<10 else'request-'+q+'-'+str(i-10)
    if a.profile_control:a.profile_control.write_text(tag)
    offset=log.stat().st_size;t=time.monotonic_ns();wall=time.time_ns();r=c.post('/walker/'+x['walker'],json=x['body'],headers={'Authorization':'Bearer '+token});elapsed=(time.monotonic_ns()-t)/1e6;r.raise_for_status();data=r.json()['data'];result=data['reports'][0]if'reports'in data else data;sha=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest();row={'query':q,'idx':0,'iteration':i,'warmup':i<10,'variant':a.variant,'request_tag':tag,'start_wall_ns':wall,'start_mono_ns':t,'end_mono_ns':time.monotonic_ns(),'client_ms':elapsed,'server_ms':float(r.headers['x-server-total-ms'])+float(r.headers.get('x-server-commit-ms',0)),'headers':dict(r.headers),'result':result,'canonical_sha256':sha,'expected_sha256':x['expected_canonical_sha256'],'parity':sha==x['expected_canonical_sha256']};rows.append(row);sink.write(json.dumps(row)+'\n');sink.flush();assert row['parity'],(q,result)
    if a.profile_control:
     time.sleep(.05)
     if i>=10:
      with log.open('rb')as f:f.seek(offset);raw=f.read()
      gzip.open(d/f'profile-{i-10}.log.gz','wb').write(raw)
     a.profile_control.write_text('idle')
   cpurows.append({'query':q,'measured_requests':n-10,'app_process_cpu_ms':cpu(pid)-cpustart,'tick_ms':1000/os.sysconf('SC_CLK_TCK'),'includes_inter_request_driver_housekeeping':True});print(json.dumps({'query':q,'variant':a.variant,'complete':True}),flush=True)
 (out/'measured-cpu.json').write_text(json.dumps(cpurows,indent=2))
finally:
 try:service('stop');shutil.copy2(J/a.variant/'server.log',out/'server.log')
 finally:
  for k in settings:
   sql=psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(k),psycopg.sql.Literal(prior[k]))if k in prior else psycopg.sql.SQL('ALTER DATABASE {} RESET {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(k));ctl.execute(sql)
  ctl.close();(out/'rows.json').write_text(json.dumps(rows,indent=2));(out/'cleanup.json').write_text(json.dumps({'logging_restored':True,'service_stopped':True,'all_parity':all(x['parity']for x in rows),'n':len(rows)},indent=2))
