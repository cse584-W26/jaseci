#!/usr/bin/env python3
"""Independent offline checks of conventional direct/generated-SP timing evidence."""
import json,pathlib,statistics,datetime
H=pathlib.Path(__file__).resolve().parent;P=H/'timing';cells=json.loads((P/'summary.json').read_text());errors=[];normal=[];censors=[]
for c in cells:
 if c['n']:
  rows=[json.loads(x)for x in pathlib.Path(c['rows_path']).read_text().splitlines()];rr=[r for r in rows if r['phase']==c['phase'] and not r['warmup']]
  assert len(rr)==30 and len([r for r in rows if r['phase']==c['phase'] and r['warmup']])==10
  assert all(r['oracle_ok']for r in rows)
  assert statistics.median(r['ms']for r in rr)==c['median_ms']
  assert sorted({r['questions']for r in rr})==c['actual_command_counts']
  assert sorted({r['status_delta']['Com_call_procedure']for r in rr})==c['actual_call_counts']
  normal.append(c)
 else:
  assert c['attempts']==3 and c['median_ms']is None and not c['warmup_completed']
  for p in map(pathlib.Path,c['timeout_paths']):
   d=json.loads((p/'owned-watchdog-summary.json').read_text());v=json.loads((p/'server-absence-verification.json').read_text())
   assert d['timed_out']and d['timeout_receipt']['request_marker']['watchdog_elapsed_s']>=15
   assert v['verified_absent']and v['connection_id']==d['timeout_receipt']['connection_id']
   censors.append({'path':str(p),'request_s':d['timeout_receipt']['request_marker']['watchdog_elapsed_s'],'kill_wall_ns':d['timeout_receipt']['wall_ns'],'absence_receipt_mtime_ns':(p/'server-absence-verification.json').stat().st_mtime_ns})
assert len(cells)==36 and len(normal)==33 and len(censors)==9
for delay in [0,2,10]:
 d=P/f'delay-{delay}ms';assert json.loads((d/'proxy-process.json').read_text())['stopped'];assert(d/'roundtrip-before.json').exists()and(d/'roundtrip-after.json').exists()
r={'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'cells':36,'normal_cells':33,'normal_measured_samples':990,'normal_warmup_samples':330,'censored_first_requests':9,'censor_evidence':censors,'scope':'Censored fresh-JVM first SP requests have no completed warmup; asynchronous server cleanup excluded from request limit. Absence receipt mtime provides a verification upper bound, not exact disappearance time.'}
(P/'independent-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='censor_evidence'},indent=2))
