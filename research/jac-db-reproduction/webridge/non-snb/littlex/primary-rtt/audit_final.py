#!/usr/bin/env python3
"""Independently verify completed littleX RTT coverage, arithmetic and oracle receipts."""
import collections,hashlib,json,math,pathlib,statistics,time
H=pathlib.Path(__file__).resolve().parent.parent
source=H/'normalized-rtt-results.json';data=json.loads(source.read_text());cells=data['cells'];assert len(cells)==480
assert collections.Counter(r['method']for r in cells)=={'latency':360,'reference':120}
keys=[(r['method'],r['workload'],r['tweets_per_user'],r.get('write_percent'),r['arm'],r['delay_ms'])for r in cells];assert len(set(keys))==480
pairs=collections.defaultdict(list)
for r in cells:
 if r['method']=='latency':pairs[(r['workload'],r['tweets_per_user'],r.get('write_percent'),r['arm'])].append(r['delay_ms'])
assert len(pairs)==120 and all(sorted(v)==[0,2,10]for v in pairs.values())
checks=[];total=0;measured_total=0
for cell in cells:
 if cell['status']!='accepted':
  assert cell['median_ms']is None and cell['measured_count']==0 and cell.get('failed_stage')
  assert cell.get('pipeline_evidence');checks.append({'status':'actual compiler stage','arm':cell['arm'],'stage':cell['failed_stage']});continue
 oracle=json.loads(pathlib.Path(cell['source_result_oracle']).read_text());assert oracle['status']=='PASS'
 state=json.loads(pathlib.Path(cell['state_result_gate']).read_text());assert state['status']=='PASS'
 rtt=json.loads(pathlib.Path(cell['rtt_summary_artifact']).read_text());assert rtt['status']=='PASS'and pathlib.Path(cell['compact_trace_artifact']).exists()
 rows=[json.loads(line)for line in pathlib.Path(cell['requests_artifact']).read_text().splitlines()];measured=[r for r in rows if not r['warmup']]
 assert len(measured)==cell['measured_count']==cell['measured_count_requested']
 assert len(rows)==cell['warmup_count']+len(measured)
 values=[]
 for row in rows:
  assert row['command_count']==len(row['operations'])
  assert row['call_count']==sum(bool(o['is_call'])for o in row['operations'])
  assert math.isclose(row['summed_db_call_rtt_ms'],sum(o['rtt_ms']for o in row['operations']),rel_tol=1e-12,abs_tol=1e-9)
  if not row['warmup']:values.append(row['summed_db_call_rtt_ms'])
 assert statistics.median(values)==cell['median_ms']==rtt['median_ms']
 distribution={str(k):v for k,v in collections.Counter(r['command_count']for r in measured).items()}
 assert distribution==cell['sql_command_count_distribution']==cell['response_exchange_count_distribution']
 assert sum(r['call_count']>0 for r in measured)==cell['actual_call_requests']
 assert sum(bool(r['sdk_enabled_at_end'])for r in measured)==cell['sdk_enabled_at_end_requests']
 checks.append({'status':'PASS','artifact':cell['requests_artifact'],'requests':len(rows),'measured':len(measured)})
 total+=len(rows);measured_total+=len(measured)
groups=json.loads((H/'primary-rtt/complete-final/matrix/groups.json').read_text());assert len(groups)==48
for group in groups:
 assert group['returncode']==0
 root=pathlib.Path(group['summary']).parent/('delay-'+str(group['delay_ms'])+'ms')
 assert json.loads((root/'proxy-process.json').read_text())['stopped']
 assert json.loads((root/'instrumentation-restored.json').read_text())['exact_restoration']
 assert json.loads((root/'lease.json').read_text()).get('released_utc')
manifest=json.loads((H/'primary-rtt/complete-final/source-manifest.json').read_text())
for name in ['compact_proxy.py','extract.py','sweep.py','run_groups.py']:
 assert hashlib.sha256((H/'primary-rtt'/name).read_bytes()).hexdigest()==manifest[name],('Measurement source changed',name)
receipt={'status':'PASS','wall_ns':time.time_ns(),'normalized_source':str(source),'cells':480,'latency_cells':360,'reference_cells':120,'workload_arm_delay_triplets':120,'completed_and_cleaned_groups':len(groups),'status_counts':dict(collections.Counter(r['status']for r in cells)),'executed_requests_including_warmup':total,'measured_requests':measured_total,'checks':checks,'scope':'Exact coverage; sum and median from every primary request operation; same-request counts/CALL/SDK flags; independent response/state receipts; frozen measurement source hashes. Root independent verifier additionally checks raw compact protocol timestamps.'}
(H/'primary-rtt/final-audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k!='checks'}))
