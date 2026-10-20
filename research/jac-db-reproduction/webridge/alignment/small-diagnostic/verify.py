import json
from pathlib import Path
p=Path(__file__).resolve().parent; r=p.parents[1]/'integration/cases'
jac=json.loads((p/'jac-capture/rows.json').read_text());full=[json.loads(x) for x in next((r/'small-full-region-20261020').glob('baseline-*/stdout.log')).read_text().splitlines() if x.startswith('{')];pruned=[json.loads(x) for x in next((r/'small-pruned-region-20261020').glob('baseline-*/stdout.log')).read_text().splitlines() if x.startswith('{')]
assert len(jac)==len(full)==len(pruned)==3
for j,f,q in zip(jac,full,pruned):
 assert j['parity'] and f['oracle_ok'] and q['oracle_ok']
 assert j['statements']==f['source_jdbc_calls']==f['server_questions_excluding_final_observer']
 assert q['source_jdbc_calls']==q['server_questions_excluding_final_observer']
 assert {k:v for k,v in f['source_categories'].items() if k.startswith('hop:')}=={k:v for k,v in q['source_categories'].items() if k.startswith('hop:')}
 assert f['result']==q['result']
d={'all_pass':True,'jac_and_full_counts':[x['statements'] for x in jac],'pruned_counts':[x['source_jdbc_calls'] for x in pruned],'full_categories':full[0]['source_categories'],'pruned_categories':pruned[0]['source_categories'],'result':full[0]['result'],'scope':'Independent smaller diagnostic, separate from original20 inputs'};(p/'verification.json').write_text(json.dumps(d,indent=2));print(json.dumps(d))
