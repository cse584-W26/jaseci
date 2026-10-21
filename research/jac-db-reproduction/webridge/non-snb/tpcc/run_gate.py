#!/usr/bin/env python3
"""Frozen conventional Java execution of the original 900-request transaction plan."""
import argparse,hashlib,importlib.util,json,pathlib,shutil,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1]
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=mod('original',B/'integration/control.py');lease=mod('lease',H.parent/'measurement_lease.py').lease
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--program',choices=['conventional','graph'],default='conventional');parser.add_argument('--variant',choices=['full','pruned'],default='full');parser.add_argument('--attempt',default='');args=parser.parse_args();db='jac_tpcc_graph'if args.program=='graph'else'jac_tpcc_conventional'
out=H/('gate-jac-seed900'if args.program=='conventional'else'gate-graph-'+args.variant+'-900');out=out.with_name(out.name+('-'+args.attempt if args.attempt else''));out.mkdir(exist_ok=False);(out/'source').mkdir();shutil.copytree(H/'classes',out/'classes')
for f in H.glob('*.java'):shutil.copy2(f,out/'source'/f.name)
shutil.copy2(H.parent/'tpcc-plan-900.json',out/'plan.json');
if args.program=='graph':shutil.copy2(H/'graph-context.json',out/'graph-context.json')
manifest={'source':{p.name:sha(p)for p in(out/'source').glob('*.java')},'classes':{p.name:sha(p)for p in(out/'classes').glob('*.class')},'plan_sha256':sha(out/'plan.json'),'graph_context_sha256':sha(out/'graph-context.json')if args.program=='graph'else None};(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
cp=':'.join([str(out/'classes'),str(B/'integration/numeric-width/classes'),str(B/'integration/jdbc-string/combined'),str(B/'integration/sql-frontend/classes'),m.CP]);cmd=[str(m.SERVER/'bin/java'),'-Xmx2g','-Dexperiment.program='+args.program,'-Dexperiment.pruned='+str(args.variant=='pruned').lower(),'-Dexperiment.graph.context='+str(out/'graph-context.json'),'-Dexperiment.mysql.url=jdbc:mysql://127.0.0.1:55337/'+db+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useLocalSessionState=true','-cp',cp,'TpccGate',str(out/'plan.json'),str(out/'results')]
with lease('tpcc-conventional-full900-correctness',out/'lease.json'):
 reset=[sys.executable,str(H/'graph_fixture.py'),'reset','--receipt',str(out/'reset.json')]if args.program=='graph'else[sys.executable,str(H/'relational_fixture.py'),'load'];r=subprocess.run(reset,capture_output=True);(out/'reset-stdout.log').write_bytes(r.stdout);(out/'reset-stderr.log').write_bytes(r.stderr);assert r.returncode==0,r.stderr
 m.command(cmd,out/'run',300)
 rows=[json.loads(s)for s in(out/'results/requests.jsonl').read_text().splitlines()];assert len(rows)==900
 before=json.loads((out/'results/before/manifest.json').read_text());after=json.loads((out/'results/after/manifest.json').read_text());deltas={k:after[k]['rows']-before[k]['rows']for k in before};assert deltas['orders']==487 and deltas['new_order']==487 and deltas['order_line']==4746 and deltas['history']==406,deltas
 assert sum(r['result'].get('rolled_back',False)for r in rows)==7
 (out/'correctness.json').write_text(json.dumps({'status':'PASS','requests':900,'rollbacks':7,'row_deltas':deltas,'before':before,'after':after,'cross_native_state_comparison':'pending native owner export'},indent=2))
print(out)
