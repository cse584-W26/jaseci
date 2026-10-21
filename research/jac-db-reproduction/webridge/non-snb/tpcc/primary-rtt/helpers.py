#!/usr/bin/env python3
"""Fresh-state full/pruned/conventional direct and real-WeBridge latency cells."""
import argparse,datetime,decimal,fcntl,importlib.util,json,pathlib,signal,statistics,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent.parent;B=H.parents[1]
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
