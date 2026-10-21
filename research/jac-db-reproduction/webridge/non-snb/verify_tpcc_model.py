#!/usr/bin/env python3
"""Check every mutable business field against a seed-derived Python model."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEEDS = HERE / 'seed-inputs' if (HERE / 'seed-inputs/manifest.json').exists() else HERE.parents[1] / 'benchmark/tpcc/data'
FIELDS = {
    'warehouse': 'w_id w_ytd',
    'district': 'd_w_id d_id d_ytd d_next_o_id',
    'customer': 'c_w_id c_d_id c_id c_balance c_ytd_payment c_payment_cnt c_data',
    'stock': 's_w_id s_i_id s_quantity s_ytd s_order_cnt s_remote_cnt',
    'orders': 'o_w_id o_d_id o_id o_c_id o_carrier_id o_ol_cnt o_all_local',
    'new_order': 'no_w_id no_d_id no_o_id',
    'order_line': 'ol_w_id ol_d_id ol_o_id ol_number ol_i_id ol_supply_w_id ol_quantity ol_amount ol_dist_info',
    'history': 'h_c_w_id h_c_d_id h_c_id h_w_id h_d_id h_amount h_data',
}
MONEY = {'warehouse': {1}, 'district': {2}, 'customer': {3, 4},
         'order_line': {7}, 'history': {5}}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed(name):
    with (SEEDS / (name + '.jsonl')).open() as handle:
        for line in handle:
            yield json.loads(line)


def normalized(table, values):
    result = []
    for index, value in enumerate(values):
        if index in MONEY.get(table, set()):
            # Jac stores binary floats; compare their specified cent precision.
            value = format(Decimal(str(round(float(value), 2))).quantize(Decimal('.01')), 'f')
        result.append(None if value is None else str(value))
    return tuple(result)


def project(table, row):
    return normalized(table, [row[field] for field in FIELDS[table].split()])


def actual(folder, table):
    manifest = json.loads((folder / 'manifest.json').read_text())
    path = folder / (table + '.jsonl')
    compressed = not path.exists()
    if compressed:
        path = path.with_suffix(path.suffix + '.gz')
    result = Counter()
    digest = hashlib.sha256()
    with (gzip.open(path, 'rb') if compressed else path.open('rb')) as handle:
        for line in handle:
            digest.update(line)
            result[normalized(table, json.loads(line))] += 1
    assert digest.hexdigest() == manifest[table]['sha256'], path
    assert sum(result.values()) == manifest[table]['rows']
    return result


def compare(folder, expected, scoped=False):
    counts = {}
    for table, rows in expected.items():
        found = actual(folder, table)
        assert (not (found - rows) if scoped else found == rows), (str(folder), table,
                               'missing', list((rows - found).items())[:2],
                               'extra', list((found - rows).items())[:2])
        counts[table] = sum(found.values())
    if scoped:
        global_counts = json.loads((folder / 'global-counts.json').read_text())
        assert global_counts == {name: sum(rows.values()) for name, rows in expected.items()}, global_counts
    return counts


def same_input(expected, actual):
    """Original logical fields and ordered lines, allowing graph UUID bindings."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(same_input(value, actual.get(key)) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(same_input(a, b) for a, b in zip(expected, actual))
    return expected == actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    global SEEDS
    parser.add_argument('--gate', type=Path, default=HERE / 'tpcc/gate-original900')
    parser.add_argument('--seed-dir', type=Path, default=SEEDS, help='Original seed-42 generator output, including manifest.json')
    parser.add_argument('--seed-projection', choices=['relational', 'jac'], default='relational')
    parser.add_argument('--native', action='store_true', help='Read native HTTP gate and compressed state layout')
    parser.add_argument('--repeat-index', type=int, help='Repeat this original-plan input for a representative native cell')
    parser.add_argument('--repeat-count', type=int, default=40)
    parser.add_argument('--profile-case', type=Path, help='Immutable Java case; gate points to profiler run/ with scoped before/after snapshots')
    parser.add_argument('--original-prefix', type=int, help='Check this many original ordered requests and their complete committed state')
    parser.add_argument('--before-dir', type=Path, help='Override the retained initial-state directory')
    parser.add_argument('--after-dir', type=Path, help='Override the retained final-state directory')
    parser.add_argument('--request-log', type=Path, help='Override the retained original request JSONL')
    args = parser.parse_args()
    gate = args.gate.resolve()
    SEEDS = args.seed_dir.resolve()
    if args.native:
        assert args.seed_projection == 'jac'
    seed_manifest = json.loads((SEEDS / 'manifest.json').read_text())
    for entry in seed_manifest['files']:
        assert sha(SEEDS / entry['file']) == entry['sha256'], entry['file']
    plan = json.loads((HERE / 'tpcc-plan-900.json').read_text())
    if args.original_prefix is not None:
        assert args.repeat_index is None and args.profile_case is None
        assert 0 < args.original_prefix <= len(plan)
        plan = plan[:args.original_prefix]
    if args.profile_case:
        assert not args.native and args.seed_projection == 'jac' and args.repeat_index is None
        meta = json.loads((args.profile_case / 'metadata.json').read_text())
        snapshot = Path(meta['snapshot'])
        if not snapshot.exists():
            snapshot = HERE / str(snapshot).split('/non-snb/', 1)[1]
        source_input = json.loads((snapshot / 'input.json').read_text())
        matches = [i for i, row in enumerate(plan) if same_input(row, source_input)]
        assert len(matches) == 1, matches
        args.repeat_index = matches[0]
        profile_logs = [json.loads(line) for line in (gate / 'rows.jsonl').read_text().splitlines()]
        args.repeat_count = len(profile_logs)
    if args.repeat_index is not None:
        assert (args.native or args.profile_case) and 0 <= args.repeat_index < len(plan) and args.repeat_count > 0
        plan = [plan[args.repeat_index]] * args.repeat_count
    warehouses = {x['w_id']: x for x in seed('warehouse')}
    districts = {(x['d_w_id'], x['d_id']): x for x in seed('district')}
    customers = {(x['c_w_id'], x['c_d_id'], x['c_id']): x for x in seed('customer')}
    stocks = {(x['s_w_id'], x['s_i_id']): x for x in seed('stock')}
    prices = {x['i_id']: x['i_price'] for x in seed('item')}
    expected = {name: Counter() for name in FIELDS}
    for name, values in [('warehouse', warehouses), ('district', districts),
                         ('customer', customers), ('stock', stocks)]:
        expected[name].update(project(name, value) for value in values.values())
    for row in seed('orders'):
        row['o_carrier_id'] = row['o_carrier_id'] or 0
        expected['orders'][project('orders', row)] += 1
        if row['new_order']:
            expected['new_order'][normalized('new_order', [row['o_w_id'], row['o_d_id'], row['o_id']])] += 1
        for line in row['lines']:
            line = dict(line, ol_w_id=row['o_w_id'], ol_d_id=row['o_d_id'], ol_o_id=row['o_id'])
            expected['order_line'][project('order_line', line)] += 1
    if args.seed_projection == 'jac':
        # The original Jac seed walker creates one History per Customer.
        # Its literal payload differs from the separate relational history file.
        expected['history'].update(normalized('history', [row['c_w_id'], row['c_d_id'], row['c_id'],
                                                          row['c_w_id'], row['c_d_id'], 10.0, 'seed'])
                                   for row in customers.values())
    else:
        expected['history'].update(project('history', row) for row in seed('history'))
    before_folder = gate / ('before-state' if args.native else 'results/before')
    after_folder = gate / ('after-state' if args.native else 'results/after')
    if args.repeat_index is not None and not args.profile_case:
        before_folder = HERE / 'native/tpcc-gates/baseline/before-state'
        after_folder = gate / 'after40-state'
    request_path = gate / ('rows.jsonl' if args.native else 'results/requests.jsonl')
    if args.profile_case:
        before_folder, after_folder, request_path = gate / 'before', gate / 'after', gate / 'rows.jsonl'
    before_folder = args.before_dir or before_folder
    after_folder = args.after_dir or after_folder
    request_path = args.request_log or request_path
    before_counts = compare(before_folder, expected, scoped=bool(args.profile_case))
    logs = [json.loads(line) for line in request_path.read_text().splitlines()]
    assert len(logs) == len(plan)
    outcomes = Counter()
    for index, (transaction, log) in enumerate(zip(plan, logs)):
        if args.repeat_index is not None:
            assert log['iteration'] == index
            if not args.profile_case:
                assert log['original_plan_index'] == args.repeat_index
        else:
            assert log['index' if args.native else 'idx'] == index
            actual_input = log['transaction' if args.native else 'input']
            assert same_input(transaction, actual_input), index
        w = warehouses[1]
        d = districts[(1, transaction['d_id'])]
        if transaction['kind'] == 'new_order':
            if transaction['invalid']:
                if args.native:
                    assert log['rollback'] and log['status'] == 500
                    assert log['result']['error']['message'] == 'item not found'
                else:
                    assert not log['result']['success'] and log['result']['rolled_back']
                    assert log['categories'].get('transaction.rollback') == 1
                outcomes['rollback'] += 1
                continue
            customer = customers[(1, transaction['d_id'], transaction['c_id'])]
            order_id = d['d_next_o_id']
            d['d_next_o_id'] += 1
            lines = transaction['lines']
            local = int(all(line['supply_w_id'] == 1 for line in lines))
            expected['orders'][normalized('orders', [1, transaction['d_id'], order_id,
                                                     transaction['c_id'], 0, len(lines), local])] += 1
            expected['new_order'][normalized('new_order', [1, transaction['d_id'], order_id])] += 1
            total = 0.0
            for number, line in enumerate(lines, 1):
                stock = stocks[(line['supply_w_id'], line['i_id'])]
                quantity = line['quantity']
                next_quantity = stock['s_quantity'] - quantity
                stock['s_quantity'] = next_quantity + (91 if next_quantity < 10 else 0)
                stock['s_ytd'] += quantity
                stock['s_order_cnt'] += 1
                stock['s_remote_cnt'] += int(line['supply_w_id'] != 1)
                amount = round(quantity * prices[line['i_id']], 2)
                total += amount
                values = [1, transaction['d_id'], order_id, number, line['i_id'],
                          line['supply_w_id'], quantity, amount,
                          stock[f"s_dist_{transaction['d_id']:02d}"]]
                expected['order_line'][normalized('order_line', values)] += 1
            result = {'success': True, 'o_id': order_id, 'ol_cnt': len(lines),
                      'total': round(total * (1 - customer['c_discount']) * (1 + w['w_tax'] + d['d_tax']), 2)}
            outcomes['new_order'] += 1
        else:
            if transaction['c_id'] is not None:
                customer = customers[(1, transaction['c_d_id'], transaction['c_id'])]
            else:
                matches = [row for row in customers.values()
                           if row['c_w_id'] == 1 and row['c_d_id'] == transaction['c_d_id']
                           and row['c_last'] == transaction['c_last']]
                matches.sort(key=lambda row: row['c_first'])
                customer = matches[len(matches) // 2]
            amount = transaction['amount']
            w['w_ytd'] += amount
            d['d_ytd'] += amount
            customer['c_balance'] -= amount
            customer['c_ytd_payment'] += amount
            customer['c_payment_cnt'] += 1
            if customer['c_credit'] == 'BC':
                prefix = f"{customer['c_id']},{d['d_id']},1,{round(amount, 2)}|"
                customer['c_data'] = (prefix + customer['c_data'])[:500]
            values = [1, transaction['c_d_id'], customer['c_id'], 1,
                      transaction['d_id'], amount, w['w_name'] + '    ' + d['d_name']]
            expected['history'][normalized('history', values)] += 1
            result = {'success': True, 'c_id': customer['c_id'], 'amount': amount}
            outcomes['payment'] += 1
        assert log['result'] == result, (index, log['result'], result)
        if args.native:
            assert log['status'] == 200 and not log['rollback']
        else:
            assert log['categories'].get('transaction.commit') == 1
    for name, values in [('warehouse', warehouses), ('district', districts),
                         ('customer', customers), ('stock', stocks)]:
        expected[name] = Counter(project(name, value) for value in values.values())
    after_counts = compare(after_folder, expected, scoped=bool(args.profile_case))
    receipt = {'status': 'PASS', 'verifier_source_sha256': sha(Path(__file__)), 'scope': ('Independent seed-derived model; every request, retained affected-row snapshots in eight relations and complete global business counts' if args.profile_case else 'Independent seed-derived model; every request and all eight mutable business relations'),
               'requests_checked': len(logs), 'outcomes': dict(outcomes),
               'before_rows': before_counts, 'after_rows': after_counts,
               'money_comparison': 'Two decimal places, exact cents; raw precision retained in snapshots',
               'initial_history_projection': args.seed_projection,
               'input_layout': 'native HTTP' if args.native else 'Java JDBC',
               'input_check': 'All original logical fields and ordered line entries; additional graph UUID bindings permitted',
               'repeated_original_plan_index': args.repeat_index,
               'original_prefix_count': args.original_prefix,
               'plan_sha256': sha(HERE / 'tpcc-plan-900.json'),
               'seed_manifest_sha256': sha(SEEDS / 'manifest.json'),
               'request_log_sha256': sha(request_path)}
    (gate / 'independent-model-verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
