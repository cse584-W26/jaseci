#!/usr/bin/env python3
import json,pathlib,statistics,math,datetime
R=pathlib.Path(__file__).resolve().parent;P=R.parent;read=lambda p:json.loads(p.read_text())
x=read(R/'verified-six-arms.json');oracle=read(P/'alignment/small-diagnostic/input.json')['expected'];root=P/'alignment/idiomatic';gate=[json.loads(l)for l in (root/'gate-20261020/rows.jsonl').read_text().splitlines()];assert len(gate)==21 and all(r['result']==r['expected']and r['questions']==4 for r in gate)
frozen=read(P/'alignment/graph-fixture/inputs.json')+[read(P/'alignment/small-diagnostic/input.json')]
assert len(frozen)==21 and all(row['result']==inp['expected'] for row,inp in zip(gate,frozen))
rows=x['rows'];checked=x['requests_checked']
for d in [0,2,10]:
 p=root/f'delay-results/delay-{d}ms/timing/rows.jsonl';raw=[json.loads(l)for l in p.read_text().splitlines()];m=[r for r in raw if not r['warmup']];assert len(raw)==40 and len(m)==30 and all(r['result']==oracle and r['oracle_ok']and r['questions']==4 and r['jdbc_calls']==4 for r in raw)
 ms=[r['ms']for r in m];rows.append(dict(system='Java set-oriented SQL',delay_ms=d,median_ms=statistics.median(ms),p95_ms=sorted(ms)[math.ceil(len(ms)*.95)-1],commands=4,n=30));checked+=len(raw)
order=['Jac original','Jac SQL pushdown','Java full','WeBridge full','Java pruned','WeBridge pruned','Java set-oriented SQL'];rows.sort(key=lambda r:(order.index(r['system']),r['delay_ms']))
result=dict(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),all_checks_passed=True,timing_requests_checked=checked,additional_correctness_inputs=21,rows=rows)
(R/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
table='| Implementation | 0 ms | +2 ms | +10 ms | Warm SQL commands |\n|---|---:|---:|---:|---:|\n'
for n in order:
 rr=[r for r in rows if r['system']==n];table+='| '+n+' | '+' | '.join(f"{r['median_ms']:.2f}"for r in rr)+f" | {rr[0]['commands']} |\n"
(R/'table.md').write_text(table);print(table)
