#!/usr/bin/env python3
"""Independently verify frozen inputs against the original workload sources."""
import hashlib
import json
from pathlib import Path
import random
from freeze_contracts import pure_functions

HERE = Path(__file__).resolve().parent
REPRO = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    contracts = json.loads((HERE / 'workload-contracts.json').read_text())
    for name, expected in contracts['source_sha256'].items():
        assert digest(REPRO / name) == expected, name
    original = REPRO / 'benchmark/scripts/tpcc_run.py'
    ns = pure_functions(original, ['c_last', 'build_plan'], {
        'random': random, 'PLAN_SEED': 4242,
        'SYLL': ['BAR', 'OUGHT', 'ABLE', 'PRI', 'PRES',
                 'ESE', 'ANTI', 'CALLY', 'ATION', 'EING']})
    plan = json.loads((HERE / 'tpcc-plan-900.json').read_text())
    assert ns['build_plan'](900) == plan
    assert digest(HERE / 'tpcc-plan-900.json') == contracts['tpcc']['plan_file_sha256']
    representatives_path = HERE / 'tpcc/representatives.json'
    representative_count = 0
    if representatives_path.exists():
        representatives = json.loads(representatives_path.read_text())
        for label, case in representatives.items():
            expected = plan[case['original_index']]
            actual = case['input']
            assert all(actual.get(key) == value for key, value in expected.items()), label
        representative_count = len(representatives)
    source = REPRO / 'littlex/harness/mix_run.py'
    fn = pure_functions(source, ['build_schedule'], {})['build_schedule']
    schedules = json.loads((HERE / 'littlex-schedules.json').read_text())
    for fraction, slots in schedules.items():
        assert slots == fn(int(fraction))
    assert digest(HERE / 'littlex-schedules.json') == contracts['littlex']['schedule_file_sha256']
    tiers = {}
    for tier, expected in contracts['littlex']['tiers'].items():
        seed_name = 'uniform' if tier == '50' else 't' + tier
        seed = json.loads((REPRO / f'littlex/dataset/{seed_name}_seed.json').read_text())
        assert len(seed['profiles']) == 100
        assert len(seed['tweets']) == expected['tweets']
        assert len(seed['follows']) == 5000
        authors = {profile['id']: {profile['id']} for profile in seed['profiles']}
        for edge in seed['follows']:
            authors[edge['follower']].add(edge['followee'])
        counts = {user: sum(tweet['author'] in followed for tweet in seed['tweets'])
                  for user, followed in authors.items()}
        assert set(counts.values()) == {expected['full_feed_per_user']}
        tiers[tier] = {'users_checked': len(counts), 'feed_rows': expected['full_feed_per_user']}
    receipt = {'status': 'PASS', 'scope': 'Original source and deterministic input contracts',
               'source_hashes_checked': len(contracts['source_sha256']),
               'tpcc_plan_requests': len(plan), 'tpcc_representatives_checked': representative_count,
               'littlex_schedules_checked': len(schedules), 'littlex_tiers': tiers}
    (HERE / 'workload-contracts-verified.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
