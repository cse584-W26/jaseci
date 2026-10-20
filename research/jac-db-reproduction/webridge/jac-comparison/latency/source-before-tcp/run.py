"""Matched-fixture Jac timing and separate PID-classified protocol census."""
import argparse,pathlib,json,subprocess,os,time,sys,re,gzip,hashlib,shutil
import httpx,psycopg
R=pathlib.Path(__file__).resolve().parent;REPRO=R.parents[1]
p=argparse.ArgumentParser();p.add_argument('--variant',choices=['baseline','final'],required=True);p.add_argument('--database',default='jac_webridge_matched_20261020');p.add_argument('--socket',default='/tmp/jacpg-d6275e76eb');p.add_argument('--port',type=int,default=18130);p.add_argument('--mode',choices=['timing','census'],required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--warm',type=int,default=10);p.add_argument('--measure',type=int,default=30);a=p.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False);x=json.loads((REPRO/'webridge/alignment/small-diagnostic/input.json').read_text());expected={'forums':[{'forumId':r[0],'title':r[1],'postCount':r[2]} for r in x['expected']]};log=REPRO/'dbcache/pg/main/server.log';db=psycopg.connect(host=a.socket,user='jac',dbname='postgres',autocommit=True);before=db.execute('SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=%s) AND setrole=0',(a.database,)).fetchone();prior={}if not before else dict(s.split('=',1)for s in before[0]);(o/'database-settings-before.json').write_text(json.dumps(prior,indent=2));settings=['log_min_duration_statement','log_statement','log_duration'];rows=[]
def service(action):
 cmd=[sys.executable,str(R/'service.py'),action,'--variant',a.variant,'--database',a.database,'--socket',a.socket,'--port',str(a.port)];q=subprocess.run(cmd,capture_output=True,text=True);(o/(action+'-service.stdout')).write_text(q.stdout);(o/(action+'-service.stderr')).write_text(q.stderr);assert q.returncode==0,q.stderr

def cpu(pid):
 v=(pathlib.Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split();return(int(v[11])+int(v[12]))*1000/os.sysconf('SC_CLK_TCK')
try:
 for k,v in [('log_min_duration_statement','0'if a.mode=='census'else'-1'),('log_statement','none'),('log_duration','off')]:db.execute(psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(a.database),psycopg.sql.Identifier(k),psycopg.sql.Literal(v)))
 service('start');shutil.copy2(R/a.variant/'launch.json',o/'launch.json');shutil.copy2(R/a.variant/'source.json',o/'source.json');pid=int((R/a.variant/'service.pid').read_text());token=json.loads((R/a.variant/'app/svc_token.json').read_text())['svc'];count=3 if a.mode=='census'else a.warm+a.measure
 with httpx.Client(base_url='http://127.0.0.1:'+str(a.port),timeout=300)as c,(o/'rows.jsonl').open('w')as sink:
  for i in range(count):
   if a.mode=='timing' and i==a.warm: measured_cpu_start=cpu(pid)
   offset=log.stat().st_size;appcpu=cpu(pid);t=time.perf_counter();response=c.post('/walker/ic5_new_forums',json={'person_jid':x['person_jid'],'min_date':x['min_date']},headers={'Authorization':'Bearer '+token});client=(time.perf_counter()-t)*1000;cpud=cpu(pid)-appcpu;
   if response.status_code!=200:(o/('http-error-'+str(i)+'.json')).write_text(json.dumps({'status':response.status_code,'headers':dict(response.headers),'body':response.text}));
   response.raise_for_status();payload=response.json();data=payload.get('data');result=(data['reports'][0]if'reports'in data else data)if isinstance(data,dict)else payload;parity=result==expected;headers=dict(response.headers);srv=float(headers['x-server-total-ms']);commit=float(headers.get('x-server-commit-ms',0));row={'iteration':i,'warmup':i<a.warm if a.mode=='timing'else False,'mode':a.mode,'variant':a.variant,'client_ms':client,'server_total_header_ms':srv,'commit_header_ms':commit,'server_ms':srv+commit,'app_process_cpu_ms':cpud,'headers':headers,'result':result,'parity':parity,'status':response.status_code}
   if a.mode=='census':
    time.sleep(.1)
    with log.open('rb')as f:f.seek(offset);raw=f.read()
    gzip.open(o/('request'+str(i)+'.log.gz'),'wb').write(raw);groups={};phases={}
    for line in raw.decode(errors='replace').splitlines():
     m=re.search(r'\[(\d+)\].*duration: ([\d.]+) ms\s+(execute [^:]*|statement):',line)
     if m:groups.setdefault(m[1],[]).append(line)
     phase=re.search(r'\[(\d+)\].*duration: ([\d.]+) ms\s+(parse|bind|execute|statement)',line)
     if phase:entry=phases.setdefault(phase[1],{}).setdefault(phase[3],{'n':0,'ms':0.});entry['n']+=1;entry['ms']+=float(phase[2])
    row.update(execution_counts_by_pid={k:len(v)for k,v in groups.items()},execution_count=sum(map(len,groups.values())),protocol_by_pid=phases,raw_sha256=hashlib.sha256(raw).hexdigest());(o/('request'+str(i)+'-execution-lines.json')).write_text(json.dumps(groups,indent=2))
   rows.append(row);sink.write(json.dumps(row)+'\n');sink.flush();print(json.dumps({k:row[k]for k in ['iteration','variant','client_ms','server_ms','parity']}),flush=True)
   if not parity:raise RuntimeError('Result parity failed')
   if a.mode=='timing' and i==count-1:
    cpu_total=cpu(pid)-measured_cpu_start;(o/'measured-cpu.json').write_text(json.dumps({'process_cpu_ms':cpu_total,'requests':a.measure,'mean_ms_per_request':cpu_total/a.measure,'tick_ms':1000/os.sysconf('SC_CLK_TCK'),'scope':'Whole measured interval including inter-request housekeeping; isolated application process'}))
finally:
 try:
  service('stop')
  if(R/a.variant/'server.log').exists():shutil.copy2(R/a.variant/'server.log',o/'server.log')
 finally:
  for k in settings:
   q=psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(a.database),psycopg.sql.Identifier(k),psycopg.sql.Literal(prior[k]))if k in prior else psycopg.sql.SQL('ALTER DATABASE {} RESET {}').format(psycopg.sql.Identifier(a.database),psycopg.sql.Identifier(k));db.execute(q)
  db.close();(o/'rows.json').write_text(json.dumps(rows,indent=2));(o/'restored.json').write_text(json.dumps({'logging_restored':True,'service_stopped':True,'database':a.database}))
