#!/usr/bin/env python3
"""Independently recompute primary RTT sums and medians from public raw evidence."""
import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics


def read_rows(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt') as stream:
        if path.name.endswith(('.json', '.json.gz')):
            value = json.load(stream)
            assert isinstance(value, list), path
            yield from value
        else:
            for line in stream:
                if line.strip():
                    yield json.loads(line)


def close(a, b):
    assert math.isfinite(a) and math.isfinite(b)
    assert math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-5), (a, b)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--results', default='results.json')
    parser.add_argument('--out', default='rtt-verification.json')
    parser.add_argument('--allow-incomplete', action='store_true', help='Verify only an explicitly marked available subset')
    args = parser.parse_args()
    root = args.root.resolve()

    def resolve(value):
        text = str(value)
        if '/non-snb/' in text:
            text = text.split('/non-snb/', 1)[1]
        elif text.startswith('non-snb/'):
            text = text[len('non-snb/'):]
        path = root / text
        if not path.exists():
            path = path.with_suffix(path.suffix + '.gz')
        assert path.exists() and path.resolve().is_relative_to(root), value
        return path

    @lru_cache(maxsize=1)
    def mysql_trace(value):
        commands, delivered = {}, {}
        for event in read_rows(resolve(value)):
            if event.get('event') == 'command':
                k = (event['connection'], event['id'])
                assert k not in commands
                commands[k] = event
            elif event.get('event') == 'response_complete' and event.get('stage') == 'delivered':
                k = (event['connection'], event['command_id'])
                assert k not in delivered
                delivered[k] = event
        timeline = sorted(commands.values(), key=lambda command: command['at'])
        return commands, delivered, [command['at'] for command in timeline], timeline

    @lru_cache(maxsize=1)
    def native_trace(trace_value, catalog_value, receipt_value, completeness_value):
        catalog = json.loads(resolve(catalog_value).read_text())
        for identifier, sql in catalog.items():
            assert hashlib.sha256(' '.join(sql.split()).encode()).hexdigest()[:16] == identifier
        grouped = {}
        count = 0
        for call in read_rows(resolve(trace_value)):
            grouped.setdefault(call['request_tag'], []).append(call)
            assert all(identifier in catalog for identifier in call['SQL_ids'] + call['parse_SQL_ids'])
            count += 1
        receipt = json.loads(resolve(receipt_value).read_text())
        completeness = json.loads(resolve(completeness_value).read_text())
        assert receipt['stopped']
        assert receipt['client_received_bytes'] == receipt['client_forwarded_bytes']
        assert receipt['server_received_bytes'] == receipt['server_delivered_bytes']
        assert completeness['flight_count'] == count
        assert not any(completeness['pending_groups'].values())
        assert len(completeness['pending_groups']) == receipt['connections']
        return grouped

    results = json.loads((root / args.results).read_text())
    if args.allow_incomplete and isinstance(results, dict) and 'cells' in results:
        cells = results['cells']
        latency = [row for row in cells if row.get('method') != 'reference']
        results = {'metric': 'rtt', 'coverage': {'terminal_cells': len(latency), 'pending_cells': 648 - len(latency)},
                   'latency': latency, 'references': [row for row in cells if row.get('method') == 'reference']}
    assert results['metric'] == 'rtt'
    if not args.allow_incomplete:
        assert results['coverage']['terminal_cells'] == 648 and results['coverage']['pending_cells'] == 0
        assert len(results['references']) == 168
    verified = []
    all_values = list(results['latency']) + list(results['references'])
    for cell in all_values:
        if cell['status'] != 'accepted':
            continue
        path = resolve(cell['requests_artifact'])
        records = list(read_rows(path))
        measured, sql_counts, exchange_counts = [], Counter(), Counter()
        is_native = cell['arm'].startswith('jac_')
        if is_native:
            raw_native = native_trace(*(cell[name] for name in ['compact_trace_artifact', 'compact_trace_catalog_artifact', 'compact_trace_receipt_artifact', 'compact_trace_completeness_artifact']))
            tags = {row['request_tag'] for row in records}
            assert len(tags) == len(records)
            prefixes = {tag.rsplit('-', 1)[0] + '-' for tag in tags}
            owned_tags = {tag for tag in raw_native if any(tag.startswith(prefix) for prefix in prefixes)}
            assert owned_tags == tags, ('Raw native request omitted from published records', owned_tags - tags, tags - owned_tags)
        else:
            trace_path = cell.get('compact_trace_artifact')
            if not trace_path:
                summary = json.loads(resolve(cell['rtt_summary_artifact']).read_text())
                trace_path = summary['trace']
            commands, delivered, command_times, timeline = mysql_trace(trace_path)
        used = set()
        for row in records:
            if is_native:
                calls = row['calls']
                assert calls == raw_native[row['request_tag']], ('Native calls differ from raw all-connection trace', row['request_tag'])
                for call in calls:
                    assert call['reply_delivered_ns'] >= call['reply_complete_received_ns'] >= call['frontend_received_ns']
                    close(call['roundtrip_ms'], (call['reply_delivered_ns'] - call['frontend_received_ns']) / 1e6)
                    assert call['terminal_backend_type'] == 'Z'
                    assert call['SQL_count'] == len(call['SQL_ids'])
                    assert call['request_tag'] == row['request_tag']
                    identifier = (call['connection'], call['frontend_received_ns'])
                    assert identifier not in used
                    used.add(identifier)
                total = sum(call['roundtrip_ms'] for call in calls)
                close(total, row['sum_rtt_ms'])
                sql_n = sum(call['SQL_count'] for call in calls)
                assert sql_n == row['sql_command_count']
                assert len(calls) == row['response_exchange_count']
            else:
                calls = row['operations']
                first = commands[row['connection'], calls[0]['command_id'] - 1]
                last = commands[row['connection'], calls[-1]['command_id'] + 1]
                assert first['sql'].upper().startswith('SHOW SESSION STATUS')
                assert last['sql'].upper().startswith('SHOW SESSION STATUS')
                end = delivered[row['connection'], last['id']]['at']
                interval = timeline[bisect_left(command_times, first['at']):bisect_right(command_times, end)]
                unexpected = [command for command in interval if command['connection'] != row['connection']]
                assert not unexpected, ('Uncounted commands on another connection during request', row, unexpected)
                for call in calls:
                    k = (row['connection'], call['command_id'])
                    assert k not in used
                    used.add(k)
                    source, response = commands[k], delivered[k]
                    assert response['at'] >= source['at']
                    close(call['rtt_ms'], 1000 * (response['at'] - source['at']))
                    close(call['rtt_ms'], response['elapsed_ms'])
                    assert hashlib.sha256(source['sql'].encode()).hexdigest() == call['sql_sha256']
                total = sum(call['rtt_ms'] for call in calls)
                close(total, row['summed_db_call_rtt_ms'])
                sql_n = len(calls)
                assert sql_n == row['command_count']
            if not row['warmup']:
                measured.append(total)
                sql_counts[str(sql_n)] += 1
                exchange_counts[str(len(calls))] += 1
        assert len(measured) == cell['sample_n'], (cell, len(measured))
        assert len(records) - len(measured) == cell['warmup_n']
        value = cell.get('median_ms', cell.get('reference_median_ms'))
        close(statistics.median(measured), value)
        assert dict(sql_counts) == cell['sql_command_count_distribution']
        assert dict(exchange_counts) == cell['response_exchange_count_distribution']
        for name, counts in [('sql_commands', sql_counts), ('response_exchanges', exchange_counts)]:
            total = sum(int(value) * frequency for value, frequency in counts.items())
            if 'measured_' + name + '_total' in cell:
                assert cell['measured_' + name + '_total'] == total
                close(cell['mean_' + name + '_per_request'], total / len(measured))
        verified.append({'family': cell['family'], 'workload': cell['workload'], 'arm': cell['arm'],
                         'delay_ms': cell.get('delay_ms'), 'sample_n': len(measured),
                         'warmup_n': len(records) - len(measured), 'median_ms': value,
                         'requests_artifact': str(path.relative_to(root)),
                         'requests_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    receipt = {'status': 'PASS', 'coverage_scope': 'Available subset only' if args.allow_incomplete else 'Complete primary report',
               'primary_metric': 'Per-request sum of complete SQL command-response RTT',
               'latency_cells': len(results['latency']), 'reference_entries': len(results['references']),
               'accepted_values_verified': len(verified), 'measured_requests_verified': sum(x['sample_n'] for x in verified),
               'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'values': verified}
    (root / args.out).write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'values'}))


if __name__ == '__main__':
    main()
