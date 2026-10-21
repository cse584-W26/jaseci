"""Native historical littleX plans, fresh fixture per cell, independent result/state oracle."""
import argparse,pathlib,json,sys,subprocess,os,time,signal,hashlib,shutil,statistics,gzip,collections,datetime
import psycopg,httpx
R=pathlib.Path(__file__).resolve().parent;W=R.parents[1];L=R.parent/'littlex';REPRO=R.parents[2];sys.path[:0]=[str(R),str(R.parent)]
from measurement_lease import lease
from littlex_oracle import Oracle
p=argparse.ArgumentParser();p.add_argument('--method',choices=['latency','reference'],default='latency');p.add_argument('--output',default='littlex-timing');p.add_argument('--tiers',default='t20,t50,t100,t200');p.add_argument('--variants',default='baseline,final');p.add_argument('--delays',default='0,2,10');p.add_argument('--only',default='');p.add_argument('--limit-requests',type=int);p.add_argument('--instrument',action='store_true');p.add_argument('--profile-measured',type=int,default=3);p.add_argument('--oracle-fixtures',type=pathlib.Path,default=R/'littlex-oracle-fixtures');a=p.parse_args()
O=R/a.output;O.mkdir(exist_ok=True)
with(O/'command.json').open('x')as f:json.dump({'argv':[sys.executable,*sys.argv],'cwd':os.getcwd(),'requested_wall_ns':time.time_ns()},f,indent=2)
DB='jac_non_snb_littlex_work_20261020';PORT=18532;service=L/'native/service.py';recipe=json.loads((L/'recipe.json').read_text());catalog=json.loads((L/'plans/manifest.json').read_text());selected=[x for x in catalog if x['method']==a.method and x['tier']in a.tiers.split(',')and(not a.only or x['workload']+'-'+x['operation']in a.only.split(','))];assert selected
if a.method=='reference':assert a.delays=='0','Historical reference has a single local zero-delay transport condition'
def cpu(pid):
 s=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split();return(int(s[11])+int(s[12]))*1000/os.sysconf('SC_CLK_TCK')
def calibration(host,port):
 samples=[]
 with psycopg.connect(host=host,port=port,user='jac',dbname=DB,autocommit=True)as c:
  for i in range(40):
   t=time.monotonic_ns();assert c.execute('SELECT 1').fetchone()==(1,)
   if i>=10:samples.append((time.monotonic_ns()-t)/1e6)
 return {'warm':10,'n':30,'samples_ms':samples,'median_ms':statistics.median(samples)}
def extract(payload):
 d=payload.get('data',payload);return d['reports'][0]if isinstance(d,dict)and'reports'in d else d
