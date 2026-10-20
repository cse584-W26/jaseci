#!/usr/bin/env python3
"""Recompute comparison from raw request records; verify result/count gates."""
import json,pathlib,statistics,math
R=pathlib.Path(__file__).resolve().parent;P=R.parent;expected=json.loads((P/'alignment/small-diagnostic/input.json').read_text())['expected'];jexpected={'forums':[dict(zip(['forumId','title','postCount'],r))for r in expected]}
def read(p):return json.loads(p.read_text())
def percentile(x,p):return sorted(x)[math.ceil(len(x)*p)-1]
results=[];checked=0
for d in [0,2,10]:
 for v in ['baseline','final']:
  base=P/f'jac-comparison/latency/results/delay-{d}ms/timing'/v;rows=read(base/'rows.json');rr=[x for x in rows if not x['warmup']];assert len(rows)==40 and len(rr)==30
  assert all(x['status']==200 and x['result']==jexpected and abs(x['server_ms']-float(x['headers']['x-server-total-ms'])-float(x['headers']['x-server-commit-ms']))<1e-8 for x in rows)
  assert read(base/'restored.json')['service_stopped'] and read(base/'restored.json')['logging_restored'];checked+=len(rows)
  ms=[x['server_ms']for x in rr];results.append(dict(system='Jac original'if v=='baseline'else'Jac SQL pushdown',delay_ms=d,median_ms=statistics.median(ms),p95_ms=percentile(ms,.95),commands=38 if v=='baseline' else 14,n=30))
 for v in ['full','pruned']:
  base=R/f'java-results/delay-{d}ms'/v;rows=[json.loads(x)for x in (base/'requests/rows.jsonl').read_text().splitlines()];assert len(rows)==80
  for phase in ['baseline','sp']:
   rr=[x for x in rows if x['phase']==phase and not x['warmup']];cmd=4 if phase=='sp'else(38 if v=='full' else 31);assert len(rr)==30
   assert all(x['result']==expected and x['oracle_ok'] and x['questions']==cmd and x['status_delta']['Com_call_procedure']==(1 if phase=='sp' else 0) and (phase!='sp' or x['sp_enabled_at_end'])for x in rows if x['phase']==phase and not x['warmup'])
   assert all(x['result']==expected for x in rows)
   name=('Java full'if phase=='baseline'else'WeBridge full')if v=='full'else('Java pruned'if phase=='baseline'else'WeBridge pruned');ms=[x['ms']for x in rr];results.append(dict(system=name,delay_ms=d,median_ms=statistics.median(ms),p95_ms=percentile(ms,.95),commands=cmd,n=30))
  checked+=len(rows);assert read(base/'final-group-cleanup.json')['verified_empty']
 assert read(R/f'java-results/delay-{d}ms/proxy-cleanup.json')['stopped']
# Idiomatic records are added after their independent semantic and timing gates finish.
(R/'verified-six-arms.json').write_text(json.dumps({'all_checks_passed':True,'requests_checked':checked,'rows':results},indent=2)+'\n');print(json.dumps({'requests_checked':checked,'rows':results},indent=2))
