#!/usr/bin/env python3
"""Bounded original record/native/synthesis/install/CALL attempts, without handwritten SPs."""
import argparse,datetime,hashlib,json,pathlib,subprocess,sys
H=pathlib.Path(__file__).resolve().parent;E=H.parent;B=E.parent;schema=B/'expansion/fixture/compiler-schema.sql'
p=argparse.ArgumentParser();p.add_argument('--queries',nargs='+',default=['is1','is3','ic1','ic13','is2','ic2']);p.add_argument('--variants',nargs='+',default=['full','pruned']);p.add_argument('--attempt',default='original');p.add_argument('--reuse-graph',type=pathlib.Path);p.add_argument('--stack',default='20m');a=p.parse_args();summary=[];manifest=H/('pipeline-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
for query in a.queries:
 for variant in a.variants:
  record={'query':query,'variant':variant,'attempt':a.attempt,'stages':[]};summary.append(record)
  try:
   base=[sys.executable,str(H/'control.py'),'--query',query,'--variant',variant,'--inputs',str(H/'inputs'/f'{query}.json'),'--schema',str(schema),'--database','jac_snb_six_20261020','--attempt',a.attempt,'--stack',a.stack]
   case=None;graph=a.reuse_graph.resolve()if a.reuse_graph else None
   if graph:
    prior=json.loads((graph.parent.parent/'metadata.json').read_text())['manifest']
    assert prior['source_sha256']=={f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in H.glob('*.java')},'Reused native capture source changed'
    assert prior['class_sha256']=={str(f.relative_to(H/'classes')):hashlib.sha256(f.read_bytes()).hexdigest()for f in (H/'classes').rglob('*.class')},'Reused native capture classes changed'
    assert prior['inputs_sha256']==hashlib.sha256((H/'inputs'/f'{query}.json').read_bytes()).hexdigest(),'Reused capture input changed'
    assert prior['schema_sha256']==hashlib.sha256(schema.read_bytes()).hexdigest(),'Reused capture compiler schema changed'
    record['reused_original_capture']={'graph':str(graph),'sha256':hashlib.sha256(graph.read_bytes()).hexdigest(),'source_case':str(graph.parent.parent)}
   for action in (['synth','install','optimized']if graph else['record','replay','synth','install','optimized']):
    if action=='install':
     meta=json.loads((case/'metadata.json').read_text());folder=case/'generated/sql'/meta['api'];files=[folder/'graph-SP-function.sql',*sorted(folder.glob('graph-SP-*_sp_*.sql'))];assert all(f.exists()for f in files)and len(files)>1,files
     cmd=['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot','jac_snb_six_20261020'];sql=b'\n'.join(f.read_bytes()for f in files);out=case/'install';out.mkdir();r=subprocess.run(cmd,input=sql,capture_output=True);(out/'stdout.log').write_bytes(r.stdout);(out/'stderr.log').write_bytes(r.stderr);detail={'stage':action,'returncode':r.returncode,'command':cmd,'source_sql':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in files},'path':str(out)}
    else:
     cmd=base[:2]+[action]+base[2:]+(['--graph',str(graph)]if action=='synth'else[])+(['--repeats','3']if action=='optimized'else[]);r=subprocess.run(cmd,capture_output=True,text=True);paths=[pathlib.Path(v)for v in r.stdout.splitlines()if v.startswith(str(E/'webridge-cases'))];out=paths[-1]if paths else None;detail={'stage':action,'returncode':r.returncode,'command':cmd,'stdout':r.stdout,'stderr':r.stderr,'path':str(out)if out else None}
     if out:case=out.parent;record['case']=str(case)
     if action=='replay'and out:graph=out/'graph.json'
    record['stages'].append(detail);manifest.write_text(json.dumps(summary,indent=2));print(query,variant,action,r.returncode,flush=True)
    if r.returncode:record['status']='failed';record['failed_stage']=action;break
   else:record['status']='success'
  except Exception as exc:record['status']='failed';record['error']=repr(exc)
  manifest.write_text(json.dumps(summary,indent=2))
print(manifest)