routes={'feed':'load_feed_chain','feed_page':'load_feed_page','like':'like_tweet','follow':'follow_user','create_tweet':'create_tweet'}
def body(x):return{k:x[k]for k in {'feed':[],'feed_page':[],'like':['tweet_id'],'follow':['target_id'],'create_tweet':['seed_id','content']}[x['op']]}
with lease('native littleX '+a.method+' fresh-state sweep',O/'lease.json'):
 source=O/'source';source.mkdir(exist_ok=False)
 for f in [pathlib.Path(__file__),R/'littlex_oracle.py',R/'trace_proxy.py',service,L/'plans/manifest.json']:
  shutil.copy2(f,source/f.name)
 (source/'sha256.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in source.iterdir()},indent=2))
 summary=[]
 for delay in map(int,a.delays.split(',')):
  home=O/('delay-'+str(delay)+'ms');home.mkdir(exist_ok=False);pcmd=[sys.executable,str(W/'latency-comparison/proxy.py'),'--port',str(PORT),'--delay-ms',str(delay),'--unix','/tmp/jacpg-d6275e76eb/.s.PGSQL.5432','--receipt',str(home/'proxy.json')];control=home/'control.txt'
  if a.instrument:control.write_text('idle');pcmd=[sys.executable,str(R/'trace_proxy.py'),'--port',str(PORT),'--delay-ms',str(delay),'--out',str(home/'trace'),'--control',str(control)]
  log=(home/'proxy.stdout').open('w');proxy=subprocess.Popen(pcmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   time.sleep(.5);assert proxy.poll()is None;calibrated=False
   for variant in a.variants.split(','):
    for entry in selected:
     tier=entry['tier'];label=entry['workload']+'-'+entry['operation'];out=home/variant/tier/label;out.mkdir(parents=True,exist_ok=False);assert shutil.disk_usage(R).free>15*1024**3
     template=recipe['tiers'][tier]['historical_snapshot'];fixture=pathlib.Path(recipe['tiers'][tier]['fixture_manifest']).parent;tokens=json.loads((fixture/'tokens/tokens.jaseci.json').read_text());planpath=pathlib.Path(entry['path']);planraw=planpath.read_bytes();assert hashlib.sha256(planraw).hexdigest()==entry['sha256'];plan=json.loads(planraw)
     if a.instrument:plan=plan[:sum(x['warmup']for x in plan)+a.profile_measured]
     if a.limit_requests:plan=plan[:a.limit_requests]
     oracle=Oracle(a.oracle_fixtures/(tier+'.json.gz'));shutil.copy2(planpath,out/'plan.json');(out/'scope.json').write_text(json.dumps(entry|{'instrumented':a.instrument,'selected_requests':len(plan),'original_plan_sha256':entry['sha256'],'source_template':template,'HTTP_routes':routes,'clock_uuid_policy':'Native original HTTP generates UUID and clock values; source oracle verifies exact observed values and canonicalizes only newly generated values across runs'},indent=2))
     with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname='postgres',autocommit=True)as admin:
      for wait in range(50):
       clients=admin.execute('SELECT pid FROM pg_stat_activity WHERE datname=%s',(DB,)).fetchall()
       if not clients:break
       time.sleep(.2)
      assert not clients,clients
      admin.execute(psycopg.sql.SQL('DROP DATABASE IF EXISTS {}').format(psycopg.sql.Identifier(DB)));admin.execute(psycopg.sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(template)))
      prior=admin.execute('SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=%s)AND setrole=0',(DB,)).fetchone();prior={}if not prior else dict(x.split('=',1)for x in prior[0]);(out/'settings-before.json').write_text(json.dumps(prior))
      for k,v in [('log_min_duration_statement','0'if a.instrument else'-1'),('log_statement','none'),('log_duration','off')]:admin.execute(psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(k),psycopg.sql.Literal(v)))
      if not calibrated:(home/'calibration-before.json').write_text(json.dumps({'direct':calibration('/tmp/jacpg-d6275e76eb',5432),'proxy':calibration('127.0.0.1',PORT)},indent=2));calibrated=True
      started=False;rows=[];cpu_start=None
      try:
       subprocess.run([sys.executable,str(service),'start','--variant',variant,'--database',DB,'--db-host','127.0.0.1','--db-port',str(PORT)],check=True);started=True
       for name in ['launch.json','source.json']:shutil.copy2(L/'native'/variant/name,out/name)
       launch=json.loads((out/'launch.json').read_text());pid=launch['pid'];runtime=pathlib.Path(launch['source']);reference='ad469c988'if variant=='baseline'else'32c5d1dbb';actualtree=subprocess.check_output(['git','-C',str(runtime),'rev-parse','HEAD:jac'],text=True).strip();expectedtree=subprocess.check_output(['git','-C',str(runtime),'rev-parse',reference+':jac'],text=True).strip();assert actualtree==expectedtree;(out/'runtime-subtree.json').write_text(json.dumps({'reference':reference,'actual_jac_subtree':actualtree,'reference_jac_subtree':expectedtree,'equal':True},indent=2))
       with httpx.Client(base_url='http://127.0.0.1:18134',timeout=300)as client,gzip.open(out/'rows.jsonl.gz','wt',compresslevel=6)as stream:
        for sequence,item in enumerate(plan):
         x=item['input'];warm=item['warmup']
         if not warm and cpu_start is None:cpu_start=cpu(pid)
         request_tag=('warmup-'if warm else'request-')+variant+'-'+tier+'-'+label+'-'+str(sequence)
         if a.instrument:control.write_text(request_tag);pglog=REPRO/'dbcache/pg/main/server.log';offset=pglog.stat().st_size
         start=time.monotonic_ns();wall=time.time_ns();response=client.post('/walker/'+routes[x['op']],json=body(x),headers={'Authorization':'Bearer '+tokens[x['username']]});elapsed=(time.monotonic_ns()-start)/1e6;response.raise_for_status();payload=response.json();result=extract(payload);proof=oracle.apply(x,result)
         if x['op']=='create_tweet':
          stamp=datetime.datetime.fromisoformat(result['tweet']['created_at'].replace('Z','+00:00')).timestamp();assert wall/1e9-1<=stamp<=time.time()+1
         headers=dict(response.headers);total=float(headers['x-server-total-ms']);commit=float(headers['x-server-commit-ms']);row={'request_tag':request_tag,'sequence':sequence,'iteration':item['iteration'],'warmup':warm,'operation':x['op'],'username':x['username'],'HTTP_route':routes[x['op']],'request_body':body(x),'start_wall_ns':wall,'end_wall_ns':time.time_ns(),'client_ms':elapsed,'server_ms':total+commit,'status':response.status_code,'headers':headers,'response_text':response.text,'response_sha256':hashlib.sha256(response.content).hexdigest(),'oracle':proof};stream.write(json.dumps(row,separators=(',',':'))+'\n');stream.flush();rows.append({k:v for k,v in row.items()if k not in ('response_text','request_body','headers')})
         if a.instrument:
          time.sleep(.05)
          if not warm:
           with pglog.open('rb')as f:f.seek(offset);raw=f.read()
           with gzip.open(out/('profile-'+str(item['iteration'])+'.sql.log.gz'),'wb')as f:f.write(raw)
          control.write_text('idle')
       app_cpu=cpu(pid)-cpu_start if cpu_start is not None else None
       with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname=DB)as c:state=oracle.verify_database(c)
       with gzip.open(out/'after-state.json.gz','wt')as f:json.dump(state.pop('canonical'),f,separators=(',',':'))
       (out/'after-state-manifest.json').write_text(json.dumps(state,indent=2))
      finally:
       try:
        if started:subprocess.run([sys.executable,str(service),'stop','--variant',variant],check=True)
       finally:
        for k in ['log_min_duration_statement','log_statement','log_duration']:
         q=psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(k),psycopg.sql.Literal(prior[k]))if k in prior else psycopg.sql.SQL('ALTER DATABASE {} RESET {}').format(psycopg.sql.Identifier(DB),psycopg.sql.Identifier(k));admin.execute(q)
        restored=admin.execute('SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=%s)AND setrole=0',(DB,)).fetchone();restored={}if not restored else dict(x.split('=',1)for x in restored[0]);assert prior==restored;(out/'settings-restored.json').write_text(json.dumps({'exact_prior_restored':True,'before':prior,'after':restored},indent=2))
     measured=[x for x in rows if not x['warmup']];result={'instrumented':a.instrument,'tier':tier,'workload':entry['workload'],'operation':entry['operation'],'method':a.method,'variant':variant,'delay_ms':delay,'warm':len(rows)-len(measured),'n':len(measured),'server_median_ms':statistics.median(x['server_ms']for x in measured)if measured else None,'client_median_ms':statistics.median(x['client_ms']for x in measured)if measured else None,'app_cpu_total_ms':app_cpu,'CPU_tick_ms':1000/os.sysconf('SC_CLK_TCK'),'measured_operation_counts':dict(collections.Counter(x['operation']for x in measured)),'state':state,'path':str(out.relative_to(R)),'all_request_oracles_verified':True};(out/'summary.json').write_text(json.dumps(result,indent=2));summary.append(result);(O/'summary.json').write_text(json.dumps(summary,indent=2));print(tier,label,variant,delay,result['server_median_ms'],flush=True)
   (home/'calibration-after.json').write_text(json.dumps(calibration('127.0.0.1',PORT),indent=2))
  finally:
   if proxy.poll()is None:os.killpg(proxy.pid,signal.SIGTERM)
   try:proxy.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(proxy.pid,signal.SIGKILL);proxy.wait()
   log.close();(home/'cleanup.json').write_text(json.dumps({'proxy_stopped':True,'returncode':proxy.returncode,'command':pcmd},indent=2))
