#!/usr/bin/env python3
"""Run the complete original plan through compiled shapes and measured fallback."""
import argparse,datetime,fcntl,hashlib,importlib.util,json,pathlib,subprocess,sys,time,threading,os,signal
H=pathlib.Path(__file__).resolve().parent

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

p=argparse.ArgumentParser();p.add_argument('--program',choices=['conventional','graph'],required=True);p.add_argument('--variant',choices=['full','pruned'],default='full');a=p.parse_args()
status=json.loads((H/'case-status.json').read_text());selected=[r for r in status if r['program']==a.program and r['variant']==a.variant and r['sp_ready']]
available=[r for r in status if r['program']==a.program and r['variant']==a.variant and r['baseline_ready']];assert available,'No final-source direct gate available'
out=H/('mixed-'+a.program+'-'+a.variant+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));out.mkdir()
cases={r['workload']:r['case']for r in selected};(out/'cases.json').write_text(json.dumps(cases,indent=2));first=pathlib.Path(next(iter(cases.values()))if cases else available[0]['case']);meta=json.loads((first/'metadata.json').read_text())
(out/'manifest.json').write_text(json.dumps({'program':a.program,'variant':a.variant,'cases':{r['workload']:{'path':r['case'],'metadata_sha256':r['metadata_sha256']}for r in selected},'plan_sha256':hashlib.sha256((H.parent/'tpcc-plan-900.json').read_bytes()).hexdigest(),'unavailable_shapes':'Run the unchanged source transaction; retain runtime guard fallbacks','accepted_compiled_cases':len(cases),'source_snapshot_case':str(first)},indent=2))
# Dispatch is derived only from immutable fixture fields; no SQL is added to requests.
customers=[json.loads(line)for line in(H.parents[2]/'benchmark/tpcc/data/customer.jsonl').open()];byid={(c['c_w_id'],c['c_d_id'],c['c_id']):c for c in customers};byname={}
for customer in customers:byname.setdefault((customer['c_w_id'],customer['c_d_id'],customer['c_last']),[]).append(customer)
for group in byname.values():group.sort(key=lambda c:c['c_first'])
routes=[]
for x in json.loads((H.parent/'tpcc-plan-900.json').read_text()):
 if x['kind']=='new_order':
  requested='new_order_rollback'if x.get('invalid')else'new_order_'+str(len(x['lines']));dispatch=requested if requested in cases else'new_order_5'if'new_order_5'in cases else'new_order_15'if'new_order_15'in cases else requested
  method='Exact recorded shape'if requested in cases else'Accepted representative API; original WeBridge guard decides path compatibility'if dispatch in cases else'Unavailable compiled NewOrder path; unchanged source transaction'
 else:
  if x.get('c_id')is not None:c=byid[x.get('w_id',1),x['c_d_id'],x['c_id']];prefix='payment_id_'
  else:group=byname[x.get('w_id',1),x['c_d_id'],x['c_last']];c=group[len(group)//2];prefix='payment_name_'
  requested=prefix+c['c_credit'];dispatch=requested if requested in cases else prefix+'GC'if prefix+'GC'in cases else requested;method='Immutable source Customer credit and name-median dispatch; no request SQL'if dispatch==requested else'Unavailable BC specialization; accepted GC representative API with genuine runtime guards'
 failure=[{'workload':r['workload'],'status':r['status'],'failure':r.get('failure'),'pipeline':r.get('pipeline')}for r in status if r['program']==a.program and r['variant']==a.variant and r['workload']in([requested]if requested.startswith('payment')else['new_order_rollback','new_order_5','new_order_15'])and not r['sp_ready']]
 routes.append({'requested_shape':requested,'dispatch_shape':dispatch,'dispatch_method':method,'unavailable_path_receipts':failure if requested not in cases else[]})
(out/'routes.json').write_text(json.dumps(routes,indent=2))
(out/'routing-provenance.json').write_text(json.dumps({'customer_source_sha256':hashlib.sha256((H.parents[2]/'benchmark/tpcc/data/customer.jsonl').read_bytes()).hexdigest(),'scope':'Static API dispatch only, outside whole-request timer; actual transaction still loads customer and executes original guards'},indent=2))
lease=module('measurement_lease',H.parent/'measurement_lease.py').lease
timer=module('timing_command',H/'timing_command.py');watchdog=module('owned_watchdog',H.parents[1]/'benchmark-comparison/owned_watchdog.py')
with lease('tpcc-whole900-actual-webridge-'+a.program+'-'+a.variant,out/'lease.json'):
 reset=subprocess.run([sys.executable,str(H/'reset_cell.py'),'--case',str(first),'--phase','baseline','--receipt',str(out/'reset.json')],capture_output=True);(out/'reset.stdout').write_bytes(reset.stdout);(out/'reset.stderr').write_bytes(reset.stderr);assert reset.returncode==0
 generated=[]
 for case in cases.values():
  home=pathlib.Path(case);m=json.loads((home/'metadata.json').read_text());folder=home/'generated/sql'/m['api'];files=[folder/'graph-SP-function.sql',*sorted(folder.glob('graph-SP-*_sp_*.sql'))];assert len(files)>1
  r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot',meta['database']],input=((b"SET SESSION sql_mode=CONCAT(@@session.sql_mode,',NO_UNSIGNED_SUBTRACTION');\n"if m['manifest'].get('session_configuration',{}).get('no_unsigned_subtraction')else b'')+b'\n'.join(f.read_bytes()for f in files)),capture_output=True);assert r.returncode==0,r.stderr;generated.extend(str(f)for f in files)
 (out/'generated-sources.json').write_text(json.dumps(generated,indent=2))
 definitions=out/'definitions';definitions.mkdir()
 for workload,case in cases.items():
  home=pathlib.Path(case);m=json.loads((home/'metadata.json').read_text());(definitions/m['api']).symlink_to(home/'generated/sql'/m['api'],target_is_directory=True)
 overlay=out/'harness';overlay.mkdir();(overlay/'TpccMixed.java').write_bytes((H/'compat/mixed-config/TpccMixed.java').read_bytes());classes=overlay/'classes';classes.mkdir()
 build=json.loads((H/'build.json').read_text());compilecmd=[build['command'][0],'-cp',meta['classpath'],'-d',str(classes),str(overlay/'TpccMixed.java')]
 r=subprocess.run(compilecmd,capture_output=True);(out/'overlay-compile.stdout').write_bytes(r.stdout);(out/'overlay-compile.stderr').write_bytes(r.stderr);assert r.returncode==0
 (out/'harness-overlay.json').write_text(json.dumps({'source':str(overlay/'TpccMixed.java'),'source_sha256':hashlib.sha256((overlay/'TpccMixed.java').read_bytes()).hexdigest(),'class_sha256':{str(p.relative_to(classes)):hashlib.sha256(p.read_bytes()).hexdigest()for p in classes.rglob('*.class')},'command':compilecmd,'reason':'One SDK metadata singleton scans combined accepted API definitions; selected-case SPConfig refreshed before each API'},indent=2))
 cmd=timer.command(first,out/'run','sp');cpindex=cmd.index('-cp')+1;cmd[cpindex]=str(classes)+':'+cmd[cpindex];cmd.insert(cmd.index('-cp'),'-Dmixed.definitions='+str(definitions));index=cmd.index('TpccTiming');cmd=cmd[:index]+['TpccMixed',str(H.parent/'tpcc-plan-900.json'),str(out/'cases.json'),str(out/'routes.json')]
 with (H.parents[1]/'integration/.mysql-sp-profile.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  stop=threading.Event()
  def stop_stalled_client():
   while not stop.wait(.1):
    receipts=list((out/'run').glob('owned-watchdog-*.json'))
    expired=[json.loads(p.read_text())for p in receipts if 'active request exceeded' in json.loads(p.read_text()).get('reason','')]
    if not expired:continue
    pidfile=out/'run/pid.json'
    if not pidfile.exists():continue
    identity=json.loads(pidfile.read_text());pid=identity['pid'];group=identity['process_group'];proc=pathlib.Path('/proc')/str(pid)/'cmdline'
    if not proc.exists():return
    actual=proc.read_bytes().replace(b'\0',b' ').decode();assert 'TpccMixed' in actual and str(out/'run') in actual
    observations=[]
    for sig,label,pause in [(signal.SIGQUIT,'SIGQUIT thread dump',.5),(signal.SIGTERM,'SIGTERM',2),(signal.SIGKILL,'SIGKILL',0)]:
     if not proc.exists():break
     os.killpg(group,sig);observations.append({'wall_ns':time.time_ns(),'signal':label});time.sleep(pause)
    (out/'run/owned-client-timeout-stop.json').write_text(json.dumps({'pid':pid,'group':group,'verified_command':actual,'reason':'Recorded request-timeout receipt; client must stop even when server session was sleeping','signals':observations},indent=2));return
  monitor=threading.Thread(target=stop_stalled_client,daemon=True);monitor.start()
  try:result=watchdog.run(cmd,out/'run',timeout=1200,request_limit=15,db=meta['database'])
  finally:
   stop.set();monitor.join(timeout=4)
   receipt=out/'run/connection-id.json'
   if receipt.exists():
    cid=json.loads(receipt.read_text());cid=cid['connection_id']if isinstance(cid,dict)else cid;observations=[];deadline=time.monotonic()+60
    while True:
     active=subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-e','SELECT ID,DB,COMMAND,TIME,STATE,INFO FROM information_schema.PROCESSLIST WHERE ID='+str(int(cid))],text=True);observations.append({'wall_ns':time.time_ns(),'process':active})
     if not active.strip():break
     assert time.monotonic()<deadline,'Owned connection remained after60seconds';time.sleep(.25)
    (out/'run/strict-server-absence.json').write_text(json.dumps({'connection_id':cid,'absent_before_next_request':True,'observations':observations},indent=2))
 assert not result.get('timed_out'),result
 rows=[json.loads(line)for line in(out/'run/requests.jsonl').read_text().splitlines()];assert len(rows)==900
 before=json.loads((out/'run/before/manifest.json').read_text());after=json.loads((out/'run/after/manifest.json').read_text());deltas={key:after[key]['rows']-before[key]['rows']for key in before};assert deltas['orders']==487 and deltas['new_order']==487 and deltas['order_line']==4746 and deltas['history']==406,deltas
 assert sum(row['result'].get('rolled_back',False)for row in rows)==7
 direct=H/('gate-jac-seed900-tx-complete-v1'if a.program=='conventional'else'gate-graph-'+a.variant+'-900-tx-complete-v1')/'results';reference=[json.loads(line)for line in(direct/'requests.jsonl').read_text().splitlines()];assert [r['result']for r in rows]==[r['result']for r in reference],'Whole900 evolving output mismatch'
 for stage in ['before','after']:
  actual=json.loads((out/'run'/stage/'manifest.json').read_text());expected=json.loads((direct/stage/'manifest.json').read_text());assert {k:(v['rows'],v['sha256'])for k,v in actual.items()}=={k:(v['rows'],v['sha256'])for k,v in expected.items()},(stage,'Whole900 eight-table mismatch')
 (out/'correctness.json').write_text(json.dumps({'status':'PASS: all900 outputs and eight full before/after business relations equal independently verified final direct gate','reference_direct_gate':str(direct),'reference_independent_verification':str(direct.parent/'independent-model-verification.json'),'requests':900,'rollbacks':7,'row_deltas':deltas,'requests_with_call':sum(row['call_procedure']>0 for row in rows),'total_calls':sum(row['call_procedure']for row in rows),'execution':'hybrid compiled paths and actual source fallback'},indent=2))
print(out)
