#!/usr/bin/env python3
"""Fresh-state conventional gates and genuine original WeBridge stages."""
from contextlib import nullcontext
import argparse,datetime,hashlib,importlib.util,json,os,pathlib,signal,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
lease=load('lease',H.parent/'measurement_lease.py').lease
m=load('original',B/'integration/control.py')
def file_sha(path):
 digest=hashlib.sha256()
 with path.open('rb')as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
 return digest.hexdigest()
def command(cmd,out):
 out.mkdir(parents=True,exist_ok=False);started=time.time();receipt={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'timeout_seconds':1800,'status':'running'}
 (out/'command.json').write_text(json.dumps(cmd,indent=2));(out/'execution.json').write_text(json.dumps(receipt,indent=2));stdout=b'';stderr=b'';child=None
 try:
  child=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  try:stdout,stderr=child.communicate(timeout=1800)
  except subprocess.TimeoutExpired:
   receipt.update(status='timeout',owned_process_group_killed=True,server_cleanup_review_required=True);os.killpg(child.pid,signal.SIGKILL);stdout,stderr=child.communicate();raise
  receipt.update(status='completed',returncode=child.returncode)
  return subprocess.CompletedProcess(cmd,child.returncode,stdout,stderr)
 finally:
  (out/'stdout.log').write_bytes(stdout);(out/'stderr.log').write_bytes(stderr);receipt.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.time()-started,returncode=child.returncode if child else None);(out/'execution.json').write_text(json.dumps(receipt,indent=2))
def reset(out,db,graph=False):
 with nullcontext():
  cmd=[sys.executable,str(H/'graph_fixture.py'),'reset','--receipt',str(out/'reset.json')]if graph else[sys.executable,str(H/'relational_fixture.py'),'load','--database',db];r=command(cmd,out/'run');assert r.returncode==0,(out,r.stderr[-2000:])
