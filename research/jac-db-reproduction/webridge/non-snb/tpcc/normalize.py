#!/usr/bin/env python3
"""Stable126-row Java interface for the combined comparison report."""
import hashlib,json,pathlib
H=pathlib.Path(__file__).resolve().parent;source=json.loads((H/'summary.json').read_text());out=[]
for row in source:
 if row['program']=='jac':continue
 suffix='conventional'if row['program']=='conventional'else row['variant'];arm=('webridge_'if row['phase']=='sp'else'java_')+suffix
 original=row['status'];status='accepted'if original=='measured'else'pending'if original=='pending'else'failed_with_stage_evidence';artifact=row.get('rows_path')or row.get('pipeline')or row.get('failure',{}).get('raw_path')if isinstance(row.get('failure'),dict)else row.get('rows_path')or row.get('pipeline')
 record={'family':'tpcc','workload':row['workload'],'arm':arm,'delay_ms':row['delay_ms'],'status':status,'median_ms':row.get('median_ms'),'timer':'Java_method_call_wall_ms','measurement_boundary':'Whole source transaction method, including UUID allocation; connection setup and correctness exports are outside request timer','sample_n':row.get('n',0),'warmup_n':row.get('warmup_count',0),'artifact':artifact,'source_status':original,'case':row.get('case'),'method':row.get('method'),'failure':row.get('failure'),'source_row':row}
 if row.get('rows_path'):
  path=pathlib.Path(row['rows_path']);record['requests_artifact']=str(path);record['requests_artifact_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
 if row.get('timeout_paths'):record['timeout_artifacts']=row['timeout_paths']
 if record['case']:
  meta=pathlib.Path(record['case'])/'metadata.json';record['metadata_artifact']=str(meta);record['metadata_sha256']=hashlib.sha256(meta.read_bytes()).hexdigest();m=json.loads(meta.read_text());record['session_configuration']=m['manifest'].get('session_configuration');record['compatibility_classes']=m['manifest'].get('compatibility_classes')
 out.append(record)
assert len(out)==126,len(out);assert len({(r['workload'],r['arm'],r['delay_ms'])for r in out})==126
(H/'normalized-latency.json').write_text(json.dumps(out,indent=2));print(json.dumps({'rows':len(out),'statuses':{s:sum(r['status']==s for r in out)for s in sorted({r['status']for r in out})}}))
