#!/usr/bin/env python3
"""Require actual SP execution, not only fallback-preserved output parity."""
import argparse,json,pathlib,hashlib
p=argparse.ArgumentParser();p.add_argument('attempt',type=pathlib.Path);a=p.parse_args();d=a.attempt;reports=[json.loads(f.read_text()) for f in sorted(d.glob('report-*.json'))];assert reports
stderr=(d/'stderr.log').read_text();assert 'fallback to normal execution' not in stderr;assert 'Error executing stored procedure' not in stderr
for r in reports:
 assert r['oracle_ok'] and r['body']['sp_enabled_at_start'] and r['body']['sp_enabled_at_end'],r
 assert r['session_status_delta']['Com_call_procedure']==1,r
 # Cold full Jac request's four setup SELECTs plus START/SET and COMMIT,
 # with21 body SELECTs replaced by a single original generated CALL.
 if r['scope']=='cold' and r['idx']==0:
  r['expected_business_plus_preserved_setup_commands']=8
  r['additional_observed_session_commands']=r['server_questions_excluding_final_observer']-8
  assert r['server_questions_excluding_final_observer']<28,r
out={'actual_sp_execution_pass':True,'reports':reports,'stderr_sha256':hashlib.sha256((d/'stderr.log').read_bytes()).hexdigest()};(d/'sp-verification.json').write_text(json.dumps(out,indent=2));print(json.dumps({'actual_sp_execution_pass':True,'requests':len(reports)}))