def state(case,out,db):
 meta=json.loads((case/'metadata.json').read_text());cmd=[str(m.SERVER/'bin/java'),'-Dexperiment.mysql.url=jdbc:mysql://127.0.0.1:55337/'+db+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useLocalSessionState=true','-cp',meta['classpath'],'TpccGraphState'if meta['program']=='graph'else'TpccState',str(out/'state')]
 with nullcontext():r=command(cmd,out/'run');assert r.returncode==0,r.stderr
 if meta['program']=='graph':
  raw=subprocess.run(['docker','exec','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot','-N','-B',db,'-e',"SELECT id,arch_type,props,row_version,seq FROM anchors WHERE row_version='java-dirty' ORDER BY id"],capture_output=True);(out/'state/raw-mutated-anchors.tsv').write_bytes(raw.stdout);(out/'state/raw-mutated-stderr.log').write_bytes(raw.stderr);assert raw.returncode==0
 return json.loads((out/'state/manifest.json').read_text())
p=argparse.ArgumentParser();p.add_argument('--workloads',nargs='+',default=['payment_name_GC','new_order_rollback','payment_id_GC','new_order_5','new_order_15','payment_name_BC','payment_id_BC']);p.add_argument('--program',choices=['conventional','graph'],default='conventional');p.add_argument('--variant',choices=['full','pruned'],default='full');p.add_argument('--attempt',default='original');p.add_argument('--compat-cp',default='');p.add_argument('--database',default='jac_tpcc_conventional');a=p.parse_args();a.database='jac_tpcc_graph'if a.program=='graph'else a.database;run=H/('pipeline-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));run.mkdir();rows=[]
for workload in a.workloads:
 row={'family':'tpcc','workload':workload,'system':a.program+'-'+a.variant+'-webridge','stages':[],'status':'running'};rows.append(row);folder=run/workload;folder.mkdir();base=[sys.executable,str(H/'control.py'),'--lease-held','--compat-cp',a.compat_cp,'--input',str(H/'inputs'/(workload+'.json')),'--database',a.database,'--attempt',a.attempt,'--program',a.program,'--variant',a.variant,'--schema',str(H/('graph-compiler-schema.sql'if a.program=='graph'else'relational-schema.sql'))];case=None;graph=None;baseline=None
 try:
  with lease('TPC-C atomic full compiler lifecycle '+a.program+' '+a.variant+' '+workload,folder/'atomic-stage-lease.json'):
   for action in ['baseline','record','replay','synth','install','optimized']:
    if action in ['baseline','record','install']:reset(folder/(action+'-reset'),a.database,a.program=='graph')
    if action=='install':
     meta=json.loads((case/'metadata.json').read_text());sqlfolder=case/'generated/sql'/meta['api'];files=[sqlfolder/'graph-SP-function.sql',*sorted(sqlfolder.glob('graph-SP-*_sp_*.sql'))];assert len(files)>1 and all(f.exists()for f in files)
     with nullcontext():
      out=folder/'install';out.mkdir();cmd=['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot',a.database];r=subprocess.run(cmd,input=((b"SET SESSION sql_mode=CONCAT(@@session.sql_mode,',NO_UNSIGNED_SUBTRACTION');\n"if meta['manifest'].get('session_configuration',{}).get('no_unsigned_subtraction')else b'')+b'\n'.join(f.read_bytes()for f in files)),capture_output=True);(out/'stdout.log').write_bytes(r.stdout);(out/'stderr.log').write_bytes(r.stderr)
     modes=subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-e',"SELECT ROUTINE_NAME,SQL_MODE FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA='"+a.database+"' ORDER BY ROUTINE_NAME"],text=True);(out/'routine-creation-modes.txt').write_text(modes)
     detail={'stage':action,'returncode':r.returncode,'path':str(out),'sql_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in files}}
    else:
     cmd=base[:2]+[action]+base[2:]+(['--graph',str(graph)]if action=='synth'else[]);r=command(cmd,folder/action);paths=[pathlib.Path(s)for s in r.stdout.decode(errors='replace').splitlines()if s.startswith(str(H/'cases'))];out=paths[-1]if paths else None
     if out:case=out.parent;row['case']=str(case)
     if action=='replay'and out:graph=out/'graph.json'
     detail={'stage':action,'returncode':r.returncode,'path':str(out)if out else None,'command_logs':str(folder/action)}
    row['stages'].append(detail);(run/'summary.json').write_text(json.dumps(rows,indent=2));print(workload,action,r.returncode,flush=True)
    if r.returncode:
     row['status']='failed-stage';row['failed_stage']=action
     if case and action in ['replay','synth']:
      emitted=[f for f in case.rglob('*')if f.is_file()and(f.suffix in ['.sql','.ser']or f.name=='graph.json')]
      row['emitted_artifacts']=[{'path':str(f),'bytes':f.stat().st_size,'sha256':file_sha(f)}for f in emitted]
      row['emitted_artifact_review']='Required before classifying capability: formal stage exit does not prove emitted artifacts unusable'
     break
    if action in ['baseline','record','optimized']:
     snapshot=state(case,folder/(action+'-after'),a.database);hashes={k:(v['rows'],v['sha256'])for k,v in snapshot.items()}
     if action=='baseline':baseline=hashes
     else:assert hashes==baseline,(workload,action,'posttransaction business state mismatch')
     report=json.loads((out/'report.json').read_text());row.setdefault('results',{})[action]=report['result']
     if action!='baseline':assert row['results'][action]==row['results']['baseline']
     if action=='optimized':row['optimized_activation']={'call_procedure':report['session_status_delta'].get('Com_call_procedure',0),'sp_enabled_start':report['region'].get('sp_enabled_at_start'),'sp_enabled_end':report['region'].get('sp_enabled_at_end'),'server_questions':report['server_questions']}
   else:row['status']='success';row['correctness']='Identical outputs and full normalized mutable-table states from independent initial resets'
 except BaseException as e:
  row['status']='failed-stage';row['error']=repr(e)
  if isinstance(e,subprocess.TimeoutExpired):
   row['server_cleanup_review_required']=True;(run/'summary.json').write_text(json.dumps(rows,indent=2));raise
 (run/'summary.json').write_text(json.dumps(rows,indent=2))
 subprocess.run([sys.executable,str(H/'case_status.py')],stdout=subprocess.DEVNULL,check=True)
print(run)
