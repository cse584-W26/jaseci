"""Offline alignment verifier. --deep additionally reads fixture and raw-log payloads."""
import argparse,gzip,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--deep',action='store_true');a=ap.parse_args();checks={}
 gate=json.loads((HERE/'alignment-gate.json').read_text());checks['source_hash']=digest(HERE/'AlignedIc5.java')==gate['source_sha256']
 rows=[json.loads(x) for x in (HERE/'java-all20-context-aligned.jsonl').read_text().splitlines()];inputs=json.loads((HERE/'graph-fixture/inputs.json').read_text());historical={r['idx']:r['historical'] for r in json.loads((HERE/'baseline-capture/backend-filtered-counts.json').read_text()) if r['round']==1}
 checks['twenty_inputs']=sorted(r['idx'] for r in rows if r['round']==0)==list(range(20))
 checks['twenty_result_oracles']=all(r['parity'] and r['result']==inputs[r['idx']]['expected'] for r in rows)
 checks['independent_mysql_counts']=all(r['jdbc_calls']==r['server_questions'] for r in rows)
 checks['observed_jac_counts']=all(r['equal_counts'] for r in gate['rows'])
 checks['historical_warm_counts']=all(r['jdbc_calls']==historical[r['idx']]+(4 if r['round']==0 and r['idx']==0 else 0) for r in rows)
 categories=json.loads((HERE/'query-category-ledger.json').read_text());checks['per_category_counts']=all(r['equal'] and r['jac']==r['java'] and sum(r['java'].values())==r['server_questions'] for r in categories['rows'])
 base=json.loads((HERE/'baseline-capture/rows.json').read_text());checks['jac_two_rounds_results']=len(base)==40 and all(r['parity'] and not r['error'] for r in base)
 trace=[json.loads(x) for x in (HERE/'identity-trace.jsonl').read_text().splitlines()];root_entries=[r for r in trace if r.get('event')=='enter' and r.get('hook')=='JacScaleUserManager.get_root_id'];checks['identity_trace_middleware_and_worker']=any('jwt_validation_middleware' in r.get('callers',[]) for r in root_entries) and len({r['thread'] for r in root_entries})>=2 and any(r.get('cache_before') for r in root_entries)
 checks['database_settings_restored']=json.loads((HERE/'baseline-capture/restored.json').read_text())['baseline_service_restarted']
 ledger=json.loads((HERE/'removal-ledger.json').read_text());checks['pruned_derives_from_full']=ledger['base_sha256']==digest(HERE/'AlignedIc5.java') and ledger['derivative_sha256']==digest(HERE/'PrunedIc5.java')
 if 'all_removals_gate' in ledger:
  phase2_path=HERE/ledger['all_removals_gate']['path'];phase2=json.loads(phase2_path.read_text());phase2_rows=[json.loads(x) for x in (phase2_path.parent/'rows.jsonl').read_text().splitlines()]
  full_by_key={(r['round'],r['idx']):r for r in rows}
  checks['phase2_all20_results']=len(phase2_rows)==21 and all(r['parity'] and r['result']==inputs[r['idx']]['expected'] for r in phase2_rows)
  checks['phase2_independent_counts']=all(r['jdbc_calls']==r['server_questions'] for r in phase2_rows)
  checks['phase2_original_domain_hops']=all({k:v for k,v in r['categories'].items() if k.startswith('hop:')}=={k:v for k,v in full_by_key[r['round'],r['idx']]['categories'].items() if k.startswith('hop:')} for r in phase2_rows)
  checks['phase2_only_hops_and_txn']=all(r['jdbc_calls']==sum(v for k,v in r['categories'].items() if k.startswith('hop:'))+3 and set(r['categories'])==set(k for k in r['categories'] if k.startswith('hop:'))|{'begin','transaction-setting','commit'} for r in phase2_rows)
 if a.deep:
  manifest=json.loads((HERE/'graph-fixture/manifest.json').read_text());checks['fixture_file_hashes']=all(digest(HERE/'graph-fixture'/(k+'.tsv'))==v['sha256'] for k,v in manifest['files'].items())
  checks['raw_log_hashes']=all(hashlib.sha256(gzip.open(HERE/'baseline-capture'/r['log'],'rb').read()).hexdigest()==r['raw_sha256'] for r in base)
 result={'all_pass':all(checks.values()),'checks':checks,'deep':a.deep,'inputs':20,'requests':len(rows),'full_source_sha256':digest(HERE/'AlignedIc5.java')};(HERE/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
 if not result['all_pass']:raise SystemExit(1)
if __name__=='__main__':main()
