#!/usr/bin/env python3
"""Select only measured successful immutable cases, preserving all failed attempts."""
import json,pathlib
H=pathlib.Path(__file__).resolve().parent;attempts=[]
for p in sorted(H.glob('pipeline-*.json')):
 try:rows=json.loads(p.read_text())
 except json.JSONDecodeError:continue
 for row in rows:attempts.append(dict(row,manifest=str(p)))
out=[]
for q in ['is1','is2','is3','ic1','ic2','ic13']:
 for v in ['full','pruned']:
  rows=[r for r in attempts if r['query']==q and r['variant']==v];success=[r for r in rows if r.get('status')=='success'];selected=success[-1]if success else rows[-1]if rows else None;failures=[]
  for r in rows:
   for s in r.get('stages',[]):
    if s['returncode']:
     p=pathlib.Path(s['path'])if s.get('path')else None;failures.append({'stage':s['stage'],'case':r.get('case'),'manifest':r['manifest'],'run_path':str(p)if p else None,'stderr_path':str(p/'stderr.log')if p else None,'process_receipt':str(p/'process-result.json')if p and(p/'process-result.json').exists()else None})
  entry={'query':q,'variant':v,'status':'success'if success else selected.get('status','in_progress')if selected else'pending','selected_case':selected.get('case')if selected else None,'selected_manifest':selected['manifest']if selected else None,'stages':selected.get('stages',[])if selected else[],'failed_stage':selected.get('failed_stage')if selected else None,'failures':failures,'reused_original_capture':selected.get('reused_original_capture')if selected else None}
  if selected and selected.get('case'):
   meta=json.loads((pathlib.Path(selected['case'])/'metadata.json').read_text());entry['metadata']=meta;entry['frozen_snapshot']=meta['snapshot'];entry['formal_synthesis_exit']=selected.get('formal_synthesis_exit');entry['emitted_artifact_status']=selected.get('artifact_status')
   if q=='ic1'and v=='pruned'and(H/'quiet-ic1-control/owned-watchdog-summary.json').exists():
    proof=json.loads((H/'quiet-ic1-control/owned-watchdog-summary.json').read_text())
    if proof.get('timed_out'):entry['status']='censored';entry['censor_receipt']=str(H/'quiet-ic1-control/owned-watchdog-summary.json');entry['protocol']='Quiet first SP request >15 seconds; warmup not completed';entry['completed_instrumented_call']=str(pathlib.Path(selected['case'])/'optimized-20261020T220324437932Z/report-0.json')
  out.append(entry)
(H/'case-status.json').write_text(json.dumps(out,indent=2));print(json.dumps([{k:r[k]for k in ['query','variant','status','failed_stage','selected_case']}for r in out],indent=2))
