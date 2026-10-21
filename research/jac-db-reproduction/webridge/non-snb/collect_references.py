#!/usr/bin/env python3
"""Join original-schedule references separately from the latency matrix."""
import argparse
import csv
import json
from pathlib import Path
from aggregate_results import measured_count_totals

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--native', type=Path, required=True)
parser.add_argument('--littlex', type=Path, required=True)
parser.add_argument('--metric', choices=['rtt', 'application'], default='rtt')
parser.add_argument('--tpcc', type=Path)
parser.add_argument('--out', type=Path)
args = parser.parse_args()
native = json.loads(args.native.read_text())
native_rows = native if isinstance(native, list) else native.get('rows', native.get('cells'))
littlex = json.loads(args.littlex.read_text())
rows = list(native_rows)
tpcc_source = args.tpcc or ROOT / ('tpcc/rtt-reference-900-index.json' if args.metric == 'rtt' else 'tpcc/reference-900-index.json')
tpcc_document = json.loads(tpcc_source.read_text())
tpcc_rows = tpcc_document if isinstance(tpcc_document, list) else tpcc_document['rows']
primary_java_arms = {prefix + stem for prefix in ['java_', 'webridge_'] for stem in ['full', 'pruned', 'conventional']}
rows.extend(row for row in tpcc_rows if row['arm'] in primary_java_arms)
controls = [row for row in tpcc_rows if row['arm'] not in primary_java_arms]
rows.extend(r for r in littlex['cells'] if r['method'] == 'reference')
keys = set()
for row in rows + controls:
    if args.metric == 'rtt':
        row.update(measured_count_totals(row))
    key = (row['family'], row['workload'], row.get('tweets_per_user'), row.get('write_percent'), row['arm'])
    assert key not in keys, ('Duplicate reference', key)
    keys.add(key)
    assert row['status'] in {'accepted', 'failed_with_stage_evidence', 'rejected_state_gate'}, row
    if row['status'] == 'rejected_state_gate':
        assert row.get('reference_median_ms') is None, row
tpcc = [r for r in rows if r['family'] == 'tpcc']
littlex = [r for r in rows if r['family'] == 'littlex']
assert len(tpcc) == 8 and len(littlex) == 160, (len(tpcc), len(littlex))
result = {'metric': args.metric, 'scope': 'Original schedules; separate from the 648 representative added-delay latency cells. Accepted source fallbacks retain actual CALL and activation counts.', 'tpcc_reference_arms': len(tpcc), 'littlex_reference_arms': len(littlex), 'rows': rows, 'additional_controls': controls}
destination = args.out or ROOT / ('rtt-reference-results.json' if args.metric == 'rtt' else 'reference-results.json')
destination.write_text(json.dumps(result, indent=2) + '\n')
fields = ['family', 'workload', 'tweets_per_user', 'write_percent', 'arm', 'status',
          'median_ms', 'reference_median_ms', 'timer', 'sample_n', 'warmup_n',
          'sql_command_count_distribution', 'response_exchange_count_distribution',
          'measured_sql_commands_total', 'mean_sql_commands_per_request',
          'measured_response_exchanges_total', 'mean_response_exchanges_per_request',
          'actual_calls', 'actual_call_requests', 'actual_call_fraction',
          'sdk_enabled_at_end_requests', 'sdk_enabled_at_end_fraction', 'sdk_flag_scope',
          'requests_artifact', 'artifact']
with destination.with_suffix('.csv').open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in row.items()} for row in rows)
print(json.dumps({k: v for k, v in result.items() if k not in {'rows', 'additional_controls'}}))
