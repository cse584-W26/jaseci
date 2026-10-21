#!/usr/bin/env python3
"""Actually gate genuine emitted SQL when synthesis exited after writing procedures."""
import pathlib,json,subprocess,sys,time,hashlib,importlib.util,gzip
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
spec=importlib.util.spec_from_file_location('states',H/'business_state.py');states=importlib.util.module_from_spec(spec);spec.loader.exec_module(states)
out=H/('emitted-recovery-'+str(time.time_ns()));out.mkdir();rows=[]
def save():(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
def command(argv,d):
 d.mkdir();(d/'command.json').write_text(json.dumps(argv,indent=2)+'\n');r=subprocess.run(argv,capture_output=True);(d/'stdout.log').write_bytes(r.stdout);(d/'stderr.log').write_bytes(r.stderr);assert r.returncode==0,(argv,r.returncode,r.stderr.decode(errors='replace')[-2000:]);paths=[pathlib.Path(s)for s in r.stdout.decode(errors='replace').splitlines()if s.startswith(str(H/'cases'))];return paths[-1]if paths else None
seen=set()
for receipt in sorted(H.glob('pipeline-*/summary.json')):
 for source in json.loads(receipt.read_text()):
  if source.get('failed_stage')!='synth'or not source.get('case'):continue
  case=pathlib.Path(source['case']);meta=json.loads((case/'metadata.json').read_text());folder=case/'generated/sql'/meta['api'];procs=sorted(folder.glob('graph-SP-*_sp_*.sql'))
  if not procs or case in seen:continue
  seen.add(case);d=out/(meta['implementation']+'-'+case.name);d.mkdir();r={'case':str(case),'source_pipeline':str(receipt),'implementation':meta['implementation'],'status':'running','stages':[]};rows.append(r);save()
  try:
   with lease('littleX emitted-artifact actual CALL recovery',d/'lease.json'):
    before=command([sys.executable,str(H/'resume_case.py'),'baseline',str(case),'--lease-held'],d/'baseline');baseline=json.loads((before/'report.json').read_text());initial_after=states.snapshot(meta['database'],meta['implementation']!='LittleXSql');(d/'baseline-state.json').write_text(json.dumps(initial_after,indent=2)+'\n');r['stages'].append({'stage':'baseline','path':str(before)})
    files=[folder/'graph-SP-function.sql',*procs];(d/'sources.json').write_text(json.dumps([{'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}for f in files],indent=2)+'\n');sql=b"SET SESSION sql_mode=CONCAT(@@session.sql_mode,IF(FIND_IN_SET('NO_UNSIGNED_SUBTRACTION',@@session.sql_mode),'',',NO_UNSIGNED_SUBTRACTION'));\n"+b'\n'.join(f.read_bytes()for f in files);installed=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot',meta['database']],input=sql,capture_output=True);(d/'install.stdout.log').write_bytes(installed.stdout);(d/'install.stderr.log').write_bytes(installed.stderr);assert installed.returncode==0,installed.stderr.decode();r['stages'].append({'stage':'install','status':'PASS'})
    after=command([sys.executable,str(H/'resume_case.py'),'optimized',str(case),'--lease-held'],d/'optimized');result=json.loads((after/'report.json').read_text());actual=states.snapshot(meta['database'],meta['implementation']!='LittleXSql');(d/'optimized-state.json').write_text(json.dumps(actual,indent=2)+'\n');assert actual==initial_after,'Committed common state differs';assert result['result']==baseline['result'],'Full response differs';assert result['session_status_delta'].get('Com_call_procedure',0)>0 and result['region']['sp_enabled_at_end'],'Generated API did not remain active'
    inp=json.loads((pathlib.Path(meta['snapshot'])/'input.json').read_text());plan=d/'one-request-plan.json';plan.write_text(json.dumps([{'input':inp,'warmup':False,'iteration':0}],indent=2)+'\n');full=d/'full-results.jsonl.gz'
    with gzip.open(full,'wt')as f:f.write(json.dumps({'plan_ordinal':0,'warmup':False,'iteration':0,'result':result['result']})+'\n')
    tier=meta['database'].split('_')[2];command([sys.executable,str(H/'verify_outputs.py'),'--tier',tier,'--plan',str(plan),'--results',str(full),'--out',str(d/'source-oracle.json')],d/'source-oracle-command');oracle=json.loads((d/'source-oracle.json').read_text());states.assert_expected(actual,oracle['final_expected_common_state']);r.update(status='PASS genuine emitted SQL installed and active',activation=result['region'],session_status_delta=result['session_status_delta'],result_state_oracle=str(d/'source-oracle.json'),actual_final_state=str(d/'optimized-state.json'),optimized=str(after),frontend=source.get('frontend_repair'),original_failure=source['stages'])
  except BaseException as e:r.update(status='failed actual emitted-artifact gate',error=repr(e))
  save();print(case.name,r['status'],flush=True)
print(out,flush=True)
