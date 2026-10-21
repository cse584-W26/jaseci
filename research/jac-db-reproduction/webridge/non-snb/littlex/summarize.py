#!/usr/bin/env python3
"""Collect actual semantic gates, genuine lifecycle stages and measured timing cells."""
import pathlib,json
H=pathlib.Path(__file__).resolve().parent;cells=[]
for tier in ['t20','t50','t100','t200']:
 for stem,system in [('conventional','java-conventional'),('LittleXFull','java-full'),('LittleXPruned','java-pruned')]:
  gates=sorted((H/'gates'/tier).glob(stem+'-*/results/summary.json'))
  if not gates:continue
  f=gates[-1];d=json.loads(f.read_text());assert d['passed']==203;rows=f.with_name('rows.json');data=json.loads(rows.read_text())
  for op in ['feed','feed_page','create_tweet','follow','like']:
   rr=[x for x in data if x['input']['op']==op];assert rr and all(x['passed']for x in rr)
   cells.append(dict(record_kind='semantic-gate',family='littlex',workload='W1'if op=='feed'else'W3-operation'if op=='feed_page'else'W2',operation=op,tier=tier,system=system,delay_ms=None,status='correctness passed',measurement_method='seed-derived full/page identity gates; committed state deltas and idempotent-repeat checks',raw_rows_path=str(rows),warmup_count=0,measured_count=0,semantic_gate_requests=len(rr),result_oracle_receipt=str(f),state_oracle_receipt=str(rows),protocol_profile_path=None))
for p in sorted(H.glob('pipeline-*/summary.json')):
 for r in json.loads(p.read_text()):
  cells.append(dict(record_kind='genuine-pipeline',family='littlex',workload='W1'if r['operation']=='feed'else'W3-operation'if r['operation']=='feed_page'else'W2',operation=r['operation'],tier=r['tier'],system=r['implementation']+' + WeBridge',region=r['region'],delay_ms=None,status=r['status'],measurement_method='original recorder/native replay/synthesizer/installed generated procedures; fresh-state correctness',warmup_count=0,measured_count=0,pipeline_receipt=str(p),pipeline_stages=r['stages'],failure=r.get('error'),result_oracle_receipt=str(p),state_oracle_receipt=str(p),case=r.get('case')))
for p in sorted(H.glob('compiler-retry-*/summary.json')):
 r=json.loads(p.read_text());meta=json.loads((pathlib.Path(r['case'])/'metadata.json').read_text());cells.append(dict(record_kind='genuine-compiler-retry',family='littlex',system=meta['implementation']+' + WeBridge',case=r['case'],status=r['status'],frontend='explicit compatibility overlay',overlay=r['overlay'],pipeline_receipt=str(p),pipeline_stages=r['stages'],activation=r.get('activation'),actual_questions=r.get('actual_questions'),failure=r.get('error'),result_state_oracle=r.get('correctness')))
for p in sorted(H.glob('emitted-recovery-*/summary.json')):
 for r in json.loads(p.read_text()):
  cells.append(dict(record_kind='genuine-emitted-artifact-recovery',family='littlex',system=r['implementation']+' + WeBridge',case=r['case'],status=r['status'],pipeline_receipt=str(p),pipeline_stages=r['stages'],activation=r.get('activation'),actual_session_status_delta=r.get('session_status_delta'),result_state_oracle=r.get('result_state_oracle'),failure=r.get('error')))
for p in sorted((H/'timing').glob('*/summary.json'))if(H/'timing').exists()else[]:
 scope=json.loads((p.parent/'scope.json').read_text())if(p.parent/'scope.json').exists()else{}
 for r in json.loads(p.read_text()):
  x=dict(r);x.update(record_kind='superseded-timing'if scope.get('accepted_for_primary_comparison')is False else'timing',accepted_for_primary_comparison=scope.get('accepted_for_primary_comparison',True),attempt_scope=scope,measurement_method=r['method'],measured_count=r.get('n',0),raw_rows_path=r.get('rows_path'),result_oracle_receipt=r.get('correctness'),state_oracle_receipt=r.get('final_state'),protocol_profile_path=r.get('protocol_profile_path'),timing_summary_path=str(p));cells.append(x)
primary=H/'normalized-rtt-results.json'
if primary.exists():
 for r in json.loads(primary.read_text())['cells']:
  x=dict(r);x.update(record_kind='primary-sql-rtt',measurement_method='median of per-request summed complete outer SQL command round-trip durations',normalized_source=str(primary));cells.append(x)
(H/'summary.json').write_text(json.dumps(cells,indent=2)+'\n');print('Actual evidence records',len(cells),'primary RTT cells',sum(x.get('record_kind')=='primary-sql-rtt'for x in cells),'accepted primary RTT cells',sum(x.get('record_kind')=='primary-sql-rtt'and x.get('status')=='accepted'for x in cells))
