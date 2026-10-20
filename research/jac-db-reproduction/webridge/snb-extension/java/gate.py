#!/usr/bin/env python3
"""Original20 oracle and independent wire-command gate for full/pruned Java."""
import argparse,datetime,hashlib,importlib.util,json,pathlib
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];I=B/'integration'
spec=importlib.util.spec_from_file_location('ctl',I/'control.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('--queries',nargs='+',default=['is1','is3','ic1','ic13','is2','ic2']);p.add_argument('--variants',nargs='+',default=['full','pruned']);a=p.parse_args();cp=':'.join([str(H/'classes'),m.CP]);out=H/('gates-'+m.now());summary=[]
for query in a.queries:
 for variant in a.variants:
  d=out/query/variant;inp=H/'inputs'/f'{query}.json';cmd=[str(m.SERVER/'bin/java'),'-Xmx2g','-Dsnb.warmup=true','-Dalignment.dir='+str(B/'alignment'),'-Dexperiment.mysql.url=jdbc:mysql://127.0.0.1:55337/jac_snb_six_20261020?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true']
  if variant=='pruned':cmd+=['-Dpruned.'+k+'=true' for k in ['auth','acl','schema','hydration']]
  cmd+=['-cp',cp,'SnbAccess',str(inp),'1'];m.command(cmd,d,300);rows=[json.loads(line)for line in(d/'stdout.log').read_text().splitlines()if line.startswith('{')];assert len(rows)==20,(query,variant,len(rows));assert all(r['parity'] and r['jdbc_calls']==r['server_questions'] for r in rows);summary.append({'query':query,'variant':variant,'requests':len(rows),'result_parity':True,'independent_counts_equal':True,'counts':[r['jdbc_calls']for r in rows],'categories_idx0':rows[0]['categories'],'source_sha256':hashlib.sha256((H/'SnbAccess.java').read_bytes()).hexdigest(),'path':str(d)})
  (out/'summary.json').write_text(json.dumps(summary,indent=2));print(query,variant,summary[-1]['counts'],flush=True)
print(out)
