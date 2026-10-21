#!/usr/bin/env python3
"""Retry one immutable recorded graph with a named compatibility overlay and exact state gate."""
import argparse,pathlib,json,subprocess,sys,time,hashlib
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
from business_state import snapshot
p=argparse.ArgumentParser();p.add_argument('case',type=pathlib.Path);p.add_argument('--graph',required=True,type=pathlib.Path);p.add_argument('--overlay',required=True,type=pathlib.Path);a=p.parse_args();case=a.case.resolve();meta=json.loads((case/'metadata.json').read_text());out=H/('compiler-retry-'+str(time.time_ns()));out.mkdir();receipt={'case':str(case),'graph':str(a.graph.resolve()),'graph_sha256':hashlib.sha256(a.graph.read_bytes()).hexdigest(),'overlay':str(a.overlay.resolve()),'status':'running','stages':[]}
def save(): (out/'summary.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(stage,extra=[]):
 argv=[sys.executable,str(H/'resume_case.py'),stage,str(case),'--lease-held',*extra];r=subprocess.run(argv,capture_output=True);folder=out/stage;folder.mkdir();(folder/'command.json').write_text(json.dumps(argv,indent=2));(folder/'stdout.log').write_bytes(r.stdout);(folder/'stderr.log').write_bytes(r.stderr);paths=[pathlib.Path(x)for x in r.stdout.decode(errors='replace').splitlines()if x.startswith(str(H/'cases'))];path=paths[-1]if paths else None;receipt['stages'].append({'stage':stage,'returncode':r.returncode,'path':str(path)if path else None});save();assert r.returncode==0,(stage,str(path));return path
save()
try:
 with lease('littlex immutable compiler retry and installed state gate',out/'lease.json'):
  run('synth',['--graph',str(a.graph.resolve()),'--overlay',str(a.overlay.resolve())]);api=meta['api'];files=[case/'generated/sql'/api/'graph-SP-function.sql',*sorted((case/'generated/sql'/api).glob('graph-SP-*_sp_*.sql'))];assert len(files)>1 and all(f.exists()for f in files)
  script=b"SET SESSION sql_mode=CONCAT(@@session.sql_mode,IF(FIND_IN_SET('NO_UNSIGNED_SUBTRACTION',@@session.sql_mode),'',',NO_UNSIGNED_SUBTRACTION'));SELECT @@session.sql_mode,@@global.sql_mode;\n"+b'\n'.join(f.read_bytes()for f in files)
  cmd=['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot',meta['database']];r=subprocess.run(cmd,input=script,capture_output=True);(out/'install-command.json').write_text(json.dumps(cmd,indent=2));(out/'install.stdout').write_bytes(r.stdout);(out/'install.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr;receipt['generated_sources']=[{'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}for f in files];save()
  direct=run('baseline');before=snapshot(meta['database'],meta['implementation']!='LittleXSql');(out/'baseline-state.json').write_text(json.dumps(before,indent=2));dr=json.loads((direct/'report.json').read_text())
  optimized=run('optimized');after=snapshot(meta['database'],meta['implementation']!='LittleXSql');(out/'optimized-state.json').write_text(json.dumps(after,indent=2));sr=json.loads((optimized/'report.json').read_text());assert before==after,'Complete canonical business state mismatch';assert dr['result']==sr['result'],'Returned result mismatch';receipt.update(status='PASS with explicit frontend compatibility overlay',result=sr['result'],activation=sr['region'],session_status_delta=sr['session_status_delta'],actual_questions=sr['server_questions'],correctness='Exact returned result and complete canonical business state after independent pristine resets')
except Exception as e:receipt.update(status='failed-stage',error=repr(e))
save();print(out);sys.exit(0 if receipt['status'].startswith('PASS')else 1)
