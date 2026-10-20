#!/usr/bin/env python3
"""Validate original littleX cohort/process recipe and compare historical results."""
import csv
import hashlib
import json
from pathlib import Path

from aggregate import HERE, expected_cells, read_history
from original_recipe import cohorts


def main():
    data = json.loads((HERE / 'original-recipe/latest.json').read_text())
    records = data['records']
    expected = {'_'.join(c) for c in expected_cells()}
    assert len(records) == 40 and {r['cell'] for r in records} == expected
    actual_order = [r['cell'] for r in records]
    required_order = ['_'.join((phase, tier, arm, op)) for arm in ('postgres', 'jaseci')
                      for phase, tier, ops in cohorts(arm) for op in ops]
    assert actual_order == required_order, 'Original operation/phase order differs'
    sql_pids = {r['server_pid'] for r in records if r['arm'] == 'postgres'}
    assert len(sql_pids) == 1, 'SQL server restarted across cohorts'
    cohorts_seen = {}
    history = read_history()
    rows = []
    for r in records:
        assert r['runtime_commit'].startswith('ad469c988'), 'Historical CONTROL source differs'
        assert r['app_sha256'] == '89366720a196c275712ccda73c2db06b17ea509c645a87c87ef84e5409821df0'
        for flag in ('JAC_STREAM_LATERAL', 'JAC_SQL_ACL', 'JAC_FUSED_FEED', 'JAC_STICKY_DENY'):
            assert r['jac_environment'][flag] == '1'
        assert r['jac_environment']['JAC_RO_WALKERS'] == ''
        assert 'JAC_LAZY_TXN' not in r['jac_environment'] and 'JAC_EDGE_ONLY_DIRTY' not in r['jac_environment']
        phase, tier, arm, op = (r[k] for k in ('phase', 'tier', 'arm', 'operation'))
        path = Path(r['results'])
        measured = list(csv.DictReader(path.open()))
        assert measured == r['rows']
        n = 1000 if phase == 'W3' else 500
        assert sum(int(v['requests']) for v in measured) == n
        assert sum(1 for _ in csv.DictReader((path.parent / 'raw.csv').open())) == n
        assert all(int(v.get('errors') or 0) == int(v.get('warmup_errors') or 0) == 0 for v in measured)
        assert r['extra_feed_requests_before_warmup'] == 0
        assert r['driver_cpu_affinity'] == list(range(20))
        if arm == 'postgres':
            assert r['server_cpu_affinity'] == list(range(6, 14))
            assert 'port=55436' in r['sql_dsn']
        else:
            proof = json.loads(Path(r['historical_validation']).read_text())
            assert proof['reset_after_validation']
            for key in ('full_log', 'page_log'):
                assert 'PARITY OK (100 passed, 0 failed)' in Path(proof[key]).read_text()
        provenance_path = Path(r['dependency_provenance'])
        assert hashlib.sha256(provenance_path.read_bytes()).hexdigest() == r['dependency_provenance_sha256']
        provenance = json.loads(provenance_path.read_text())
        assert r['driver_python'] == provenance['environments']['driver']['python']
        assert r['sql_python'] == provenance['environments']['sql']['python']
        group = cohorts_seen.setdefault(r['cohort'], [])
        group.append(r)
        assert r['initial_seed_counts'] == dict(tweets=100 * int(tier[1:]), follows=5000, likes=0)
        for evidence in r['prevalidation']:
            d = json.loads(Path(evidence).read_text())
            assert 'PARITY OK (100 passed, 0 failed)' in (Path(d['results']).parent / 'oracle.log').read_text()
        for v in measured:
            if v['workload'] in ('like', 'follow', 'create_tweet'):
                assert v['oracle_ok'] == 'True' and v['oracle_actual'] == v['oracle_expected']
                if phase == 'W2':
                    assert int(v['oracle_actual']) == 610
            elif phase == 'W1':
                assert int(v['warm_count']) == 110
            operation = 'feed' if v['workload'] == 'feed_chain' else v['workload']
            frac = op if phase == 'W3' else ''
            h = history[(phase, tier, arm, frac, operation)]
            rows.append(dict(phase=phase, tier=tier, arm=arm, fraction=frac, operation=operation,
                             server_p50_ms=float(v['server_p50_ms']), client_p50_ms=float(v['p50_ms']),
                             historical_server_p50_ms=float(h['server_p50_ms']),
                             original_server_p50_ms=float(h['server_p50_ms']), results=str(path)))
    assert len(cohorts_seen) == 24
    jac_pids = set()
    for path, group in cohorts_seen.items():
        assert len({r['server_pid'] for r in group}) == 1
        phase = group[0]['phase']
        if group[0]['arm'] == 'jaseci':
            jac_pids.add(group[0]['server_pid'])
        expected_post = group[0]['initial_seed_counts'].copy()
        for r in group:
            assert r['state_before_operation'] == expected_post
            for v in r['rows']:
                if v['workload'] in ('like', 'follow', 'create_tweet'):
                    key = {'like': 'likes', 'follow': 'follows', 'create_tweet': 'tweets'}[v['workload']]
                    expected_post[key] += int(v['oracle_actual'])
        assert json.loads((Path(path) / 'post-counts.json').read_text()) == expected_post
        if phase == 'W2':
            assert [r['operation'] for r in group] == ['like', 'follow', 'create_tweet']
    assert len(jac_pids) == 12, 'Jac fresh-process cohort boundaries differ'
    output = HERE / 'original-recipe/summary'
    output.mkdir(exist_ok=True)
    with (output / 'comparison.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    validation = dict(complete_cells=40, validated_cells=40, request_errors=0,
                      sql_server_processes=1, jac_server_processes=12, cohorts=24,
                      preserved_w2_shared_state=True, original_phase_order=True,
                      source_directory=data['directory'])
    (output / 'validation.json').write_text(json.dumps(validation, indent=2))
    report = ['# littleX original-recipe reproduction', '',
              '40/40cells passed.24cohorts; SQL uses one server process, Jac uses12fresh cohort processes.',
              'W2 preserves like→follow→create_tweet shared state. Each operation has110warm+500timed;',
              'W3 has110warm+1000timed. All count/write oracles and raw sample counts pass.',
              'Jac source and configuration:ad469c988 historical CONTROL, matching the original reference.',
              'SQL server affinity6-13; both drivers unpinned0-19; original SQL/driver frozen locks onPython3.13.', '',
              '| Phase | Tweets/user | Fraction | Operation | Jac CONTROL | SQL | CONTROL/SQL | Historical CONTROL/SQL |',
              '|---|---|---|---|---:|---:|---:|---:|']
    groups = {}
    for r in rows:
        groups.setdefault((r['phase'], r['tier'], r['fraction'], r['operation']), {})[r['arm']] = r
    for key, pair in sorted(groups.items()):
        j, p = pair['jaseci'], pair['postgres']
        report.append('| ' + ' | '.join(key) +
                      f' | {j["server_p50_ms"]:.3f} | {p["server_p50_ms"]:.3f} | {j["server_p50_ms"] / p["server_p50_ms"]:.2f}' +
                      f' | {j["historical_server_p50_ms"] / p["historical_server_p50_ms"]:.2f} |')
    (output / 'REPORT.md').write_text('\n'.join(report) + '\n')
    print(json.dumps(validation, indent=2))


if __name__ == '__main__':
    main()
