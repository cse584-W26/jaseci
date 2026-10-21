#!/usr/bin/env python3
"""Reset/install helper invoked inside a caller-owned host lease."""
import argparse,hashlib,json,pathlib,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--case',type=pathlib.Path,required=True);p.add_argument('--phase',choices=['baseline','sp'],required=True);p.add_argument('--receipt',type=pathlib.Path,required=True);a=p.parse_args();assert not a.receipt.exists();a.receipt.parent.mkdir(parents=True,exist_ok=True);meta=json.loads((a.case/'metadata.json').read_text());start=time.time_ns()
cmd=[sys.executable,str(H/'graph_fixture.py'),'reset','--receipt',str(a.receipt.with_name('graph-reset.json'))]if meta['program']=='graph'else[sys.executable,str(H/'relational_fixture.py'),'load','--database',meta['database']]
r=subprocess.run(cmd,capture_output=True,text=True);a.receipt.with_name('reset-stdout.log').write_text(r.stdout);a.receipt.with_name('reset-stderr.log').write_text(r.stderr);assert r.returncode==0,r.stderr
receipt={'start_wall_ns':start,'case':str(a.case),'phase':a.phase,'reset_command':cmd,'database':meta['database'],'reset_returncode':r.returncode}
if a.phase=='sp':
 folder=a.case/'generated/sql'/meta['api'];files=[folder/'graph-SP-function.sql',*sorted(folder.glob('graph-SP-*_sp_*.sql'))];assert len(files)>1 and all(f.exists()for f in files)
 r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot',meta['database']],input=((b"SET SESSION sql_mode=CONCAT(@@session.sql_mode,',NO_UNSIGNED_SUBTRACTION');\n"if meta['manifest'].get('session_configuration',{}).get('no_unsigned_subtraction')else b'')+b'\n'.join(f.read_bytes()for f in files)),capture_output=True);a.receipt.with_name('install-stdout.log').write_bytes(r.stdout);a.receipt.with_name('install-stderr.log').write_bytes(r.stderr);receipt.update(install_returncode=r.returncode,sql_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in files});assert r.returncode==0,r.stderr
if a.phase=='sp':
 modes=subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-e',"SELECT ROUTINE_NAME,SQL_MODE FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA='"+meta['database']+"' ORDER BY ROUTINE_NAME"],text=True);receipt['routine_creation_sql_modes']=modes;receipt['declared_session_configuration']=meta['manifest'].get('session_configuration')
receipt['end_wall_ns']=time.time_ns();a.receipt.write_text(json.dumps(receipt,indent=2))
