#!/usr/bin/env python3
import pathlib,json,subprocess,sys
D=pathlib.Path(__file__).resolve().parent;H=D.parent;R=H/'mixed-conventional-full-20261021T013535Z';cases=json.loads((R/'cases.json').read_text());first=next(iter(cases.values()))
subprocess.run([sys.executable,str(H/'reset_cell.py'),'--case',first,'--phase','baseline','--receipt',str(D/'reset.json')],check=True)
for case in cases.values():
 home=pathlib.Path(case);m=json.loads((home/'metadata.json').read_text());folder=home/'generated/sql'/m['api'];files=[folder/'graph-SP-function.sql',*sorted(folder.glob('graph-SP-*_sp_*.sql'))]
 r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot',m['database']],input=b"SET SESSION sql_mode=CONCAT(@@session.sql_mode,',NO_UNSIGNED_SUBTRACTION');\n"+b'\n'.join(p.read_bytes()for p in files),capture_output=True);assert r.returncode==0,r.stderr
(D/'prepare-complete.json').write_text(json.dumps({'cases':cases,'installed':True},indent=2))
