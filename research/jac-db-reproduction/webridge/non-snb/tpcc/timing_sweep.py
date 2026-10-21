#!/usr/bin/env python3
"""Fresh-state full/pruned/conventional direct and real-WeBridge latency cells."""
import argparse,datetime,decimal,fcntl,importlib.util,json,pathlib,signal,statistics,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
t=module('timer',H/'timing_command.py');w=module('watchdog',B/'benchmark-comparison/owned_watchdog.py');lease=module('lease',H.parent/'measurement_lease.py').lease
w.ctl.LIMITS={'rss_bytes':12*1024**3,'output_bytes':8*1024**3}
def sql(q):return subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-N','-B','-uroot','-e',q],text=True)
def settings():return {'instruments':sql('SELECT NAME,ENABLED,TIMED FROM performance_schema.setup_instruments ORDER BY NAME'),'consumers':sql('SELECT NAME,ENABLED FROM performance_schema.setup_consumers ORDER BY NAME'),'logging':sql('SELECT @@global.general_log,@@global.log_output')}
def restore(before,out):
 statements=[]
 for line in before['instruments'].splitlines():
  name,enabled,timed=line.split('\t')
  if name.startswith('statement/sp/'):statements.append("UPDATE performance_schema.setup_instruments SET ENABLED='"+enabled+"',TIMED='"+timed+"' WHERE NAME='"+name+"';")
 sql('\n'.join(statements));after=settings();assert before==after,'Exact instrumentation restoration failed';(out/'instrumentation-restored.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exact_full_snapshot_equal':True,'state':after},indent=2))
def absence(out,db):
 receipt=out/'connection-id.json'
 if not receipt.exists():return
 cid=json.loads(receipt.read_text());cid=cid['connection_id']if isinstance(cid,dict)else cid;observed=[];deadline=time.monotonic()+60
 while True:
  result=sql('SELECT ID,DB,COMMAND,TIME,STATE,INFO FROM information_schema.PROCESSLIST WHERE ID='+str(int(cid)));observed.append({'wall_ns':time.time_ns(),'process':result})
  if not result.strip():break
  assert time.monotonic()<deadline,'Owned JDBC connection remained after60s';time.sleep(.25)
 (out/'strict-server-absence.json').write_text(json.dumps({'connection_id':cid,'database':db,'absent_before_next_cell':True,'observations':observed},indent=2))
def p95(values):
 a=sorted(values);r=(len(a)-1)*.95;i=int(r);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(r-i)
def state_hashes(path):
 m=json.loads((path/'manifest.json').read_text());return {k:(v['rows'],v['sha256'])for k,v in m.items()}
def compare(baseline,sp,out):
 a=[json.loads(line)for line in(baseline/'rows.jsonl').read_text().splitlines()];b=[json.loads(line)for line in(sp/'rows.jsonl').read_text().splitlines()];assert len(a)==len(b)==40
 assert [r['result']for r in a]==[r['result']for r in b],'Evolving request outputs differ'
 for stage in ['before','after']:
  assert state_hashes(baseline/stage)==state_hashes(sp/stage),(stage,'Targeted mutable state differs')
  assert json.loads((baseline/stage/'global-counts.json').read_text())==json.loads((sp/stage/'global-counts.json').read_text()),(stage,'Global entity counts differ')
 (out/'correctness.json').write_text(json.dumps({'status':'PASS','requests_compared':40,'scope':'All evolving outputs, exact targeted mutable-state SHA values, all global entity counts; full eight-table gates are separate','baseline':str(baseline),'webridge':str(sp)},indent=2))
