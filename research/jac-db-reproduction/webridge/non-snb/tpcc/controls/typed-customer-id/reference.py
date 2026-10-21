#!/usr/bin/env python3
"""Additional typed-JDBC prefix6 gate, conditionally the original900 gate."""
import pathlib,json,sys,importlib.util,subprocess,hashlib,datetime,fcntl
H=pathlib.Path(__file__).resolve().parents[2];D=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
s=importlib.util.spec_from_file_location('watchdog',H.parents[1]/'benchmark-comparison/owned_watchdog.py');w=importlib.util.module_from_spec(s);s.loader.exec_module(w)
case=H/'cases/conventional-full-payment_name_GC-f4f4c31ba90c-typed-getInt-control';m=json.loads((case/'metadata.json').read_text());out=D/('reference-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));out.mkdir();plan=json.loads((H.parent/'tpcc-plan-900.json').read_text());routes=json.loads((H/'mixed-conventional-full-20261021T013535Z/routes.json').read_text());defs=out/'definitions';defs.mkdir();(defs/m['api']).symlink_to(case/'generated/sql'/m['api'],target_is_directory=True);original=json.loads((H/'mixed-first-fallback-prefix6/java-command.json').read_text());snap=pathlib.Path(m['snapshot']);overlay=H/'mixed-first-fallback-prefix6/classes'
def run(name,n,compiled):
 d=out/name;d.mkdir();(d/'plan.json').write_text(json.dumps(plan[:n],indent=2));(d/'routes.json').write_text(json.dumps(routes[:n],indent=2));(d/'cases.json').write_text(json.dumps({'payment_name_GC':str(case)}if compiled else{},indent=2))
 subprocess.run([sys.executable,str(H/'reset_cell.py'),'--case',str(case),'--phase','sp'if compiled else'baseline','--receipt',str(d/'reset.json')],check=True)
 a=list(original);i=a.index('-cp');a[i+1]=str(overlay)+':'+m['classpath']
 for j,x in enumerate(a):
  if x.startswith('-Dexecution.dir='):a[j]='-Dexecution.dir='+str(d/'run')
  elif x.startswith('-Dintegration.dir='):a[j]='-Dintegration.dir='+str(case)
  elif x.startswith('-Dintegration.api='):a[j]='-Dintegration.api='+m['api']
  elif x.startswith('-Dmixed.definitions='):a[j]='-Dmixed.definitions='+str(defs)
  elif x.startswith('-Dexperiment.mysql.url='):a[j]=x.replace('{endpoint}','127.0.0.1:55337')
 i=a.index('TpccMixed');a[i+1:]=[str(d/'plan.json'),str(d/'cases.json'),str(d/'routes.json')]
 with (H.parents[1]/'integration/.mysql-sp-profile.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);r=w.run(a,d/'run',timeout=180,request_limit=15,db=m['database']);assert not r['timed_out'],r
 # Explicitly prove no owned database session remains before the next request batch.
 cid=json.loads((d/'run/connection-id.json').read_text())['connection_id'];p=subprocess.run(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-e','SELECT ID FROM information_schema.PROCESSLIST WHERE ID='+str(cid)],capture_output=True,text=True);assert p.returncode==0 and not p.stdout.strip();(d/'run/server-absence.json').write_text(json.dumps({'connection_id':cid,'absent_before_next_batch':True}))
 rows=[json.loads(l)for l in(d/'run/requests.jsonl').read_text().splitlines()];assert len(rows)==n
 return d,rows

def states(d,stage):return {k:(v['rows'],v['sha256'])for k,v in json.loads((d/'run'/stage/'manifest.json').read_text()).items()}
with lease('TPC-C additional idiomatic typed-getInt prefix/full900 control',out/'lease.json'):
 baseline,a=run('prefix6-direct',6,False);sp,b=run('prefix6-webridge',6,True);passed=[x['result']for x in a]==[x['result']for x in b]and all(states(baseline,t)==states(sp,t)for t in['before','after']);receipt={'status':'PASS'if passed else'REJECTED','requests':6,'all_outputs_equal':[x['result']for x in a]==[x['result']for x in b],'eight_full_relations_equal':all(states(baseline,t)==states(sp,t)for t in['before','after']),'calls':sum(x['call_procedure']for x in b),'actual_requests':str(sp/'run/requests.jsonl'),'typed_source':str(D/'TpccSql.java'),'typed_source_sha256':hashlib.sha256((D/'TpccSql.java').read_bytes()).hexdigest(),'source_diff':str(D/'source.diff'),'primary_replacement':False};(out/'prefix6-correctness.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
 if passed:
  full,r=run('original900-webridge',900,True);reference=H/'gate-jac-seed900-tx-complete-v1/results';expected=[json.loads(l)for l in(reference/'requests.jsonl').read_text().splitlines()];same=[x['result']for x in r]==[x['result']for x in expected];state_equal=all(states(full,t)=={k:(v['rows'],v['sha256'])for k,v in json.loads((reference/t/'manifest.json').read_text()).items()}for t in['before','after']);(out/'original900-correctness.json').write_text(json.dumps({'status':'PASS'if same and state_equal else'REJECTED','requests':900,'warmup_count':100,'measured_count':800,'outputs_equal':same,'eight_full_relations_equal':state_equal,'requests_with_call':sum(x['call_procedure']>0 for x in r),'active_requests':sum(x['call_procedure']>0 and x['sp_enabled_end']for x in r),'actual_requests':str(full/'run/requests.jsonl'),'reference':str(reference),'primary_replacement':False,'scope':'Additional idiomatic-JDBC typedCustomerID; onlynameGCcompiled; IDPayments/NewOrders ordinarysource; actualnameBCguardfallback retained'},indent=2));print('full900',same,state_equal,flush=True)
print(out)
