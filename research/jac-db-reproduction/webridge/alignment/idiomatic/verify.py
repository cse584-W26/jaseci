#!/usr/bin/env python3
"""Independent offline raw result, SQL census and cleanup verification."""
import json,pathlib,statistics,hashlib
h=pathlib.Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
gate=[json.loads(x) for x in (h/'gate-20261020/rows.jsonl').read_text().splitlines()]
assert len(gate)==21 and all(x['result']==x['expected'] and x['oracle_ok'] and x['questions']==x['jdbc_calls']==4 for x in gate)
out={'gate_inputs':21,'gate_exact_results':True,'timing':{},'artifacts':{}}
for delay in [0,2,10]:
 p=h/'delay-results'/f'delay-{delay}ms';rows=[json.loads(x) for x in (p/'timing/rows.jsonl').read_text().splitlines()];assert len(rows)==40 and all(x['result']==x['expected'] and x['questions']==4 and x['status_delta']['Com_select']==1 and x['status_delta']['Com_commit']==1 and x['status_delta']['Com_call_procedure']==0 for x in rows)
 rr=[x for x in rows if not x['warmup']];assert len(rr)==30
 assert load(p/'proxy-process.json')['stopped']
 out['timing'][str(delay)]={'warm':10,'measured':30,'median_ms':statistics.median(x['ms'] for x in rr),'questions':4,'all_exact':True,'proxy_stopped':True}
for p in [h/'ic5.sql',h/'IdiomaticIc5.java',h/'explain-small.json',h/'explain-original-idx1.json']:
 out['artifacts'][str(p.relative_to(h))]=hashlib.sha256(p.read_bytes()).hexdigest()
(h/'independent-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
