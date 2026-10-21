#!/usr/bin/env python3
"""All seed read identities and committed write gates for graph Java implementations."""
import pathlib,json,sys,subprocess,time,importlib.util,argparse
H=pathlib.Path(__file__).resolve().parent;W=H.parents[1];sys.path.insert(0,str(H.parent));from measurement_lease import lease
s=importlib.util.spec_from_file_location('c',W/'integration/control.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
p=argparse.ArgumentParser();p.add_argument('--implementations',nargs='+',default=['LittleXFull','LittleXPruned']);p.add_argument('--tiers',nargs='+',default=['t20','t50','t100','t200']);a=p.parse_args()
for impl in a.implementations:
 for tier in a.tiers:
  d=H/'fixtures'/tier;db=json.loads((d/'mysql-load.json').read_text())['database'];out=H/'gates'/tier/(impl+'-'+str(time.time_ns()))
  with lease('littlex '+impl+' semantic gate '+tier,out.with_suffix('.lease.json')):
   subprocess.run([sys.executable,str(H/'reset_relations.py'),tier,'--lease-held'],check=True)
   url='jdbc:mysql://127.0.0.1:55337/'+db+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true';cmd=['taskset','-c','9,19',str(c.SERVER/'bin/java'),'-Xmx2g','-Dlittlex.url='+url,'-Dlittlex.implementation='+impl,'-Dlittlex.templates='+str(H/'native-templates.json'),'-cp',str(H/'classes')+':'+c.CP,'LittleXGraphGate',str(H/(tier+'-graph-gate-inputs.json')),str(out/'results')];c.command(cmd,out,600);r=json.loads((out/'results/summary.json').read_text());assert r['passed']==203;print(impl,tier,r,flush=True)
