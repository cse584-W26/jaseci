#!/usr/bin/env python3
"""Fresh-state original-reference and RTT cells with genuine generated-API fallback."""
import pathlib,json,sys,argparse,subprocess,time,statistics,signal,fcntl,importlib.util,hashlib
H=pathlib.Path(__file__).resolve().parent.parent;W=H.parents[1]
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
t=load('timer',H/'timing_command.py');state=load('states',H/'business_state.py');wd=load('wd',W/'benchmark-comparison/owned_watchdog.py');lease=load('lease',H.parent/'measurement_lease.py').lease
wd.ctl.LIMITS={'rss_bytes':12*1024**3,'output_bytes':8*1024**3}
def sql(q):return subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-N','-B','-uroot','-e',q],text=True)
def settings():return dict(instruments=sql('SELECT NAME,ENABLED,TIMED FROM performance_schema.setup_instruments ORDER BY NAME'),consumers=sql('SELECT NAME,ENABLED FROM performance_schema.setup_consumers ORDER BY NAME'),logging=sql('SELECT @@global.general_log,@@global.log_output'))
def restore(before,out):
 parts=[]
 for line in before['instruments'].splitlines():
  n,e,timed=line.split('\t')
  if n.startswith('statement/sp/'):parts.append("UPDATE performance_schema.setup_instruments SET ENABLED='"+e+"',TIMED='"+timed+"' WHERE NAME='"+n+"';")
 sql('\n'.join(parts));after=settings();assert after==before;out.write_text(json.dumps({'exact_restoration':True,'state':after},indent=2))
def absence(out):
 p=out/'connection-id.json'
 if not p.exists():return
 cid=int(json.loads(p.read_text())['connection_id']);observed=[];end=time.monotonic()+90
 while True:
  row=sql('SELECT ID,DB,COMMAND,TIME,STATE FROM information_schema.PROCESSLIST WHERE ID='+str(cid));observed.append({'wall_ns':time.time_ns(),'row':row})
  if not row.strip():break
  assert time.monotonic()<end,'Owned database connection remains';time.sleep(.25)
 (out/'server-absence.json').write_text(json.dumps({'connection_id':cid,'absent_before_next_cell':True,'observations':observed},indent=2))
def hashes(x):return {k:(v['rows'],v['sha256'])for k,v in x.items()}
def percentile(v,q):
 a=sorted(v);r=(len(a)-1)*q;i=int(r);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(r-i)
p=argparse.ArgumentParser();p.add_argument('--build-snapshot',type=pathlib.Path);p.add_argument('--bundle-map',type=pathlib.Path,required=True,help='implementation→successful generated API bundle; missing regions retain measured direct fallback');p.add_argument('--out',type=pathlib.Path);p.add_argument('--tiers',nargs='+',default=['t20','t50','t100','t200']);p.add_argument('--implementations',nargs='+',default=['LittleXSql','LittleXFull','LittleXPruned']);p.add_argument('--methods',nargs='+',default=['reference','latency']);p.add_argument('--delays',nargs='+',type=int,default=[0,2,10]);p.add_argument('--operations',nargs='+');p.add_argument('--port',type=int,default=18537);a=p.parse_args();a.out=a.out or H/'timing'/str(time.time_ns());a.out.mkdir(parents=True,exist_ok=False);bundles=json.loads(a.bundle_map.read_text());plans=json.loads((H/'plans/manifest.json').read_text());summary=[]
if a.build_snapshot:
 a.build_snapshot=a.build_snapshot.resolve();manifest=json.loads((a.build_snapshot/'snapshot-sha256.json').read_text())
 import hashlib
 for name,expected in manifest.items():assert hashlib.sha256((a.build_snapshot/name).read_bytes()).hexdigest()==expected,('Snapshot changed',name)
 (a.out/'build-snapshot.json').write_text(json.dumps({'path':str(a.build_snapshot),'sha256_manifest':manifest},indent=2)+'\n')
