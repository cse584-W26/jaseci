"""Offline exact category-delta verifier for all cumulative removal steps."""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);a=ap.parse_args();out=a.directory.resolve();summary=json.loads((out/'summary.json').read_text());base={(r['round'],r['idx']):r for r in map(json.loads,(HERE/'java-all20-context-aligned.jsonl').read_text().splitlines())};oracle=json.loads((HERE/'graph-fixture/inputs.json').read_text());result={'source_sha256':summary['source_sha256'],'configs':[]}
 for c in summary['configs']:
  rows=[json.loads(x) for x in (out/c['name']/'rows.jsonl').read_text().splitlines()];tests=[];flags=c['flags']
  for r in rows:
   expected=dict(base[r['round'],r['idx']]['categories'])
   if 'auth' in flags:expected.pop('identity',None)
   if 'acl' in flags:
    expected['anchor-load']-=1
    if not expected['anchor-load']:expected.pop('anchor-load')
   if 'schema' in flags:
    for k in ['server-version','schema-fingerprint','type-registry']:expected.pop(k,None)
   if 'hydration' in flags:expected.pop('anchor-load',None)
   tests.append({'round':r['round'],'idx':r['idx'],'exact_category_delta':expected==r['categories'],'expected_statements':sum(expected.values()),'jdbc_statements':r['jdbc_calls'],'server_statements':r['server_questions'],'independent_count':sum(expected.values())==r['jdbc_calls']==r['server_questions'],'result_oracle':r['parity'] and r['result']==oracle[r['idx']]['expected']})
  passed=len(rows)==21 and c['gate_pass'] and all(t['exact_category_delta'] and t['independent_count'] and t['result_oracle'] for t in tests);result['configs'].append({'name':c['name'],'pass':passed,'cold20_statements':c['cold20_statements'],'warm_repeat0_statements':c['warm_repeat0_statements'],'rows':tests})
 result['all_pass']=len(result['configs'])==5 and all(c['pass'] for c in result['configs']);result['source_matches_current']=summary['source_sha256']==hashlib.sha256((HERE/'PrunedIc5.java').read_bytes()).hexdigest();result['all_pass']=result['all_pass'] and result['source_matches_current'];(out/'exact-removal-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='configs'},indent=2));print([(c['name'],c['pass'],c['cold20_statements']) for c in result['configs']])
 if not result['all_pass']:raise SystemExit(1)
if __name__=='__main__':main()
