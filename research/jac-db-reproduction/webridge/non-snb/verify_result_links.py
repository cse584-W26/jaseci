#!/usr/bin/env python3
"""Verify report evidence paths within an archived public study tree."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('root', type=Path)
a = p.parse_args()
root = a.root.resolve()


def resolve(value):
    text = str(value)
    if '/non-snb/' in text:
        text = text.split('/non-snb/', 1)[1]
    elif text.startswith('non-snb/'):
        text = text[len('non-snb/'):]
    path = root / text
    assert path.resolve().is_relative_to(root), ('Evidence escapes the public tree', value)
    if not path.exists() and path.suffix == '.jsonl':
        path = path.with_suffix('.jsonl.gz')
    assert path.exists(), ('Missing public evidence', value, str(path))
    return path


r = json.loads((root / 'results.json').read_text())
assert r['metric'] == 'rtt'
assert r['coverage']['terminal_cells'] == 648 and r['coverage']['pending_cells'] == 0
checked = set()
for row in r['latency']:
    checked.add(str(resolve(row['artifact']).relative_to(root)))
    for name in ['requests_artifact', 'compact_trace_artifact', 'compact_trace_catalog_artifact', 'compact_trace_receipt_artifact', 'compact_trace_completeness_artifact', 'rtt_summary_artifact', 'correctness', 'source_result_oracle', 'state_result_gate', 'public_full_results_chunk_index']:
        value = row.get(name)
        if isinstance(value, str):
            checked.add(str(resolve(value).relative_to(root)))
    for name, value in row.get('gates', {}).items():
        if isinstance(value, str) and (name.endswith('_artifact') or name.endswith('_verification')):
            checked.add(str(resolve(value).relative_to(root)))
for identifier, arms in r['cycles'].items():
    for arm, record in arms.items():
        values = [record['artifact']] if record.get('artifact') else [v['artifact'] for v in record['observations']]
        for value in values:
            checked.add(str(resolve(value).relative_to(root)))
        for observation in record['observations']:
            for name in ['artifact', 'requests_artifact', 'primary_rtt', 'result_gate', 'state_result_gate']:
                value = observation.get(name)
                if isinstance(value, str):
                    checked.add(str(resolve(value).relative_to(root)))
for row in r['latency']:
    assert row['arm'] in r['cycles'].get(row['case_id'], {}), ('Missing SQL/command evidence', row['case_id'], row['arm'])
references = json.loads((root / 'rtt-reference-results.json').read_text())
assert references['metric'] == 'rtt'
assert references['tpcc_reference_arms'] == 8 and references['littlex_reference_arms'] == 160
for row in references['rows'] + references.get('additional_controls', []):
    evidence = [row.get(name) for name in ['artifact', 'requests_artifact', 'compact_trace_artifact', 'compact_trace_catalog_artifact', 'compact_trace_receipt_artifact', 'compact_trace_completeness_artifact', 'rtt_summary_artifact', 'rtt_summary', 'gate_failure_evidence', 'raw_requests', 'after_full_state', 'correctness_receipt', 'source_result_oracle', 'state_result_gate', 'routing_receipt', 'public_full_results_chunk_index']]
    evidence.extend(value for key, value in row.get('gates', {}).items() if key.endswith('_artifact'))
    assert any(evidence), ('Reference lacks evidence', row)
    for value in evidence:
        if isinstance(value, str):
            checked.add(str(resolve(value).relative_to(root)))
receipt = {'status': 'PASS', 'latency_cells': len(r['latency']), 'reference_arms': len(references['rows']), 'workload_arms_with_cycle_or_stage_evidence': sum(map(len, r['cycles'].values())), 'distinct_evidence_paths_checked': len(checked), 'paths': sorted(checked), 'verifier_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(root / 'result-links-verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: v for k, v in receipt.items() if k != 'paths'}))
