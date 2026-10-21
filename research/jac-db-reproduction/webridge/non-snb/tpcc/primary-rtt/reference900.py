#!/usr/bin/env python3
"""Fresh compact-RTT original900 reference, using frozen mixed harness bytecode."""
import argparse,json,pathlib,signal,subprocess,sys,time,datetime
D=pathlib.Path(__file__).resolve().parent;H=D.parent;N=H.parent
sys.path.insert(0,str(D));import helpers as h;from extract import extract
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--port',type=int,default=18638);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
old=json.loads((H/'reference-900-index.json').read_text())['rows'];status=json.loads((H/'case-status.json').read_text());summaries=[]
for variant in ['conventional','full','pruned']:
 for phase in ['baseline','sp']:
  arm=('java_'if phase=='baseline'else'webridge_')+variant;source=next(r for r in old if r['arm']=='webridge_'+variant);root=pathlib.Path(source['raw_requests']).parent.parent;case=next(c for c in status if c['program']==('conventional'if variant=='conventional'else'graph')and c['variant']==('full'if variant=='conventional'else variant));out=a.out/arm;out.mkdir();run=out/'run'
  with h.lease('TPC-C compact original900 '+arm,out/'lease.json'):
   before=h.settings();assert before['logging'].split('\t')[0]=='0';h.sql("UPDATE performance_schema.setup_instruments SET ENABLED='NO',TIMED='NO' WHERE NAME LIKE 'statement/sp/%'");(out/'instrumentation-before.json').write_text(json.dumps(before,indent=2));proxy=None;log=(out/'proxy.log').open('w')
   try:
    subprocess.run([sys.executable,str(H/'reset_cell.py'),'--case',case['case'],'--phase','baseline','--receipt',str(out/'reset.json')],check=True)
    cases=json.loads((root/'cases.json').read_text())if phase=='sp'else{};(out/'cases.json').write_text(json.dumps(cases,indent=2))
    for c in cases.values():
     m=json.loads((pathlib.Path(c)/'metadata.json').read_text());folder=pathlib.Path(c)/'generated/sql'/m['api'];files=[folder/'graph-SP-function.sql',*sorted(folder.glob('graph-SP-*_sp_*.sql'))];r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot',m['database']],input=b"SET SESSION sql_mode=CONCAT(@@session.sql_mode,',NO_UNSIGNED_SUBTRACTION');\n"+b'\n'.join(f.read_bytes()for f in files),capture_output=True);assert r.returncode==0,r.stderr
    argv=json.loads((root/'run/command.json').read_text())['argv'];argv=[s.replace(str(root/'run'),str(run)).replace('127.0.0.1:55337','127.0.0.1:'+str(a.port))for s in argv];idx=argv.index('TpccMixed');argv[idx+2]=str(out/'cases.json');(out/'command.json').write_text(json.dumps(argv,indent=2));meta=json.loads((pathlib.Path(case['case'])/'metadata.json').read_text())
    proxy=subprocess.Popen([sys.executable,str(N/'littlex/primary-rtt/compact_proxy.py'),'--port',str(a.port),'--target-port','55337','--delay-ms','0','--trace',str(out/'compact.jsonl'),'--receipt',str(out/'proxy-cleanup.json')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    for _ in range(200):
     if '"ready": true'in(out/'proxy.log').read_text():break
     assert proxy.poll()is None;time.sleep(.05)
    else:raise RuntimeError('Proxy not ready')
    result=h.w.run(argv,run,timeout=1200,request_limit=15,db=meta['database']);h.absence(run,meta['database']);assert not result['timed_out'];rows=[json.loads(x)for x in(run/'requests.jsonl').read_text().splitlines()];assert len(rows)==900
    with(run/'rows.jsonl').open('w')as f:
     for r in rows:r['iteration']=r['idx'];f.write(json.dumps(r)+'\n')
   finally:
    if proxy and proxy.poll()is None:proxy.send_signal(signal.SIGTERM)
    if proxy:
     try:proxy.wait(timeout=5)
     except subprocess.TimeoutExpired:proxy.kill();proxy.wait()
    log.close();h.restore(before,out)
   measured=extract(out/'compact.jsonl',run,out/'rtt');entry={'family':'tpcc','workload':'original900','arm':arm,'requests':900,'warmup_count':100,'measured_count':800,'metric':'summed_db_call_rtt_ms','rtt_summary':str(out/'rtt/summary.json'),'raw_requests':str(run/'requests.jsonl'),'before':str(run/'before'),'after':str(run/'after'),'source_reference':source,'status':'awaiting_full_state_oracle','unaccepted_median_ms':measured['median_ms']};verify=[sys.executable,str(N/'verify_tpcc_model.py'),'--gate',str(out),'--seed-projection','jac','--original-prefix','900','--before-dir',str(run/'before'),'--after-dir',str(run/'after'),'--request-log',str(run/'requests.jsonl')];v=subprocess.run(verify,capture_output=True,text=True);(out/'oracle-stdout.log').write_text(v.stdout);(out/'oracle-stderr.log').write_text(v.stderr);(out/'oracle-command.json').write_text(json.dumps({'argv':verify,'returncode':v.returncode},indent=2));entry.update(status='accepted'if v.returncode==0 else'rejected_state_or_result',median_ms=measured['median_ms']if v.returncode==0 else None,oracle=str(out/'oracle-command.json'),actual_calls=sum(r['call_procedure']for r in rows),requests_with_call=sum(r['call_procedure']>0 for r in rows),active_requests=sum(bool(r['sp_enabled_end'])and r['call_procedure']>0 for r in rows));summaries.append(entry);(a.out/'rtt-reference-900-index.json').write_text(json.dumps({'rows':summaries},indent=2));print(arm,'collected; oracle pending',flush=True)
