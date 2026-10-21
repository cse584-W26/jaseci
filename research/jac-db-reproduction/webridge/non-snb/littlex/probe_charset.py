import pathlib,sys,subprocess,json,time,importlib.util,shutil
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
spec=importlib.util.spec_from_file_location('timer',H/'timing_command.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t);out=H/'charset-probe'/str(time.time_ns());out.mkdir(parents=True);shutil.copy2(H/'CharsetProbe.java',out/'CharsetProbe.java');shutil.copy2(__file__,out/'probe_charset.executed.py')
with lease('littleX exact JDBC charset diagnostic',out/'lease.json'):
 cp=str(H/'classes')+':'+t.c.CP;cmd=[str(t.c.SERVER/'bin/javac'),'-cp',cp,'-d',str(out),str(out/'CharsetProbe.java')];r=subprocess.run(cmd,capture_output=True);(out/'compile.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr
 for tier in ['t20','t50','t100','t200']:
  for suffix,extra in [('default',''),('utf8mb4-collation','&connectionCollation=utf8mb4_bin')]:
   url='jdbc:mysql://127.0.0.1:55337/jac_lx_'+tier+'_20261020?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true'+extra;argv=[str(t.c.SERVER/'bin/java'),'-cp',str(out)+':'+cp,'CharsetProbe',url];r=subprocess.run(argv,capture_output=True,timeout=30);(out/(tier+'-'+suffix+'.stderr.log')).write_bytes(r.stderr);assert r.returncode==0,r.stderr;data=json.loads(r.stdout.decode().splitlines()[-1]);data['jdbc_url']=url;(out/(tier+'-'+suffix+'.json')).write_text(json.dumps(data,indent=2)+'\n');print(tier,suffix,data,flush=True)
print(out,flush=True)
