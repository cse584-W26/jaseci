"""Original-source six-query instrumentation; graph version checked, setup separated."""
import pathlib,subprocess,sys,os,signal,time,json,gzip,re,hashlib
import httpx,psycopg
R=pathlib.Path(__file__).resolve().parent;W=R.parents[1];J=W/'jac-comparison';REPRO=W.parent;out=R/'source-census';out.mkdir(exist_ok=False);DB='jac_snb_bench_pg_fbdb3a2c';SOCKET='/tmp/jacpg-d6275e76eb';log=REPRO/'dbcache/pg/main/server.log';inputs=json.loads((R.parent/'inputs-representative.json').read_text());ctl=psycopg.connect(host=SOCKET,user='jac',dbname='postgres',autocommit=True);dc=psycopg.connect(host=SOCKET,user='jac',dbname=DB,autocommit=True)
def snapshot(name):
 t=time.monotonic();anchors=dc.execute("SELECT count(*),min(xmin::text::bigint),max(xmin::text::bigint),sum(xmin::text::bigint) FROM anchors").fetchone();catalog=dc.execute("SELECT c.relname,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE NOT t.tgisinternal ORDER BY c.relname,t.tgname").fetchall();(out/(name+'.json')).write_text(json.dumps({'anchors_count_xmin_summary':anchors,'trigger_definitions':catalog,'elapsed_s':time.monotonic()-t},indent=2,default=str));return anchors
prior=ctl.execute('SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=%s)AND setrole=0',(DB,)).fetchone();prior={}if not prior else dict(x.split('=',1)for x in prior[0]);(out/'logging-before.json').write_text(json.dumps(prior));before=snapshot('source-before');control=out/'control.txt';control.write_text('warmup');cmd=[sys.executable,str(J/'roundtrip-profile/trace_proxy.py'),'--port','18532','--delay-ms','0','--control',str(control),'--out',str(out/'trace')];plog=(out/'proxy.stdout').open('w');perr=(out/'proxy.stderr').open('w');proxy=subprocess.Popen(cmd,stdout=plog,stderr=perr,start_new_session=True);(out/'proxy-command.json').write_text(json.dumps(cmd));rows=[];started=False

def service(action):
 c=[sys.executable,str(J/'service.py'),action,'--variant','baseline','--database',DB,'--db-host','127.0.0.1','--db-port','18532'];r=subprocess.run(c,capture_output=True,text=True);(out/(action+'-service.stdout')).write_text(r.stdout);(out/(action+'-service.stderr')).write_text(r.stderr);assert r.returncode==0,r.stderr
try:
 for key,value in [('log_min_duration_statement','0'),('log_statement','none'),('log_duration','off')]:ctl.execute(psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(key),psycopg.sql.Literal(value)))
 for _ in range(100):
  if proxy.poll()is not None:raise RuntimeError('Proxy failed')
  if(out/'proxy.stdout').stat().st_size:break
  time.sleep(.05)
 service('start');started=True;token=json.loads((J/'baseline/app/svc_token.json').read_text())['svc'];setup_offset=log.stat().st_size
 with httpx.Client(base_url='http://127.0.0.1:18130',timeout=300)as c:
  for query in ['is1','is3','ic1','ic13','is2','ic2']:
   x=inputs[query];d=out/query;d.mkdir();warm_offset=log.stat().st_size
   for i in range(13):
    tag='warmup-'+query if i<10 else'request-'+query+'-'+str(i-10);control.write_text(tag);offset=log.stat().st_size;t=time.monotonic_ns();wall=time.time_ns();response=c.post('/walker/'+x['walker'],json=x['body'],headers={'Authorization':'Bearer '+token});elapsed=(time.monotonic_ns()-t)/1e6;response.raise_for_status();payload=response.json();data=payload.get('data');result=(data['reports'][0]if'reports'in data else data)if isinstance(data,dict)else payload;actual=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest();row={'query':query,'idx':x['idx'],'iteration':i,'warmup':i<10,'request_tag':tag,'start_wall_ns':wall,'start_mono_ns':t,'end_mono_ns':time.monotonic_ns(),'client_ms':elapsed,'server_ms':float(response.headers['x-server-total-ms'])+float(response.headers.get('x-server-commit-ms',0)),'headers':dict(response.headers),'result':result,'canonical_sha256':actual,'expected_sha256':x['expected_canonical_sha256'],'parity':actual==x['expected_canonical_sha256']};assert row['parity'],(query,result,actual)
    time.sleep(.05)
    with log.open('rb')as f:f.seek(offset);raw=f.read()
    if i>=10:gzip.open(d/f'profile-{i-10}.log.gz','wb').write(raw)
    with(d/'rows.jsonl').open('a')as f:f.write(json.dumps(row)+'\n')
    rows.append(row);control.write_text('idle')
    if i==0:print(json.dumps({'query':query,'first_touch_ms':row['server_ms'],'parity':True}),flush=True)
   with log.open('rb')as f:f.seek(warm_offset);raw=f.read()
   gzip.open(d/'setup-and-profile.log.gz','wb').write(raw);(d/'oracle.json').write_text(json.dumps(result,indent=2));(d/'input.json').write_text(json.dumps(x,indent=2));print(json.dumps({'query':query,'complete':True,'profile_n':3,'oracle':str(d/'oracle.json')}),flush=True)
finally:
 try:service('stop')
 finally:
  for key in ['log_min_duration_statement','log_statement','log_duration']:
   sql=psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(key),psycopg.sql.Literal(prior[key]))if key in prior else psycopg.sql.SQL('ALTER DATABASE {} RESET {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(key));ctl.execute(sql)
  ctl.close()
  if proxy.poll()is None:os.killpg(proxy.pid,signal.SIGTERM)
  try:proxy.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(proxy.pid,signal.SIGKILL);proxy.wait()
  plog.close();perr.close();after=snapshot('source-after');dc.close();(out/'cleanup.json').write_text(json.dumps({'logging_restored':True,'service_stopped':True,'proxy_returncode':proxy.returncode,'anchor_count_xmin_unchanged':before==after},indent=2));(out/'rows.json').write_text(json.dumps(rows,indent=2));assert before==after
