#!/usr/bin/env python3
"""Index executed protocol evidence by workload and configuration."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path

from aggregate_results import HERE, case_id, local


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def histogram(values):
    return dict(sorted(Counter(values).items()))


def display(values):
    return '/'.join(str(v) for v in sorted(set(values)))


def collect_rtt():
    contract = json.loads((HERE / 'coverage-contract.json').read_text())['cells']
    wanted = {(case_id(row), row['arm']) for row in contract}
    indexed = {}
    for name in ['native', 'tpcc', 'littlex']:
        source = HERE / name / 'rtt-cycle-evidence.json'
        if not source.exists():
            continue
        document = json.loads(source.read_text())
        if 'rows' in document:
            grouped = {}
            for row in document['rows']:
                record = dict(row)
                record.setdefault('artifact', str(source.relative_to(HERE)))
                record.setdefault('display', 'stage failure' if all(o['status'] != 'accepted' for o in row['observations']) else 'counts in observations')
                assert row['arm'] not in grouped.get(row['case_id'], {})
                grouped.setdefault(row['case_id'], {})[row['arm']] = record
            document = grouped
        for identifier, arms in document.items():
            for arm, record in arms.items():
                assert (identifier, arm) in wanted, ('Unexpected RTT command evidence', source, identifier, arm)
                assert arm not in indexed.get(identifier, {}), ('Duplicate RTT command evidence', identifier, arm)
                assert record.get('artifact') and record.get('display'), record
                observations = record.get('observations', [])
                labels = {}
                for observation in observations:
                    distribution = observation.get('sql_command_count_distribution', observation.get('command_count_distribution'))
                    if not distribution:
                        continue
                    values = sorted(int(value) for value in distribution)
                    sql = str(values[0]) if len(values) == 1 else f'{values[0]}–{values[-1]}'
                    exchanges = observation.get('response_exchange_count_distribution', distribution)
                    exchange_values = sorted(int(value) for value in exchanges)
                    if exchange_values != values:
                        suffix = str(exchange_values[0]) if len(exchange_values) == 1 else f'{exchange_values[0]}–{exchange_values[-1]}'
                        sql += f' ({suffix})'
                    labels[int(observation['delay_ms'])] = sql
                if labels:
                    record['display'] = ' / '.join(labels.get(delay, 'pending') for delay in [0, 2, 10])
                    record['display_definition'] = 'SQL command count range per request at 0 / +2 / +10 ms; parentheses give response-exchange count when different. All counts come from the same RTT requests.'
                indexed.setdefault(identifier, {})[arm] = record
    observed = {(identifier, arm) for identifier, arms in indexed.items() for arm in arms}
    missing = sorted(wanted - observed)
    (HERE / 'rtt-cycle-evidence.json').write_text(json.dumps(indexed, indent=2) + '\n')
    (HERE / 'rtt-cycle-coverage-progress.json').write_text(json.dumps({'observed_workload_arms': len(observed), 'required_workload_arms': len(wanted), 'missing': missing}, indent=2) + '\n')
    print(json.dumps({'metric': 'rtt', 'observed_workload_arms': len(observed), 'missing': len(missing)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metric', choices=['rtt', 'application'], default='rtt')
    args = parser.parse_args()
    if args.metric == 'rtt':
        collect_rtt()
        return
    indexed = {}
    native = HERE / 'native/protocol-summary.json'
    for row in json.loads(native.read_text())['arms']:
        assert row['all_response_delivery_and_PID_SQL_order_verified']
        identifier = 'tpcc-' + row['class']
        arm = 'jac_original' if row['variant'] == 'baseline' else 'jac_final'
        target = indexed.setdefault(identifier, {}).setdefault(arm, {'observations': []})
        target['observations'].append({'delay_ms': row['delay_ms'], 'sample_n': row['n'], 'complete_response_cycles': row['actual_complete_response_flight_counts'], 'SQL_counts': row['actual_SQL_counts'], 'SQL_categories_per_request': row['SQL_categories_per_request'], 'artifact': 'native/' + row['source'], 'source_sha256': row['source_sha256']})
    for arms in indexed.values():
        for row in arms.values():
            values = [int(v) for o in row['observations'] for v in o['complete_response_cycles']]
            row['display'] = display(values) + ' (0/+2 ms)'

    # A case must be the final selected immutable source, including a failed
    # compiler case whose direct baseline was executed successfully.
    selected = {r['case']: r for r in json.loads((HERE / 'tpcc/case-status.json').read_text()) if r.get('case')}
    candidates = {}
    for inputs in (HERE / 'profile-inputs').glob('tpcc-*'):
        receipt = inputs / 'source-case.json'
        if not receipt.exists():
            continue
        info = json.loads(receipt.read_text())
        case = info['case']
        if case not in selected:
            continue
        out = local(info['profile_output'])
        analysis = out / 'analysis.json'
        if not analysis.exists():
            continue
        profile = json.loads(analysis.read_text())
        if profile['status'] != 'PASS':
            continue
        requests = [r for r in profile['requests'] if not r['warmup']]
        assert len(requests) == profile['measured_requests'] and requests
        phase = requests[0]['phase']
        assert all(r['phase'] == phase for r in requests)
        selection = selected[case]
        stem = 'conventional' if selection['program'] == 'conventional' else selection['variant']
        arm = ('webridge_' if phase == 'sp' else 'java_') + stem
        identifier = 'tpcc-' + selection['workload']
        k = (identifier, arm)
        if k in candidates and candidates[k][0] > analysis.stat().st_mtime_ns:
            continue
        record = {'display': display([r['cycles'] for r in requests]) + ' (+2 ms)', 'artifact': str(analysis.relative_to(HERE)), 'artifact_sha256': digest(analysis), 'sample_n': len(requests), 'complete_response_cycles': histogram(r['cycles'] for r in requests), 'actual_CALL_count': histogram(r['actual_CALL_count'] for r in requests), 'execution_paths': histogram(r['execution_path'] for r in requests), 'business_commands_outside_CALL': histogram(r['business_commands_outside_CALL'] for r in requests), 'wire_categories': [r['wire_categories'] for r in requests], 'inside_CALL_categories': [[c['direct_child_counts'] for c in r['CALLs']] for r in requests], 'source_case': case}
        candidates[k] = (analysis.stat().st_mtime_ns, record)
    for (identifier, arm), (_, record) in candidates.items():
        indexed.setdefault(identifier, {})[arm] = record
    for selection in selected.values():
        if selection['status'] != 'failed-stage':
            continue
        stem = 'conventional' if selection['program'] == 'conventional' else selection['variant']
        arm = 'webridge_' + stem
        identifier = 'tpcc-' + selection['workload']
        assert arm not in indexed.get(identifier, {}), ('Failed compiler case has executed SP evidence', selection)
        indexed.setdefault(identifier, {})[arm] = {'display': 'failed ' + str(selection['failure']), 'stage_failure': selection['failure'], 'artifact': selection['pipeline'], 'source_case': selection['case']}

    # littleX owners publish an explicitly measured protocol index. Each entry
    # identifies its tier/mix, original endpoint and final immutable build.
    for source in [HERE / 'native/littlex-cycle-evidence.json', HERE / 'littlex/cycle-evidence.json']:
        if source.exists():
            document = json.loads(source.read_text())
            for identifier, arms in document.items():
                assert identifier.startswith('littlex-')
                for arm, record in arms.items():
                    assert arm not in indexed.get(identifier, {})
                    assert record['artifact'] and record['display']
                    indexed.setdefault(identifier, {})[arm] = record
    (HERE / 'cycle-evidence.json').write_text(json.dumps(indexed, indent=2) + '\n')
    wanted = json.loads((HERE / 'coverage-contract.json').read_text())['cells']
    missing = sorted({(case_id(r), r['arm']) for r in wanted if r['arm'] not in indexed.get(case_id(r), {})})
    (HERE / 'cycle-coverage-progress.json').write_text(json.dumps({'observed_workload_arms': sum(map(len, indexed.values())), 'required_workload_arms': 216, 'missing': missing}, indent=2) + '\n')
    print(json.dumps({'observed_workload_arms': sum(map(len, indexed.values())), 'missing': len(missing)}))


if __name__ == '__main__':
    main()
