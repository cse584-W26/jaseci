#!/usr/bin/env python3
"""Machine-readable readiness, preserving each genuine compiler stage outcome."""
import hashlib,json,pathlib
H=pathlib.Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
workloads=list(json.loads((H/'representatives.json').read_text()));records=[];final_sources=json.loads((H/'build.json').read_text())['sources']
for manifest in sorted(H.glob('pipeline-*/summary.json')):
 for row in json.loads(manifest.read_text()):
  if not row.get('case'):continue
  case=pathlib.Path(row['case']);meta=json.loads((case/'metadata.json').read_text());expected=sha(H.parent/'native/tpcc-fixture/export.json')if meta.get('program')=='graph'else sha(H/'relational-fixture-jac-seed/manifest.json')if(H/'relational-fixture-jac-seed/manifest.json').exists()else None
  if meta['manifest'].get('fixture_manifest_sha256')!=expected:continue
  records.append((manifest,row,meta))
out=[]
for program,variant in [('conventional','full'),('graph','full'),('graph','pruned')]:
 for workload in workloads:
  candidates=[r for r in records if r[1]['workload']==workload and r[2].get('program')==program and r[2].get('variant')==variant]
  current=[r for r in candidates if r[2]['manifest'].get('source')==final_sources];selected=current[-1]if current else None;entry={'family':'tpcc','workload':workload,'program':program,'variant':variant,'system':'conventional relational Java'if program=='conventional'else'graph Java '+variant,'status':'pending','baseline_ready':False,'sp_ready':False}
  entry['attempt_history']=[{'case':r[1]['case'],'status':r[1]['status'],'pipeline':str(r[0]),'failure':r[1].get('error')or r[1].get('failed_stage'),'matches_final_sources':r[2]['manifest'].get('source')==final_sources}for r in candidates]
  if selected:
   manifest,row,meta=selected;entry.update(status=row['status'],case=row['case'],pipeline=str(manifest),stages=row['stages'],metadata_sha256=sha(pathlib.Path(row['case'])/'metadata.json'),source_manifest=meta['manifest'],baseline_ready='baseline'in row.get('results',{}),optimized_activation=row.get('optimized_activation'),failure=row.get('error')or row.get('failed_stage'))
   entry['sp_ready']=row['status']=='success';entry['sp_activation_status']='active'if row.get('optimized_activation',{}).get('sp_enabled_end')and row.get('optimized_activation',{}).get('call_procedure',0)>0 else'fallback observed'if entry['sp_ready']else'not gated'
  out.append(entry)
(H/'case-status.json').write_text(json.dumps(out,indent=2));print(json.dumps({'cases':len(out),'baseline_ready':sum(r['baseline_ready']for r in out),'sp_ready':sum(r['sp_ready']for r in out)},indent=2))
