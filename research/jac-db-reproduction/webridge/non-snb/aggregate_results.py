#!/usr/bin/env python3
"""Join observed cells against the frozen coverage contract before publication."""
import argparse
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYS = ['family', 'workload', 'tweets_per_user', 'write_percent', 'arm', 'delay_ms']


def key(row):
    return tuple(row.get(k) for k in KEYS)


def local(value):
    p = Path(value)
    if p.exists():
        return p
    if '/non-snb/' in str(p):
        return HERE / str(p).split('/non-snb/', 1)[1]
    if str(p).startswith('non-snb/'):
        return HERE / str(p)[len('non-snb/'):]
    return HERE / p


def case_id(row):
    stem = row['family'] + '-' + row['workload']
    if row.get('tweets_per_user') is not None:
        stem += '-t' + str(row['tweets_per_user'])
    if row.get('write_percent') is not None:
        stem += '-w' + str(row['write_percent'])
    return stem


def measured_count_totals(row):
    result = {}
    for kind, field in [('sql_commands', 'sql_command_count_distribution'), ('response_exchanges', 'response_exchange_count_distribution')]:
        distribution = row.get(field)
        if not distribution:
            continue
        n = sum(distribution.values())
        assert n == row['sample_n'], ('Count histogram sample mismatch', row)
        total = sum(int(value) * frequency for value, frequency in distribution.items())
        result['measured_' + kind + '_total'] = total
        result['mean_' + kind + '_per_request'] = total / n
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--metric', choices=['rtt', 'application'], default='rtt')
    p.add_argument('--inputs', nargs='+', type=Path)
    p.add_argument('--allow-incomplete', action='store_true')
    a = p.parse_args()
    if a.inputs is None:
        a.inputs = ([HERE / 'native/normalized-rtt-latency.json', HERE / 'tpcc/normalized-rtt-latency.json', HERE / 'littlex/normalized-rtt-results.json']
                    if a.metric == 'rtt' else
                    [HERE / 'native/normalized-latency.json', HERE / 'tpcc/normalized-latency.json', HERE / 'littlex/normalized-results.json'])
    contract = json.loads((HERE / 'coverage-contract.json').read_text())
    wanted = {key(r): r for r in contract['cells']}
    assert len(wanted) == 648
    observed = {}
    references = []
    for source in a.inputs:
        if not source.exists() and a.allow_incomplete:
            continue
        document = json.loads(source.read_text())
        rows = document if isinstance(document, list) else document['cells']
        for row in rows:
            if row.get('status') == 'pending' and a.allow_incomplete:
                continue
            if row.get('method') == 'reference':
                references.append(row)
                continue
            k = key(row)
            assert k in wanted, ('Unexpected cell', source, k)
            assert k not in observed, ('Duplicate cell', source, k)
            assert row['status'] in ['accepted', 'failed_with_stage_evidence'], row
            artifact = local(row['artifact'])
            assert artifact.exists() or artifact.with_suffix(artifact.suffix + '.gz').exists(), artifact
            if row['status'] == 'accepted':
                assert isinstance(row['median_ms'], (int, float)) and math.isfinite(row['median_ms']) and row['median_ms'] > 0, row
                if a.metric == 'rtt':
                    assert 'round' in row.get('timer', '').lower() or 'rtt' in row.get('timer', '').lower(), ('Primary value must explicitly identify SQL round-trip timing', row)
            else:
                assert row.get('median_ms') is None, ('Stage failure has fabricated latency', row)
            observed[k] = {**row, **(measured_count_totals(row) if a.metric == 'rtt' else {}), 'case_id': case_id(row), 'normalized_source': str(source.relative_to(HERE) if source.is_relative_to(HERE) else source)}
    missing = [r for k, r in wanted.items() if k not in observed]
    coverage = {'metric': a.metric, 'required_cells': 648, 'terminal_cells': len(observed), 'pending_cells': len(missing), 'accepted_cells': sum(r['status'] == 'accepted' for r in observed.values()), 'failed_stage_cells': sum(r['status'] == 'failed_with_stage_evidence' for r in observed.values()), 'pending': missing}
    (HERE / ('rtt-coverage-progress.json' if a.metric == 'rtt' else 'application-coverage-progress.json')).write_text(json.dumps(coverage, indent=2) + '\n')
    if missing:
        assert a.allow_incomplete, ('Incomplete coverage', len(missing))
        partial_name = 'rtt-results.partial.json' if a.metric == 'rtt' else 'application-results.partial.json'
        scope = 'Available primary SQL round-trip measurements' if a.metric == 'rtt' else 'Secondary application timings; retained partial quiet-run coverage'
        (HERE / partial_name).write_text(json.dumps({'metric': a.metric, 'scope': scope, 'coverage': coverage, 'latency': list(observed.values()), 'references': references}, indent=2) + '\n')
        print(json.dumps({k: v for k, v in coverage.items() if k != 'pending'}))
        return
    rows = [observed[key(r)] for r in contract['cells']]
    cases = {}
    for row in rows:
        identifier = row['case_id']
        if identifier in cases:
            continue
        title = ('TPC-C: ' if row['family'] == 'tpcc' else 'littleX: ') + row['workload'].replace('_', ' ')
        subtitle = ('Median summed SQL round-trip time per request (ms)' if a.metric == 'rtt' else 'Median application request time (ms)') + '; added database-response delay by column'
        if row['family'] == 'littlex':
            subtitle += f"; {row['tweets_per_user']} tweets / user"
            if 'write_percent' in row:
                subtitle += f"; {row['write_percent']}% writes"
        boundary = ('Compact proxy: frontend command arrival to complete-response delivery; per-request sum across owned connections. SQL counts use the same requests. Database, communication and configured delay are included; application work between calls is outside.' if a.metric == 'rtt' else 'Native: HTTP client wall; Java: application-call boundary. Counts use separately stated scopes.')
        cases[identifier] = {'id': identifier, 'title': title, 'subtitle': subtitle, 'source': f"Source: results.json / results.csv, case_id={identifier}; per-cell raw and gate links retained", 'note': boundary + ' PostgreSQL 18 / MySQL 5.7. CALL %: requests invoking a procedure; E%: SDK enabled after request, shown when different. Per-request SQL/fallback and stage evidence are retained.'}
    for row in rows:
        if row['status'] == 'failed_with_stage_evidence':
            labels = {'synth': 'synthesis failed', 'replay': 'replay failed',
                      'install': 'install failed', 'record': 'record failed',
                      'baseline': 'baseline failed'}
            stage = row.get('failed_stage', row.get('failure'))
            row['display_status'] = row.get('display_status', labels.get(stage, str(stage) + ' failed' if stage else 'runtime/gate failed'))
    narrative = json.loads((HERE / 'report_narrative.json').read_text())
    cycles_path = HERE / ('rtt-cycle-evidence.json' if a.metric == 'rtt' else 'cycle-evidence.json')
    assert cycles_path.exists(), 'Complete observed-cycle index before rendering the report'
    cycles = json.loads(cycles_path.read_text())
    expected_arms = {(case_id(row), row['arm']) for row in contract['cells']}
    actual_arms = {(identifier, arm) for identifier, arms in cycles.items() for arm in arms}
    assert expected_arms == actual_arms, ('Incomplete command/stage evidence', sorted(expected_arms - actual_arms), sorted(actual_arms - expected_arms))
    if a.metric == 'rtt':
        for identifier, arm in sorted(expected_arms):
            observations = cycles[identifier][arm]['observations']
            by_delay = {int(o['delay_ms']): o for o in observations}
            assert len(by_delay) == len(observations) and set(by_delay) == {0, 2, 10}, ('Incomplete or duplicate same-request count evidence', identifier, arm)
            for delay, observation in by_delay.items():
                row = next(r for r in rows if r['case_id'] == identifier and r['arm'] == arm and r['delay_ms'] == delay)
                if row['status'] != 'accepted':
                    assert observation.get('status') == row['status'], (identifier, arm, delay)
                    continue
                counts = observation.get('sql_command_count_distribution', observation.get('command_count_distribution'))
                assert counts == row['sql_command_count_distribution'], ('Count index differs from timing requests', identifier, arm, delay)
    reference_data = json.loads((HERE / ('rtt-reference-results.json' if a.metric == 'rtt' else 'reference-results.json')).read_text())
    assert reference_data['tpcc_reference_arms'] == 8 and reference_data['littlex_reference_arms'] == 160
    assert len(reference_data['rows']) == 168
    result = {'schema': 2, 'metric': a.metric, 'coverage': coverage, 'latency': rows, 'references': reference_data['rows'], 'additional_reference_controls': reference_data.get('additional_controls', []), 'cases': list(cases.values()), 'cycles': cycles, 'narrative_before_data': narrative['before'], 'narrative_after_data': narrative['after']}
    stem = 'results' if a.metric == 'rtt' else 'application-results'
    (HERE / (stem + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    fields = ['case_id', *KEYS, 'status', 'median_ms', 'timer', 'sample_n', 'warmup_n',
              'sql_command_count_distribution', 'response_exchange_count_distribution',
              'measured_sql_commands_total', 'mean_sql_commands_per_request',
              'measured_response_exchanges_total', 'mean_response_exchanges_per_request',
              'actual_call_fraction', 'sdk_enabled_at_end_fraction', 'requests_artifact',
              'rtt_summary_artifact', 'compact_trace_artifact', 'compact_trace_catalog_artifact',
              'compact_trace_receipt_artifact', 'compact_trace_completeness_artifact', 'artifact', 'normalized_source']
    with (HERE / (stem + '.csv')).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in row.items()} for row in rows)
    print(json.dumps({k: v for k, v in coverage.items() if k != 'pending'}))


if __name__ == '__main__':
    main()
