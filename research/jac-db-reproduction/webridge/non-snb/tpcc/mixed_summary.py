#!/usr/bin/env python3
"""Inventory original-plan compiled/source execution, including rejected state gates."""
import pathlib,json,hashlib,collections
H=pathlib.Path(__file__).resolve().parent
rows=[]
for d in sorted(H.glob('mixed-*')):
 if not d.is_dir():continue
 manifest=d/'manifest.json'
 if not manifest.exists():continue
 m=json.loads(manifest.read_text());r=d/'run/requests.jsonl';requests=[json.loads(l)for l in r.read_text().splitlines()]if r.exists()else[]
 correctness=d/'correctness.json';failure=d/'correctness-failure.json'
 item={'attempt':str(d),'program':m['program'],'variant':m['variant'],'original_plan_sha256':m['plan_sha256'],'routing':'Immutable fixture credit/name-median shape dispatch outside request timer; within-API guards belong to actual SDK','requests_completed':len(requests),'accepted_compiled_cases':m['accepted_compiled_cases'],'requests_with_call':sum(x['call_procedure']>0 for x in requests),'total_calls':sum(x['call_procedure']for x in requests),'completed_active_requests':sum(x['sp_enabled_end']and x['call_procedure']>0 for x in requests),'execution_counts':dict(collections.Counter(x['execution']for x in requests)),'raw_requests':str(r)if r.exists()else None,'requests_sha256':hashlib.sha256(r.read_bytes()).hexdigest()if r.exists()else None}
 if correctness.exists():item.update(status='accepted',correctness_receipt=str(correctness))
 elif failure.exists():item.update(status='rejected_state_gate',correctness_receipt=str(failure))
 elif (d/'harness-failure.json').exists():item.update(status='failed_before_database_action',failure_receipt=str(d/'harness-failure.json'))
 elif (d/'run/owned-watchdog-summary.json').exists():item.update(status='bounded_request_failure',failure_receipt=str(d/'run/owned-watchdog-summary.json'))
 else:item['status']='pending'
 rows.append(item)
(H/'mixed-results.json').write_text(json.dumps(rows,indent=2));print(json.dumps([{k:r[k]for k in ['attempt','status','requests_completed','requests_with_call']}for r in rows],indent=2))