def save():
 (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for delay in a.delays:
 selected=[r for r in plans if (not a.operations or r['operation']in a.operations) and r['tier']in a.tiers and r['method']in a.methods and not(r['method']=='reference'and delay!=0)]
 if not selected:continue
 d=a.out/('delay-'+str(delay)+'ms');d.mkdir()
 with lease('littlex Java exclusive quiet '+str(delay)+'ms',d/'lease.json'):
  before=settings();assert before['logging'].split('\t')[0]=='0';(d/'instrumentation-before.json').write_text(json.dumps(before,indent=2));sql("UPDATE performance_schema.setup_instruments SET ENABLED='NO',TIMED='NO' WHERE NAME LIKE 'statement/sp/%'");log=(d/'proxy.log').open('w');proxy=subprocess.Popen([sys.executable,str(H/'primary-rtt/compact_proxy.py'),'--port',str(a.port),'--target-port','55337','--delay-ms',str(delay),'--trace',str(d/'compact-protocol.jsonl'),'--receipt',str(d/'proxy-cleanup.json')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   for _ in range(100):
    if '"ready": true'in(d/'proxy.log').read_text():break
    assert proxy.poll()is None;time.sleep(.05)
   else:raise RuntimeError('Proxy not ready')
   cp=str(W/'latency-comparison/classes')+':'+t.c.CP;t.c.command([str(t.c.SERVER/'bin/java'),'-cp',cp,'Roundtrip',str(a.port),str(d/'roundtrip-before.json')],d/'calibration-before',60)
   for plan in selected:
    assert hashlib.sha256(pathlib.Path(plan['path']).read_bytes()).hexdigest()==plan['sha256'],('Frozen plan changed',plan['path'])
    tier=plan['tier'];db='jac_lx_'+tier+'_20261020'
    for impl in a.implementations:
     cell=d/tier/(plan['workload']+'-'+plan['operation']+'-'+plan['method'])/impl;cell.mkdir(parents=True);baseline=None
     for phase in ['baseline','sp']:
      base=dict(family='littlex',workload=plan['workload'],operation=plan['operation'],tier=tier,system=impl+(' + WeBridge'if phase=='sp'else''),phase=phase,delay_ms=delay,method=plan['method'],warmup_count=plan['warmup'],measured_count_requested=plan['measured'],plan=plan['path'],plan_sha256=plan['sha256']);bundle=bundles.get(impl)
      base.update(instrumentation='compact-protocol-rtt-v1',primary_metric='summed_db_call_rtt_ms',connection_compatibility=str(H/'charset-compatibility.json'),build_snapshot=str(a.build_snapshot)if a.build_snapshot else str(H/'build.json'),webridge_bundle=str(bundle)if phase=='sp'and bundle else None,frontend_selection=str(pathlib.Path(bundle)/'selection-provenance.json')if phase=='sp'and bundle else None)
      if phase=='sp':
       operations=json.loads((pathlib.Path(bundle)/'metadata.json').read_text())['operations']if bundle else{}
       required=[plan['operation']+'/dispatch',plan['operation']+'/business']if impl=='LittleXFull'and plan['operation']=='feed'else[plan['operation']+'/business']if impl=='LittleXPruned'and plan['operation']=='feed'else[plan['operation']]
       available=all(k in operations for k in required)
       if not bundle or(plan['workload']!='W3'and not available):
        pointer=json.loads((H/'selected-cases.json').read_text());selected_manifest=pathlib.Path(pointer['manifest']);failures=json.loads(selected_manifest.read_text())['original_and_repaired_stage_evidence'];relevant=[]
        for failure in failures:
         case=pathlib.Path(failure['case'])if failure.get('case')else None
         if case and(case/'metadata.json').exists():
          metadata=json.loads((case/'metadata.json').read_text());inp=json.loads((pathlib.Path(metadata['snapshot'])/'input.json').read_text())
          if metadata['implementation']==impl and(inp['op']==plan['operation']or plan['workload']=='W3'):relevant.append(failure)
        stage=relevant[-1].get('failed_stage')if relevant else'no accepted generated API'
        summary.append(dict(base,status='failed-pipeline; '+str(stage),failed_stage=stage,pipeline_evidence=relevant,stage_manifest=str(selected_manifest),n=0,median_ms=None));save();continue
      out=cell/phase;out.mkdir();start=time.time_ns();row=None
      try:
       subprocess.run([sys.executable,str(H/'reset_relations.py'),tier,'--lease-held']+(['--bundle',str(bundle),'--install-receipt',str(out/'bundle-install.json')]if phase=='sp'else[]),check=True)
       beforestate=state.snapshot(db,impl!='LittleXSql');(out/'before-state.json').write_text(json.dumps(beforestate,indent=2));argv=t.command(plan['path'],out,db,a.port,phase,impl,bundle)
       if a.build_snapshot:argv=[x.replace(str(H/'classes'),str(a.build_snapshot/'classes')).replace(str(H/'native-templates.json'),str(a.build_snapshot/'native-templates.json'))for x in argv]
       with(W/'integration/.mysql-sp-profile.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX);guard=wd.run(argv,out,timeout=7200,request_limit=15,db=db)
       absence(out);assert not guard['timed_out'],'Request exceeded15s; sequence incomplete';subprocess.run([sys.executable,str(H/'verify_outputs.py'),'--tier',tier,'--plan',plan['path'],'--results',str(out/'full-results.jsonl.gz'),'--out',str(out/'source-oracle.json')],check=True);requests=[json.loads(s)for s in(out/'rows.jsonl').read_text().splitlines()];assert len(requests)==plan['warmup']+plan['measured'];measured=[r for r in requests if not r['warmup']];assert len(measured)==plan['measured'];afterstate=state.snapshot(db,impl!='LittleXSql');(out/'after-state.json').write_text(json.dumps(afterstate,indent=2));oracle=json.loads((out/'source-oracle.json').read_text());state.assert_expected(beforestate,oracle['initial_expected_common_state']);state.assert_expected(afterstate,oracle['final_expected_common_state']);(out/'independent-state-oracle.json').write_text(json.dumps({'status':'PASS','scope':oracle['common_state_scope'],'initial_actual':beforestate,'initial_expected':oracle['initial_expected_common_state'],'final_actual':afterstate,'final_expected':oracle['final_expected_common_state'],'response_oracle':str(out/'source-oracle.json')},indent=2)+'\n');v=[r['ms']for r in measured];calls=[r['status_delta'].get('Com_call_procedure',0)for r in measured]
       row=dict(base,status='measured',n=len(v),median_ms=statistics.median(v),p95_ms=percentile(v,.95),thread_cpu_median_ms=statistics.median(r['thread_cpu_ms']for r in measured),questions=sorted(set(r['questions']for r in measured)),call_procedure=sorted(set(calls)),call_requests=sum(c>0 for c in calls),call_fraction=sum(c>0 for c in calls)/len(calls),sdk_enabled_at_end_requests=sum(bool(r.get('sp_enabled_at_end'))for r in measured),sdk_enabled_at_end_fraction=sum(bool(r.get('sp_enabled_at_end'))for r in measured)/len(measured),sdk_flag_scope="sp_enabled_at_end at request completion; for multi-region requests this is the final region flag",activation_by_operation={op:{'requests':sum(r['op']==op for r in measured),'call_requests':sum(r['op']==op and r['status_delta'].get('Com_call_procedure',0)>0 for r in measured),'sdk_enabled_at_end_requests':sum(r['op']==op and bool(r.get('sp_enabled_at_end'))for r in measured)}for op in sorted({r['op']for r in measured})},rows_path=str(out/'rows.jsonl'),source_result_oracle=str(out/'source-oracle.json'),independent_state_oracle=str(out/'independent-state-oracle.json'),full_results_path=str(out/'full-results.jsonl.gz'),initial_state=str(out/'before-state.json'),final_state=str(out/'after-state.json'),per_operation_counts=plan['per_operation_counts'],start_wall_ns=start,end_wall_ns=time.time_ns())
       if phase=='baseline':baseline=(requests,beforestate,afterstate)
       else:
        ar,bs,as_=baseline;assert [r['canonical_result_sha256']for r in ar]==[r['canonical_result_sha256']for r in requests],'Evolving result hashes differ';assert hashes(bs)==hashes(beforestate)and hashes(as_)==hashes(afterstate),'Business state differs';receipt={'status':'PASS','compared_requests':len(requests),'scope':'all evolving canonical result hashes plus complete common business entity/relation state','before':hashes(beforestate),'after':hashes(afterstate)};(cell/'correctness.json').write_text(json.dumps(receipt,indent=2));row['correctness']=str(cell/'correctness.json')
      except BaseException as e:
       if isinstance(e,KeyboardInterrupt):raise
       absence(out);row=dict(base,status='failed-runtime-or-correctness',error=repr(e),n=0,median_ms=None,raw_path=str(out),start_wall_ns=start,end_wall_ns=time.time_ns())
      if row['status']=='measured':
       ex=load('compact_extract',H/'primary-rtt/extract.py');rtt=ex.extract(d/'compact-protocol.jsonl',out,out/'primary-rtt');row['application_median_ms_secondary']=row.pop('median_ms');row['application_p95_ms_secondary']=row.pop('p95_ms');row['median_ms']=rtt['median_ms'];row['primary_rtt']=str(out/'primary-rtt/summary.json');row['primary_rows_path']=rtt['rows_path'];row['metric']=rtt['metric']
      summary.append(row);save();print(tier,plan['workload'],plan['operation'],impl,phase,delay,row['status'],flush=True)
   t.c.command([str(t.c.SERVER/'bin/java'),'-cp',cp,'Roundtrip',str(a.port),str(d/'roundtrip-after.json')],d/'calibration-after',60)
  finally:
   if proxy.poll()is None:proxy.send_signal(signal.SIGTERM)
   try:proxy.wait(timeout=5)
   except subprocess.TimeoutExpired:proxy.kill();proxy.wait()
   log.close();(d/'proxy-process.json').write_text(json.dumps({'pid':proxy.pid,'returncode':proxy.returncode,'stopped':proxy.poll()is not None},indent=2));restore(before,d/'instrumentation-restored.json')
   import gzip,shutil
   raw=d/'compact-protocol.jsonl';packed=d/'compact-protocol.jsonl.gz'
   if raw.exists():
    digest=hashlib.sha256()
    with raw.open('rb')as source,gzip.open(packed,'wb',compresslevel=6)as dest:
     while chunk:=source.read(1024*1024):digest.update(chunk);dest.write(chunk)
    (d/'compact-trace-receipt.json').write_text(json.dumps({'raw_path':str(raw),'raw_sha256':digest.hexdigest(),'raw_bytes':raw.stat().st_size,'lossless_gzip':str(packed),'compressed_bytes':packed.stat().st_size},indent=2)+'\n')
    for receipt in d.rglob('primary-rtt/summary.json'):
     content=json.loads(receipt.read_text());content['trace']=str(packed);receipt.write_text(json.dumps(content,indent=2)+'\n')
    raw.unlink()
print(a.out)
