#!/usr/bin/env python3
import pathlib,json,sys,subprocess,time,importlib.util
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
s=importlib.util.spec_from_file_location('c',H.parents[1]/'integration/control.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
with lease('littlex all13business-field equality',H/('verify-lease-'+c.now()+'.json')):
 for t in ['t20','t50','t100','t200']:
  d=H/'fixtures'/t;db=json.loads((d/'mysql-load.json').read_text())['database'];cmd=['taskset','-c','9,19',str(c.SERVER/'bin/java'),'-Dlittlex.url=jdbc:mysql://127.0.0.1:55337/'+db+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8','-cp',str(H/'classes')+':'+c.CP,'VerifyLittleX',str(d)];r=subprocess.run(cmd,capture_output=True,text=True);(d/'verify-command.json').write_text(json.dumps({'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2));assert r.returncode==0,r.stderr;print(t,r.stdout,flush=True)
