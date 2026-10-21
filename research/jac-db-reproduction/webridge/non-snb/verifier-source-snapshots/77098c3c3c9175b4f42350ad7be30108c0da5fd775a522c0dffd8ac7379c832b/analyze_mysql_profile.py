#!/usr/bin/env python3
"""Verify actual request/response cycles and executed stored-program work."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re


def read_lines(path):
    if not path.exists() and path.suffix != '.gz':
        path = path.with_suffix(path.suffix + '.gz')
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def category(sql):
    text = ' '.join((sql or '').lower().split())
    if text.startswith(('begin', 'start transaction')):
        return 'transaction.begin'
    if text.startswith('commit'):
        return 'transaction.commit'
    if text.startswith('savepoint '):
        return 'framework.savepoint'
    if text.startswith('release savepoint '):
        return 'framework.release_savepoint'
    if text.startswith('rollback to '):
        return 'framework.rollback_to_savepoint'
    if text.startswith('rollback'):
        return 'transaction.rollback'
    if text.startswith('set '):
        return 'transaction.setting'
    if text.startswith('call '):
        return 'stored_procedure.call'
    if 'information_schema' in text or 'mysql.proc' in text or text.startswith('show create procedure'):
        return 'driver.procedure_metadata'
    if 'identity_users' in text or 'identity_lookups' in text:
        return 'identity.lookup'
    if 'graph_types' in text:
        return 'type_registry'
    if 'kv_state' in text:
        return 'schema.guard'
    if text.startswith('insert') and 'anchors' in text:
        return 'write.anchor_upsert'
    if text.startswith('select a.id, a.kind') or text.startswith('select a.id,a.kind'):
        return 'hydration.full_anchor'
    relational = ['warehouse', 'district', 'customer', 'stock', 'orders', 'new_order', 'order_line', 'history',
                  'lx_profiles', 'lx_tweets', 'lx_follows']
    # Resolve the actual target/primary FROM table before considering joined
    # tables. UPDATE lx_tweets JOIN lx_profiles mutates tweets, not profiles.
    verb = text.split()[0] if text else 'empty'
    target = re.search(r'^(?:update|insert(?:\s+ignore)?\s+into|replace\s+into|delete\s+from)\s+(?:`?\w+`?\.)?`?(\w+)`?', text)
    if target is None and verb == 'select':
        target = re.search(r'\bfrom\s+(?:`?\w+`?\.)?`?(\w+)`?', text)
    if target is not None and target.group(1) in relational:
        return 'relational.' + target.group(1) + '.' + verb
    for table in relational:
        if re.search(r'\b' + table + r'\b', text):
            return 'relational.' + table + '.' + text.split()[0]
    if 'anchors' in text:
        return 'graph.anchor_query'
    if re.search(r'\bjac_\w+\b', text):
        return 'graph.projected_query'
    return 'other.' + (text.split()[0] if text else 'empty')


def generated_sources(path):
    if path is None:
        return {}, []
    inputs = json.loads(path.read_text())
    assert isinstance(inputs, list)
    definitions = {}
    receipts = []
    for filename in inputs:
        source_path = Path(filename)
        if not source_path.is_absolute():
            source_path = path.parent / source_path
        if not source_path.exists() and '/non-snb/' in str(source_path):
            source_path = Path(__file__).resolve().parent / str(source_path).split('/non-snb/', 1)[1]
        text = source_path.read_text()
        names = re.findall(r'CREATE\s+(?:DEFINER\s*=\s*\S+\s+)?PROCEDURE\s+`?(\w+)`?', text, re.I)
        if not names:
            continue
        assert len(names) == 1, source_path
        cursors = dict(re.findall(r'DECLARE\s+cursor_(\d+)\s+CURSOR\s+FOR\s+(.*?);', text, re.I | re.S))
        definitions[names[0].casefold()] = {'cursors': cursors, 'source': str(source_path),
                                'sha256': hashlib.sha256(source_path.read_bytes()).hexdigest()}
        receipts.append({'path': str(source_path), 'sha256': hashlib.sha256(source_path.read_bytes()).hexdigest()})
    return definitions, receipts


def analyze(root, sources_path=None):
    collection = json.loads((root / 'collection.json').read_text())
    assert collection['status'] == 'PASS', collection
    restored = json.loads((root / 'instrumentation-restored.json').read_text())
    assert restored['exact_prior_settings_restored']
    config = json.loads((root / 'config.json').read_text())
    controls = bool(config.get('all_control_events'))
    events = read_lines(root / 'protocol.jsonl.gz')
    assert not [event for event in events if event['event'] in
                ['overlapping_command', 'unexpected_column_terminator', 'unsupported_local_infile']]
    commands = [event for event in events if event['event'] == 'command']
    assert commands and len({event['connection'] for event in commands}) == 1
    ends = {(event['command_id'], event['stage']): event for event in events
            if event['event'] == 'response_complete'}
    frames = Counter()
    for event in events:
        if event['event'] == 'server_frame' and event['stage'] == 'delivered':
            frames[event['command_id']] += event['payload_bytes'] + 4
    for current, following in zip(commands, commands[1:]):
        assert following['at'] >= ends[current['id'], 'delivered']['at'], (current, following)
    rows = read_lines(root / 'run/rows.jsonl')
    bounds = [index for index, command in enumerate(commands)
              if command['sql'].upper().startswith('SHOW SESSION STATUS')]
    assert len(bounds) == 2 * len(rows), (len(bounds), len(rows))
    pfs = read_lines(root / 'pfs.jsonl')
    connection = json.loads((root / 'connection.json').read_text())
    assert all(event['thread'] == connection['thread_id'] for event in pfs)
    assert len({(event['thread'], event['event']) for event in pfs}) == len(pfs)
    snapshots = json.loads((root / 'P_S-thread-summary-snapshots.json').read_text())
    latest = next((snapshot['rows'] for snapshot in reversed(snapshots) if snapshot['rows']), None)
    assert latest, 'A live final thread summary is required'
    totals = {event['name']: event['count'] for event in latest}
    selected = ['statement/sp/stmt', 'statement/sp/copen', 'statement/sql/call_procedure']
    observed = Counter(event['name'] for event in pfs)
    completeness = {}
    for name in selected:
        completeness[name] = {'server_thread_count': totals.get(name, 0), 'captured': observed[name]}
        assert totals.get(name, 0) == observed[name], (name, completeness[name])
    definitions, source_receipts = generated_sources(sources_path)
    calls = [event for event in pfs if event['name'] == 'statement/sql/call_procedure']
    call_index = 0
    output = []
    for index, row in enumerate(rows):
        actual_commands = commands[bounds[2 * index] + 1:bounds[2 * index + 1]]
        assert len(actual_commands) == row['questions'], (index, len(actual_commands), row['questions'])
        operations = []
        trees = []
        for command in actual_commands:
            delivered = ends[command['id'], 'delivered']
            received = ends[command['id'], 'received']
            operations.append({'command_id': command['id'], 'category': category(command['sql']),
                               'sql': command['sql'], 'sql_sha256': hashlib.sha256(command['sql'].encode()).hexdigest(),
                               'command_to_complete_ms': delivered['elapsed_ms'],
                               'server_receive_ms': received['elapsed_ms'],
                               'added_delivery_ms': (delivered['at'] - received['at']) * 1000,
                               'response_frames': delivered['frames'], 'result_sets': delivered['resultsets'],
                               'response_rows': delivered['rows'], 'response_wire_bytes': frames[command['id']],
                               'command_wire_bytes': len(command['sql'].encode()) + 5,
                               'server_error': delivered['error']})
            if category(command['sql']) != 'stored_procedure.call':
                continue
            parent = calls[call_index]
            call_index += 1
            call_name = re.match(r'CALL\s+`?(\w+)`?', command['sql'], re.I)[1]
            parent_name = re.match(r'CALL\s+`?(\w+)`?', parent.get('sql') or '', re.I)[1]
            assert call_name == parent_name
            assert parent['end_event'] is not None
            children = [event for event in pfs if parent['event'] < event['event'] <= parent['end_event']]
            direct = [event for event in children if event['nest'] == parent['event']]
            missing = sorted(set(range(parent['event'] + 1, parent['end_event'] + 1)) - {event['event'] for event in children})
            if controls:
                assert not missing
            labels = {}
            associations = []
            for event in children:
                if event['name'] != 'statement/sp/copen':
                    continue
                procedure = definitions.get((event.get('object') or '').casefold())
                assert procedure, ('Generated source required for cursor', event)
                siblings = [sibling for sibling in children
                            if sibling['nest'] == event['nest'] and sibling['event'] > event['event']]
                returned = next((sibling for sibling in siblings
                                 if sibling['name'] == 'statement/sp/stmt'
                                 and re.match(r'SELECT\s+cursor_cnt_(\d+)', sibling.get('sql') or '', re.I)), None)
                assert returned, event
                number = re.match(r'SELECT\s+cursor_cnt_(\d+)', returned['sql'], re.I)[1]
                declaration = procedure['cursors'][number]
                labels[event['event']] = 'business.cursor.' + category(declaration)
                associations.append({'open_event_id': event['event'], 'return_event_id': returned['event'],
                                     'cursor_number': number, 'declared_SQL': declaration,
                                     'source': procedure['source'], 'source_sha256': procedure['sha256']})
            costs = Counter()
            counts = Counter()
            for event in direct:
                statement = event.get('sql') or ''
                if event['event'] in labels:
                    label = labels[event['event']]
                elif event['name'] == 'statement/sp/stmt':
                    if re.match(r'SELECT\s+(?:QUERY_ID|cursor_cnt_|cursor_s)', statement, re.I):
                        label = 'return.materialized_result_or_metadata'
                    elif statement.lower().startswith('select') and not re.search(r'\bfrom\b', statement, re.I):
                        label = 'return.scalar'
                    else:
                        kind = category(statement)
                        label = kind if kind.startswith(('transaction.', 'framework.')) else 'business.' + kind
                else:
                    label = 'control.' + event['name'].split('/')[-1]
                counts[label] += 1
                costs[label] += event['timer_ps'] / 1e9
            triggers = [event for event in children if event.get('object_type') == 'TRIGGER']
            trees.append({'parent_event_id': parent['event'], 'procedure': call_name,
                          'parent_inclusive_ms': parent['timer_ps'] / 1e9, 'parent_error': parent['error'],
                          'captured_nested_events': len(children), 'missing_event_ids': missing,
                          'control_events_instrumented': controls,
                          'direct_child_counts': dict(counts), 'direct_child_timer_ms': dict(costs),
                          'cursor_associations': associations, 'direct_children': direct,
                          'trigger_event_count': len(triggers),
                          'trigger_inclusive_timers_overlap': True})
        enabled_end = row.get('sp_enabled_at_end', row.get('sp_enabled_end'))
        if row['phase'] != 'sp':
            assert not trees
        call_counter = row.get('call_procedure', (row.get('status_delta') or {}).get('Com_call_procedure'))
        if call_counter is not None:
            assert len(trees) == call_counter
        execution = 'direct'
        outside_calls = [operation for operation in operations
                         if not operation['category'].startswith(('transaction.', 'driver.', 'framework.'))
                         and operation['category'] != 'stored_procedure.call']
        if row['phase'] == 'sp':
            execution = 'call_and_direct_sql' if trees and outside_calls else 'call_only' if trees else 'fallback'
        output.append({'iteration': row['iteration'], 'warmup': row['warmup'], 'phase': row['phase'],
                       'execution_path': execution, 'actual_CALL_count': len(trees),
                       'business_commands_outside_CALL': len(outside_calls),
                       'sp_enabled_at_end': enabled_end,
                       'op': row.get('op'), 'cycles': len(actual_commands),
                       'instrumented_request_ms': row['ms'], 'operations': operations,
                       'wire_categories': dict(Counter(operation['category'] for operation in operations)),
                       'response_wire_bytes': sum(operation['response_wire_bytes'] for operation in operations),
                       'response_frames': sum(operation['response_frames'] for operation in operations),
                       'CALLs': trees})
    assert call_index == len(calls)
    result = {'status': 'PASS', 'analyzer_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'scope': 'Wire cycles, complete-response ordering and captured stored-program events',
              'request_count': len(output), 'measured_requests': sum(not row['warmup'] for row in output),
              'server_thread_count_checks': completeness, 'generated_sources': source_receipts,
              'result_equality_gate': 'The workload collector separately verifies outputs and database state.',
              'requests': output}
    (root / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--generated-sources-json', type=Path)
    args = parser.parse_args()
    result = analyze(args.directory.resolve(), args.generated_sources_json)
    print(json.dumps({'status': result['status'], 'measured_requests': result['measured_requests']}))
