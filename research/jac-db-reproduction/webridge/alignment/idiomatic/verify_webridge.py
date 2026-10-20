#!/usr/bin/env python3
import pathlib,json,statistics,hashlib
h=pathlib.Path(__file__).resolve().parent;out={};load=lambda p:json.loads(p.read_text())
gate=[json.loads(x) for x in (h/'webridge-gate20-final/requests/rows.jsonl').read_text().splitlines()];assert len(gate)==20 and all(x['oracle_ok'] and x['sp_enabled_at_end'] and x['questions']==4 and x['status_delta']['Com_call_procedure']==1 for x in gate)
out['original_parameter_gate']={'passed':20,'calls_per_request':1};out['cells']={}
for d in [0,2,10]:
 p=h/'webridge-delay-results'/f'delay-{d}ms';rr=[json.loads(x) for x in (p/'idiomatic/requests/rows.jsonl').read_text().splitlines()];assert len(rr)==80 and all(x['oracle_ok'] and x['questions']==4 for x in rr)
 assert load(p/'proxy-process.json')['stopped'];assert load(p/'idiomatic/final-group-cleanup.json')['verified_empty']
 cell={}
 for arm in ['baseline','sp']:
  a=[x for x in rr if x['phase']==arm];assert len(a)==40 and sum(x['warmup'] for x in a)==10
  assert all(x['status_delta']['Com_call_procedure']==(1 if arm=='sp' else 0) and (arm!='sp' or x['sp_enabled_at_end']) for x in a)
  r=[x for x in a if not x['warmup']];cell[arm]={'median_ms':statistics.median(x['ms'] for x in r),'samples':30,'questions':4,'calls':1 if arm=='sp' else 0}
 cell['calibration_before_ms']=statistics.median(load(p/'roundtrip.json'));cell['calibration_after_ms']=statistics.median(load(p/'roundtrip-after.json'));out['cells'][str(d)]=cell
reverse={}
for d in [0,2,10]:
 p=h/'webridge-delay-reverse-results'/f'delay-{d}ms';r=[json.loads(x) for x in (p/'idiomatic/requests/rows.jsonl').read_text().splitlines()];assert len(r)==80 and all(x['oracle_ok'] and x['questions']==4 and x['status_delta']['Com_call_procedure']==(1 if x['phase']=='sp' else 0) and (x['phase']!='sp' or x['sp_enabled_at_end']) for x in r);assert load(p/'proxy-process.json')['stopped'] and load(p/'idiomatic/final-group-cleanup.json')['verified_empty'];reverse[str(d)]={a:statistics.median(x['ms'] for x in r if x['phase']==a and not x['warmup']) for a in ['baseline','sp']}
out['reverse_order_medians_ms']=reverse
out['source_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in h.glob('*.java')};(h/'webridge-independent-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
