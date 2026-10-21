#!/usr/bin/env python3
"""Freeze original pure workload generators and their actual outputs."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

HERE = Path(__file__).resolve().parent
REPRO = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pure_functions(path, names, namespace):
    tree = ast.parse(path.read_text())
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in functions} == set(names)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


def write(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def main():
    tpcc = REPRO / 'benchmark/scripts/tpcc_run.py'
    namespace = pure_functions(tpcc, ['c_last', 'build_plan'], {
        'random': random, 'PLAN_SEED': 4242,
        'SYLL': ['BAR', 'OUGHT', 'ABLE', 'PRI', 'PRES',
                 'ESE', 'ANTI', 'CALLY', 'ATION', 'EING']})
    plan = namespace['build_plan'](900)
    def totals(rows):
        count = Counter('rollback' if row.get('invalid') else row['kind'] for row in rows)
        return {'requests': len(rows), **count,
                'order_lines': sum(len(row['lines']) for row in rows
                                   if row['kind'] == 'new_order' and not row['invalid']),
                'payment_amount': round(sum(row['amount'] for row in rows
                                            if row['kind'] == 'payment'), 2)}
    expected = totals(plan)
    assert (expected['new_order'], expected['payment'], expected['rollback']) == (487, 406, 7)
    assert expected['order_lines'] == 4746 and expected['payment_amount'] == 1062049.86
    write(HERE / 'tpcc-plan-900.json', plan)
    mix_source = REPRO / 'littlex/harness/mix_run.py'
    schedule_fn = pure_functions(mix_source, ['build_schedule'], {})['build_schedule']
    schedules = {str(frac): schedule_fn(frac) for frac in (0, 5, 15, 30)}
    write(HERE / 'littlex-schedules.json', schedules)
    source_paths = [tpcc, mix_source, REPRO / 'scripts/tpcc_gate.py',
                    REPRO / 'benchmark/tpcc/data/manifest.json',
                    REPRO / 'benchmark/tpcc/jaseci-pg/app.jac',
                    REPRO / 'benchmark/tpcc/postgres/app.py',
                    REPRO / 'littlex/harness/write_run.py',
                    REPRO / 'littlex/harness/oracle.py',
                    REPRO / 'littlex/postgres/app.py',
                    REPRO / 'littlex/historical-app-source/app.jac']
    write(HERE / 'workload-contracts.json', {
        'source_sha256': {str(path.relative_to(REPRO)): sha(path) for path in source_paths},
        'tpcc': {'seed': 4242, 'warmup': totals(plan[:100]), 'measured': totals(plan[100:]),
                 'all_requests': expected,
                 'canonical_plan_sha256': hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(),
                 'plan_file_sha256': sha(HERE / 'tpcc-plan-900.json')},
        'littlex': {'schedule_slots': 100,
                    'counts_per_100': {key: dict(Counter(value)) for key, value in schedules.items()},
                    'schedule_file_sha256': sha(HERE / 'littlex-schedules.json'),
                    'profiles': 100, 'initial_follows': 5000,
                    'tiers': {str(tier): {'tweets_per_user': tier, 'tweets': tier * 100,
                                        'full_feed_per_user': tier * 51} for tier in (20, 50, 100, 200)}}})
    print(json.dumps({'tpcc': expected, 'littlex_schedule_fractions': list(schedules)}, sort_keys=True))


if __name__ == '__main__':
    main()
