#!/usr/bin/env python3
"""Normalize observed littleX cells to the common eight-arm coverage contract."""
import argparse,json,pathlib
H=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('summaries',nargs='+',type=pathlib.Path);p.add_argument('--out',required=True,type=pathlib.Path);p.add_argument('--require-complete',action='store_true');p.add_argument('--replacement-list',type=pathlib.Path,default=H/'replacement-summaries.json');a=p.parse_args();rows=[];seen=set()
def replacement_key(r):return(r['method'],r['workload'],r['operation'],r['tier'],r['system'],r['phase'],r['delay_ms'])
replacements=[pathlib.Path(x)for x in json.loads(a.replacement_list.read_text())]if a.replacement_list.exists()else[]
replacements=[path for path in replacements if any(r.get('replaces_potential_overlap_summary')and any(source.parent in pathlib.Path(r['replaces_potential_overlap_summary']).parents for source in a.summaries)for r in json.loads(path.read_text()))]
replacement_origins={replacement_key(r):str(path)for path in replacements for r in json.loads(path.read_text())}
a.summaries.extend(path for path in replacements if path not in a.summaries)
for summary in a.summaries:
 for r in json.loads(summary.read_text()):
  if replacement_key(r)in replacement_origins and replacement_origins[replacement_key(r)]!=str(summary):continue
  impl=r['system'].split(' + ')[0];stem={'LittleXSql':'conventional','LittleXFull':'full','LittleXPruned':'pruned'}[impl];arm=('webridge_'if r['phase']=='sp'else'java_')+stem;w3=r['workload']=='W3';workload='mixed'if w3 else r['operation'];row={'family':'littlex','workload':workload,'tweets_per_user':int(r['tier'][1:]),'arm':arm,'delay_ms':r['delay_ms'],'status':'accepted'if r['status']=='measured'else'failed_with_stage_evidence','median_ms':r.get('median_ms'),'artifact':r.get('rows_path',r.get('raw_path',str(summary))),'method':r['method'],'observed_status':r['status'],'summary_source':str(summary),'warmup_count':r['warmup_count'],'measured_count':r.get('n',0),'measured_count_requested':r['measured_count_requested'],'source_result_oracle':r.get('source_result_oracle'),'state_result_gate':r.get('independent_state_oracle',r.get('correctness')),'actual_call_requests':r.get('call_requests'),'actual_call_fraction':r.get('call_fraction'),'sdk_enabled_at_end_requests':r.get('sdk_enabled_at_end_requests'),'sdk_enabled_at_end_fraction':r.get('sdk_enabled_at_end_fraction'),'sdk_flag_scope':r.get('sdk_flag_scope'),'activation_by_operation':r.get('activation_by_operation'),'actual_questions_distribution':r.get('questions'),'actual_call_count_distribution':r.get('call_procedure')}
  row.update({k:r.get(k)for k in ['build_snapshot','webridge_bundle','frontend_selection','connection_compatibility']})
  if r.get('primary_rtt'):
   row.update(timer='compact SQL round-trip sum',metric=r['metric'],artifact=r['primary_rows_path'],primary_rtt=r['primary_rtt'],application_median_ms_secondary=r.get('application_median_ms_secondary'),instrumentation=r.get('instrumentation'))
  row['full_results_logical_monolith']=r.get('full_results_path');oracle=pathlib.Path(r['source_result_oracle'])if r.get('source_result_oracle')else None
  if oracle and oracle.exists():row['public_full_results_chunk_index']=json.loads(oracle.read_text()).get('public_chunk_index')
  logical=pathlib.Path(r['full_results_path'])if r.get('full_results_path')else None
  public_index=logical.with_name('full-results-public-chunks')/'index.json'if logical else None
  if public_index and public_index.exists():row['public_full_results_chunk_index']=str(public_index)
  if w3:row['write_percent']=int(r['operation'])
  if r.get('error'):row['error']=r['error']
  for field in ['failed_stage','pipeline_evidence','stage_manifest','replaces_potential_overlap_summary','cleanup_verification']: 
   if field in r:row[field]=r[field]
  key=(row['method'],row['workload'],row['tweets_per_user'],row.get('write_percent'),arm,row['delay_ms']);assert key not in seen,('Duplicate observed cell',key);seen.add(key);rows.append(row)
latency=[r for r in rows if r['method']=='latency'];references=[r for r in rows if r['method']=='reference']
if a.require_complete:assert len(latency)==360 and len(references)==120,(len(latency),len(references))
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps({'schema':1,'latency_cells':len(latency),'reference_cells':len(references),'required_latency_cells':360,'required_reference_cells':120,'cells':rows},indent=2)+'\n');print(a.out)
