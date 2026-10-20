#!/usr/bin/env python3
"""Verify derivative all20+repeat output against the independently proven full port."""
import argparse,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('stdout',type=pathlib.Path);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--reference',type=pathlib.Path);a=p.parse_args();R=pathlib.Path(__file__).resolve().parent;A=R.parent/'alignment';ref_path=a.reference or A/'alignment-gate.json';reference=json.loads(ref_path.read_text());inputs=json.loads((A/'graph-fixture/inputs.json').read_text());rows=[json.loads(x) for x in a.stdout.read_text().splitlines() if x.startswith('{')];assert len(rows)==21,len(rows);verified=[]
for actual,expected in zip(rows,reference['rows']):
 assert actual['idx']==expected['idx'],(actual['idx'],expected['idx'])
 count=expected['statements'] if 'statements' in expected else expected['java']
 assert actual['jdbc_calls']==actual['server_questions']==count,actual
 if 'jac_observed' in expected:assert count==expected['jac_observed']
 assert actual['categories']==expected['categories'],(actual['categories'],expected['categories'])
 assert actual['parity'] and actual['result']==inputs[actual['idx']]['expected'],actual
 verified.append(dict(idx=actual['idx'],round=actual['round'],calls=actual['jdbc_calls'],categories=actual['categories'],result_parity=True,counts_equal_to_reference=True))
report=dict(raw_stdout=str(a.stdout.resolve()),raw_sha256=hashlib.sha256(a.stdout.read_bytes()).hexdigest(),reference=str(ref_path.resolve()),all_passed=True,requests=21,cold20_total=sum(x['calls'] for x in verified[:20]),warm_repeat_calls=verified[-1]['calls'],rows=verified);assert report['cold20_total']==(reference['cold20_statements'] if 'cold20_statements' in reference else 278773) and report['warm_repeat_calls']==(reference['warm_repeat0_statements'] if 'warm_repeat0_statements' in reference else 24);a.out.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