def summarize(rows,base,out):
 measured=[r for r in rows if not r['warmup']];assert len(measured)==30
 v=[r['ms']for r in measured];calls=[r['call_procedure']for r in measured];active=sum(bool(r['sp_enabled_end'])and r['call_procedure']>0 for r in measured)
 return dict(base,status='measured',warmup_count=10,n=30,median_ms=statistics.median(v),p95_ms=p95(v),thread_cpu_median_ms=statistics.median(r['thread_cpu_ms']for r in measured),questions=sorted(set(r['questions']for r in measured)),call_procedure=sorted(set(calls)),compiled_active_requests=active,compiled_active_fraction=active/30,call_requests=sum(c>0 for c in calls),rows_path=str(out/'rows.jsonl'),state_scope=str(out/'after/scope.json'),method='Fresh initial state per phase; same operation40times;10mutatingwarmups+30measured; legitimate original-runtime fallback retained')
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,default=H/'timing');p.add_argument('--delays',nargs='+',type=int,default=[0,2,10]);p.add_argument('--port',type=int,default=18537);a=p.parse_args();a.out.mkdir(exist_ok=False);cases=json.loads((H/'case-status.json').read_text());assert len(cases)==21 and all(c['baseline_ready']and c['status']!='running'for c in cases),'Finish all genuine pipelines and direct correctness before quiet timing';summary=[]
with lease('TPC-C Java exclusive quiet latency sweep',a.out/'lease.json'):
 before=settings();assert before['logging'].split('\t')[0]=='0';(a.out/'instrumentation-before.json').write_text(json.dumps(before,indent=2));sql("UPDATE performance_schema.setup_instruments SET ENABLED='NO',TIMED='NO' WHERE NAME LIKE 'statement/sp/%'");(a.out/'instrumentation-disabled.json').write_text(json.dumps(settings(),indent=2))
 try:
  for delay in a.delays:
   d=a.out/f'delay-{delay}ms';d.mkdir();log=(d/'proxy.log').open('w');cmd=[sys.executable,str(B/'latency-comparison/proxy.py'),'--port',str(a.port),'--delay-ms',str(delay),'--target-port','55337','--receipt',str(d/'proxy-cleanup.json')];proxy=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    for _ in range(100):
     if '"ready": true'in(d/'proxy.log').read_text():break
     assert proxy.poll()is None;time.sleep(.05)
    else:raise RuntimeError('Proxy not ready')
    cp=str(B/'latency-comparison/classes')+':'+t.m.CP;t.m.command([str(t.m.SERVER/'bin/java'),'-cp',cp,'Roundtrip',str(a.port),str(d/'roundtrip.json')],d/'calibration',60)
    for c in cases:
     name=c['program']+'-'+c['variant'];cell=d/name/c['workload'];cell.mkdir(parents=True);baseline=None
     for phase in ['baseline','sp']:
      base={'family':'tpcc','workload':c['workload'],'system':c['system']+(' + WeBridge'if phase=='sp'else''),'program':c['program'],'variant':c['variant'],'phase':phase,'delay_ms':delay,'case':c['case']}
      if phase=='sp'and not c['sp_ready']:
       summary.append(dict(base,status='failed-stage',failure=c['failure'],pipeline=c['pipeline'],n=0,median_ms=None));(a.out/'summary.json').write_text(json.dumps(summary,indent=2));continue
      resultrow=None;timeout_paths=[]
      for attempt in range(3):
       out=cell/phase/('attempt-'+str(attempt));out.mkdir(parents=True);resetcmd=[sys.executable,str(H/'reset_cell.py'),'--case',c['case'],'--phase',phase,'--receipt',str(out/'reset.json')];subprocess.run(resetcmd,check=True);argv=t.command(c['case'],out,phase,10,30,'127.0.0.1:'+str(a.port));meta=json.loads((pathlib.Path(c['case'])/'metadata.json').read_text())
       try:
        with (B/'integration/.mysql-sp-profile.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX);guard=w.run(argv,out,timeout=900,request_limit=15,db=meta['database'])
        absence(out,meta['database']);assert not guard['timed_out'],'Request exceeded15s; sequence incomplete';rows=[json.loads(line)for line in(out/'rows.jsonl').read_text().splitlines()];resultrow=summarize(rows,base,out)
        if phase=='baseline':baseline=out
        else:compare(baseline,out,cell)
        break
       except BaseException as error:
        if isinstance(error,KeyboardInterrupt):raise
        absence(out,meta['database']);failure={'type':type(error).__name__,'error':str(error),'attempt':attempt,'raw_path':str(out)};(out/'failure.json').write_text(json.dumps(failure,indent=2));resultrow=dict(base,status='failed-runtime-or-correctness',n=0,median_ms=None,attempts=attempt+1,failure=failure)
        # Repeated fresh attempts are required only for actual bounded timeouts.
        guard_path=out/'owned-watchdog-summary.json'
        if not guard_path.exists()or not json.loads(guard_path.read_text()).get('timed_out'):break
        timeout_paths.append(str(guard_path));resultrow.update(status='timeout >15s; incomplete evolving sequence',timeout_paths=list(timeout_paths),warmup_count=10,measured_count_requested=30)
      summary.append(resultrow);(a.out/'summary.json').write_text(json.dumps(summary,indent=2));print(c['workload'],name,delay,phase,resultrow['status'],flush=True)
   finally:
    if proxy.poll()is None:proxy.send_signal(signal.SIGTERM)
    try:proxy.wait(timeout=5)
    except subprocess.TimeoutExpired:proxy.kill();proxy.wait()
    log.close();(d/'proxy-process.json').write_text(json.dumps({'pid':proxy.pid,'returncode':proxy.returncode,'stopped':proxy.poll()is not None},indent=2))
 finally:restore(before,a.out)
