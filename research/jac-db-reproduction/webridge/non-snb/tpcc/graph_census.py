#!/usr/bin/env python3
"""Actual three-request graph-port census and full mutable-state gates per class."""
import argparse,hashlib,importlib.util,json,pathlib,shutil,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1]
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=mod('original',B/'integration/control.py');lease=mod('lease',H.parent/'measurement_lease.py').lease
p=argparse.ArgumentParser();p.add_argument('--variant',choices=['full','pruned'],default='full');a=p.parse_args();out=H/('graph-census-'+a.variant);out.mkdir(exist_ok=False);summary=[]
expected={'payment_name_GC':12,'new_order_rollback':16,'payment_id_GC':10,'new_order_5':14,'new_order_15':14,'payment_name_BC':11,'payment_id_BC':10}
with lease('TPC-C graph '+a.variant+' actual census',out/'lease.json'):
 if not(H/'graph-context.json').exists():subprocess.run([sys.executable,str(H/'prepare_graph_context.py')],check=True)
 subprocess.run([sys.executable,str(H/'graph_views.py')],check=True)
 (out/'source').mkdir();shutil.copytree(H/'classes',out/'classes')
 for f in H.glob('*.java'):shutil.copy2(f,out/'source'/f.name)
 shutil.copy2(H/'graph-context.json',out/'graph-context.json');(out/'source-sha256.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in(out/'source').glob('*.java')},indent=2))
 cp=':'.join([str(out/'classes'),str(B/'integration/numeric-width/classes'),str(B/'integration/jdbc-string/combined'),str(B/'integration/sql-frontend/classes'),m.CP])
 for label in expected:
  d=out/label;d.mkdir();subprocess.run([sys.executable,str(H/'graph_fixture.py'),'reset','--receipt',str(d/'reset.json')],check=True);x=json.loads((H/'inputs'/(label+'.json')).read_text());(d/'plan.json').write_text(json.dumps([x,x,x],indent=2));cmd=[str(m.SERVER/'bin/java'),'-Xmx2g','-Dexperiment.program=graph','-Dexperiment.pruned='+str(a.variant=='pruned').lower(),'-Dexperiment.graph.context='+str(out/'graph-context.json'),'-Dexperiment.mysql.url=jdbc:mysql://127.0.0.1:55337/jac_tpcc_graph?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useLocalSessionState=true','-cp',cp,'TpccGate',str(d/'plan.json'),str(d/'results')];m.command(cmd,d/'run',300)
  rows=[json.loads(line)for line in(d/'results/requests.jsonl').read_text().splitlines()];assert len(rows)==3
  if a.variant=='full':assert [r['jdbc_calls']for r in rows[1:]]==[expected[label]]*2,(label,rows)
  before=json.loads((d/'results/before/manifest.json').read_text());after=json.loads((d/'results/after/manifest.json').read_text())
  if label=='new_order_rollback':assert {k:v['sha256']for k,v in before.items()}=={k:v['sha256']for k,v in after.items()},'Rollback state changed'
  summary.append({'workload':label,'variant':a.variant,'requests':str(d/'results/requests.jsonl'),'jdbc_calls':[r['jdbc_calls']for r in rows],'source_count_gate':'PASS'if a.variant=='full'else'pruned measured','before':before,'after':after});(out/'summary.json').write_text(json.dumps(summary,indent=2));print(label,a.variant,'PASS',flush=True)
print(out)
