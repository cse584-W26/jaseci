#!/usr/bin/env python3
"""Run executable conventional read/write gates against dedicated matched fixtures."""
import pathlib,json,sys,subprocess,importlib.util,time
H=pathlib.Path(__file__).resolve().parent;W=H.parents[1];sys.path.insert(0,str(H.parent));from measurement_lease import lease
sp=importlib.util.spec_from_file_location('control',W/'integration/control.py');c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)
for tier in ['t20','t50','t100','t200']:
 d=H/'fixtures'/tier;db=json.loads((d/'mysql-load.json').read_text())['database'];out=H/'gates'/tier/('conventional-'+c.now())
 with lease('littlex conventional semantic gate '+tier,out.parent/(out.name+'-lease.json')):
  subprocess.run([sys.executable,str(H/'reset_relations.py'),tier,'--lease-held'],check=True)
  url='jdbc:mysql://127.0.0.1:55337/'+db+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true';cmd=[str(c.SERVER/'bin/java'),'-Xmx2g','-Dlittlex.url='+url,'-cp',str(H/'classes')+':'+c.CP,'LittleXGate',str(H/(tier+'-gate-inputs.json')),str(out/'results')];c.command(cmd,out,300)
  result=json.loads((out/'results/summary.json').read_text());assert result['passed']==203;print(tier,result,flush=True)
