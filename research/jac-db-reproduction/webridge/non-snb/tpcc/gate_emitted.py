#!/usr/bin/env python3
"""Install and state-check genuine emitted artifacts in a separate compatibility case."""
import argparse,fcntl,hashlib,importlib.util,json,pathlib,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--case',type=pathlib.Path,required=True);p.add_argument('--origin',type=pathlib.Path,required=True);p.add_argument('--baseline-state',type=pathlib.Path,required=True);a=p.parse_args();case=a.case.resolve();origin=a.origin.resolve();meta=json.loads((origin/'metadata.json').read_text());overlays=[H/'compat/numeric-alias/classes',H/'compat/update-expression/classes'];meta['classpath']=':'.join(map(str,overlays))+':'+meta['classpath'];meta['manifest']['compatibility_classes']={str(f.relative_to(H)):sha(f)for d in overlays for f in d.rglob('*.class')};meta['provenance']={'original_case':str(origin),'original_metadata_sha256':sha(origin/'metadata.json'),'trace_reuse':'Unchanged native concolic graph; only SQL frontend arithmetic placeholders and NUMERIC alias compatibility changed','label':'WeBridge + frontend compatibility fixes'};(case/'metadata.json').write_text(json.dumps(meta,indent=2))
lease=module('lease',H.parent/'measurement_lease.py').lease;watchdog=module('watchdog',B/'benchmark-comparison/owned_watchdog.py');watchdog.ctl.LIMITS={'rss_bytes':12*1024**3,'output_bytes':8*1024**3};out=case/'installed-gate';out.mkdir()
with lease('TPC-C emitted write procedure install and full state gate',out/'lease.json'):
 r=subprocess.run([sys.executable,str(H/'reset_cell.py'),'--case',str(case),'--phase','sp','--receipt',str(out/'reset.json')],capture_output=True);(out/'reset.stdout').write_bytes(r.stdout);(out/'reset.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr
 old=json.loads(next(origin.glob('baseline-*/command.json')).read_text())['argv'];run=out/'optimized';cmd=[]
 for value in old:
  if value.startswith('-Dintegration.dir='):value='-Dintegration.dir='+str(case)
  elif value.startswith('-Dexecution.dir='):value='-Dexecution.dir='+str(run)
  elif value==meta.get('classpath'):pass
  cmd.append(value)
 cmd[cmd.index('-cp')+1]=meta['classpath'];cmd[-1]='optimized'
 with (B/'integration/.mysql-sp-profile.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  try:result=watchdog.run(cmd,run,timeout=120,request_limit=15,db=meta['database'])
  finally:
   receipt=run/'connection-id.json'
   if receipt.exists():
    cid=json.loads(receipt.read_text());cid=cid['connection_id']if isinstance(cid,dict)else cid;observations=[];deadline=time.monotonic()+60
    while True:
     active=subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-e','SELECT ID,DB,COMMAND,TIME,STATE,INFO FROM information_schema.PROCESSLIST WHERE ID='+str(int(cid))],text=True);observations.append({'wall_ns':time.time_ns(),'process':active})
     if not active.strip():break
     assert time.monotonic()<deadline;time.sleep(.25)
    (run/'strict-server-absence.json').write_text(json.dumps({'connection_id':cid,'absent_before_next_request':True,'observations':observations},indent=2))
 assert not result['timed_out'],result
 state=out/'after';java=cmd[0];statecmd=[java,'-Xmx2g','-Dexperiment.mysql.url=jdbc:mysql://127.0.0.1:55337/'+meta['database']+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8','-cp',meta['classpath'],'TpccGraphState'if meta['program']=='graph'else'TpccState',str(state)];r=subprocess.run(statecmd,capture_output=True,timeout=300);(out/'state.stdout').write_bytes(r.stdout);(out/'state.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr
 before=json.loads(a.baseline_state.read_text());after=json.loads((state/'manifest.json').read_text());assert {k:(v['rows'],v['sha256'])for k,v in before.items()}=={k:(v['rows'],v['sha256'])for k,v in after.items()},'Full eight-table state differs'
 baseline=json.loads(next(origin.glob('baseline-*/report.json')).read_text());report=json.loads((run/'report.json').read_text());assert baseline['result']==report['result']
 (out/'correctness.json').write_text(json.dumps({'status':'PASS','all_eight_mutable_tables_exact':True,'output_exact':True,'report':report,'origin':str(origin),'baseline_state':str(a.baseline_state)},indent=2));print(case)
