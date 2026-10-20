#!/usr/bin/env python3
import pathlib,json,hashlib
H=pathlib.Path(__file__).resolve().parent;I=H.parents[1]/'integration';result=[]
for q in ['is1','is2','is3','ic1','ic2','ic13']:
 c=I/'cases'/json.loads((H/'selected-cases.json').read_text())[q];x={'query':q,'variant':'set','case_path':str(c),'selected_idx':0,'stages':[],'status':'not-started'}
 for stage in ['record','replay','synth','install','optimized']:
  attempts=[]
  for d in sorted(c.glob(stage+'-*')):
   if not d.is_dir():continue
   p=d/'process-result.json';r=json.loads(p.read_text())if p.exists()else{};report=d/'report.json';rr=json.loads(report.read_text())if report.exists()else{}
   attempts.append({'path':str(d),'returncode':r.get('returncode'),'stop_reason':r.get('stop_reason'),'oracle_ok':rr.get('oracle_ok'),'questions':rr.get('questions'),'sp_enabled':rr.get('sp_enabled_at_end')})
  if attempts:x['stages'].append({'stage':stage,'attempts':attempts})
 reports=sorted(c.glob('optimized-*/report.json'))
 if reports and json.loads(reports[-1].read_text()).get('oracle_ok')and json.loads(reports[-1].read_text()).get('sp_enabled_at_end'):x['status']='selected-input-genuine-pipeline-passed'
 elif x['stages']:x['status']='in-progress-or-failed-see-stage-receipts'
 x['budget_probes']=[str(p) for p in sorted(H.glob('quiet-'+q+'-control-*/owned-watchdog-summary.json'))]
 if x['budget_probes'] and x['status']!='selected-input-genuine-pipeline-passed':x['status']='compiled-installed; bounded runtime probes recorded separately'
 if(c/'source/SnbSetSql.java').exists():x['source_sha256']=hashlib.sha256((c/'source/SnbSetSql.java').read_bytes()).hexdigest()
 result.append(x)
(H/'case-status.json').write_text(json.dumps(result,indent=2)+'\n')
