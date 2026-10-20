#!/usr/bin/env python3
"""Validate canonical40-cell littleX matrix and compare historical CONTROL/SQL."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
HISTORY = HERE.parents[1] / 'DBHarness/session0904/run/data'
TRUE = {'True', 'true', '1'}


def expected_cells():
    for phase in ('W1', 'W2', 'W3'):
        for tier in (('t20', 't50', 't100', 't200') if phase != 'W3' else ('t200',)):
            for arm in ('jaseci', 'postgres'):
                for op in (('feed',) if phase == 'W1' else
                           ('create_tweet', 'follow', 'like') if phase == 'W2' else ('0', '5', '15', '30')):
                    yield phase, tier, arm, op


def read_history():
    out = {}
    for folder, arm in [('littlex_control', 'jaseci'), ('littlex_baselines', 'postgres')]:
        for phase in ('W1', 'W2', 'W3'):
            with (HISTORY / folder / (phase.lower() + '_master.csv')).open() as f:
                for r in csv.DictReader(f):
                    if r['arm'] != ('jaseci-pg' if arm == 'jaseci' else 'postgres'):
                        continue
                    op = 'feed' if r['op'] == 'feed_chain' else r['op']
                    out[(phase, r['tier'], arm, r['frac'] if phase == 'W3' else '', op)] = r
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    history = read_history()
    errors, missing, summaries, rows = [], [], [], []
    for phase, tier, arm, op in expected_cells():
        cell = '_'.join((phase, tier, arm, op))
        marker = HERE / 'data' / cell / 'complete.json'
        if not marker.exists():
            missing.append(cell)
            continue
        d = json.loads(marker.read_text())
        problems = []
        if d.get('measurement_role', '').startswith('diagnostic'):
            problems.append('diagnostic artifact in canonical marker')
        result = Path(d['results'])
        work = result.parent
        with result.open() as f:
            measured = list(csv.DictReader(f))
        count = sum(int(r['requests']) for r in measured)
        if count != (1000 if phase == 'W3' else 500):
            problems.append(f'expected canonical sample count, got {count}')
        if measured != d['rows']:
            problems.append('CSV and completion metadata differ')
        if any(int(r.get('errors') or 0) or int(r.get('warmup_errors') or 0) for r in measured):
            problems.append('request errors')
        oracle = (work / 'oracle.log').read_text()
        if 'PARITY OK (100 passed, 0 failed)' not in oracle:
            problems.append('100-user seed-derived oracle missing')
        seed_counts = json.loads((work / 'seed-counts.json').read_text())
        expected_seed = dict(tweets=100 * int(tier[1:]), follows=5000, likes=0)
        if seed_counts != expected_seed:
            problems.append('seed counts mismatch')
        if phase == 'W1' and any(int(r.get('warm_count') or 0) != 110 for r in measured):
            problems.append('read warmup count differs from110')
        if phase == 'W2' and 'warmup_errors=0' not in (work / 'driver.log').read_text():
            problems.append('write warmup incomplete')
        for r in measured:
            if r['workload'] in ('create_tweet', 'follow', 'like'):
                if r.get('oracle_ok') not in TRUE:
                    problems.append('write-delta oracle failed')
                if int(r['oracle_actual']) != int(r['oracle_expected']):
                    problems.append('write delta differs')
                if phase == 'W2' and int(r['oracle_expected']) != 610:
                    problems.append('expected110warm+500timed writes')
        raw = list(csv.DictReader((work / 'raw.csv').open()))
        if len(raw) != count:
            problems.append(f'raw timing count {len(raw)} differs from {count}')
        if arm == 'postgres' and ('host=127.0.0.1' not in d['sql_dsn'] or 'port=55436' not in d['sql_dsn']):
            problems.append('SQL topology differs fromPG16/TCP55436')
        reset = d.get('reset', {})
        provenance_path = Path(d.get('dependency_provenance', str(HERE / 'missing-dependency-provenance')))
        if not provenance_path.exists() or hashlib.sha256(provenance_path.read_bytes()).hexdigest() != d.get('dependency_provenance_sha256'):
            problems.append('locked dependency provenance missing or changed')
        else:
            provenance = json.loads(provenance_path.read_text())
            for role, field in [('driver', 'driver_python'), ('sql', 'sql_python')]:
                if d.get(field) != provenance['environments'][role]['python']:
                    problems.append(role + ' interpreter differs from locked provenance')
        if arm == 'jaseci' and reset.get('fixture'):
            fixture = Path(reset['fixture'])
            if hashlib.sha256(fixture.read_bytes()).hexdigest() != reset['fixture_sha256']:
                problems.append('fixture metadata hash differs')
        summaries.append(dict(cell=cell, requests=count, checks_passed=not problems,
                              problems=problems, results=str(result), reset=reset))
        errors += [cell + ': ' + p for p in problems]
        for r in measured:
            operation = 'feed' if r['workload'] == 'feed_chain' else r['workload']
            frac = op if phase == 'W3' else ''
            h = history.get((phase, tier, arm, frac, operation))
            actual = float(r['server_p50_ms'])
            historical = float(h['server_p50_ms']) if h else None
            rows.append(dict(phase=phase, tier=tier, arm=arm, frac=frac, operation=operation,
                             requests=int(r['requests']), server_p50_ms=actual,
                             client_p50_ms=float(r['p50_ms']),
                             historical_server_p50_ms=historical,
                             current_over_historical=actual / historical if historical else None,
                             oracle_ok=r.get('oracle_ok', ''), results=str(result)))
    out = HERE / 'summary'
    out.mkdir(exist_ok=True)
    payload = dict(expected_cells=40, complete_cells=len(summaries),
                   validated_cells=sum(s['checks_passed'] for s in summaries),
                   missing=missing, errors=errors, cells=summaries, rows=rows)
    (out / 'validation.json').write_text(json.dumps(payload, indent=2))
    if rows:
        with (out / 'comparison.csv').open('w') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    report = ['# littleX canonical reproduction', '',
              f'Validated cells: {payload["validated_cells"]}/40; missing: {len(missing)}; errors: {len(errors)}.', '',
              'Current Jac: final32c5d1dbb defaults (LAZY_TXN on), Python3.14 PBS. Historical littleX reference: ad469c988 CONTROL.',
              'SQL app and HTTP driver: separate original locked dependencies on CPython3.13.16 PBS20261013.',
              'SQL topology: PostgreSQL16 Docker/TCP; Jac: native PostgreSQL18.',
              'Each cell checks seed counts,100-user seed-derived feed/page parity, request counts and errors.',
              'Write rows additionally check database-truth deltas. Latencies below are server p50 milliseconds.', '',
              '| Phase | Tweets/user | Fraction | Operation | Jac final defaults | SQL | Final/SQL | Historical CONTROL/SQL |',
              '|---|---|---|---|---:|---:|---:|---:|']
    groups = {}
    for r in rows:
        groups.setdefault((r['phase'], r['tier'], r['frac'], r['operation']), {})[r['arm']] = r
    for key, group in sorted(groups.items()):
        if 'jaseci' not in group or 'postgres' not in group:
            continue
        j, p = group['jaseci'], group['postgres']
        hj, hp = j['historical_server_p50_ms'], p['historical_server_p50_ms']
        old = f'{hj / hp:.2f}' if hj and hp else ''
        report.append('| ' + ' | '.join(key) + f' | {j["server_p50_ms"]:.3f} | {p["server_p50_ms"]:.3f} | {j["server_p50_ms"] / p["server_p50_ms"]:.2f} | {old} |')
    if errors:
        report += ['', 'Validation findings:', ''] + ['- ' + x for x in errors]
    if missing:
        report += ['', 'Pending cells:', ''] + ['- ' + x for x in missing]
    (out / 'REPORT.md').write_text('\n'.join(report) + '\n')
    print(json.dumps({k: payload[k] for k in ('expected_cells', 'complete_cells', 'validated_cells', 'errors')}, indent=2))
    if errors or (missing and not args.allow_incomplete):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
