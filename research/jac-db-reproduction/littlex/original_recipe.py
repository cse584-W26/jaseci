#!/usr/bin/env python3
"""Run the original littleX cohort/order/process recipe with frozen baselines."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

import run as lx


def seed_path(tier):
    return lx.HERE / 'dataset' / (('uniform' if tier == 't50' else tier) + '_seed.json')


def cohorts(arm):
    tiers = ['t20', 't50', 't100', 't200']
    phases = ['W2', 'W3', 'W1'] if arm == 'postgres' else ['W3', 'W1', 'W2']
    for phase in phases:
        if phase == 'W3':
            for frac in ('0', '5', '15', '30'):
                yield phase, 't200', [frac]
        else:
            for tier in tiers:
                yield phase, tier, ['like', 'follow', 'create_tweet'] if phase == 'W2' else ['feed']


def metadata_affinity(p):
    return dict(server_pid=p.pid, server_cpu_affinity=sorted(os.sched_getaffinity(p.pid)),
                driver_cpu_affinity=sorted(os.sched_getaffinity(0)))


def validate_historical_fixture(tier, seed, env):
    """Validate old-runtime auth/full/page semantics, then caller restores again."""
    app, tokens, reset = lx.fixture(tier, seed, env)
    folder = Path(reset['fixture']).parent
    proof = folder / 'historical-validation.json'
    if proof.exists():
        prior = json.loads(proof.read_text())
        if prior['fixture_sha256'] != reset['fixture_sha256']:
            raise RuntimeError('Historical validation fixture changed')
        return str(proof)
    e = dict(env, JAC_PG_APP_DIR=str(app))
    p = None
    try:
        p = lx.launch([lx.BIN, 'start', 'main.jac', '-p', '18120', '--no-client'],
                      app, e, folder / 'validation-server.log', 18120, '/healthz')
        base = [lx.DRIVER_PYTHON, lx.HERE / 'harness/oracle.py', '--engines', 'jaseci',
                '--tokens-dir', tokens, '--seed', seed, '--url-jaseci', 'http://127.0.0.1:18120']
        lx.command([*base, '--walker', 'load_feed_chain'], e, log=folder / 'validation-full.log')
        lx.command([*base, '--page'], e, log=folder / 'validation-page.log')
    finally:
        lx.stop(p)
    proof.write_text(json.dumps(dict(fixture_sha256=reset['fixture_sha256'],
                                    full_feed_users=100, top20_users=100,
                                    full_log=str(folder / 'validation-full.log'),
                                    page_log=str(folder / 'validation-page.log'),
                                    reset_after_validation=True), indent=2))
    return str(proof)


def run_suite(arms):
    import psycopg
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = lx.HERE / 'original-recipe' / run_id
    output.mkdir(parents=True)
    records = []
    historical_proofs = {}
    env_base = lx.environment()
    # Historical CONTROL: the original caller supplied these before start_pg.sh.
    env_base.update(PERF='1', JAC_STREAM_LATERAL='1', JAC_SQL_ACL='1',
                    JAC_FUSED_FEED='1', JAC_STICKY_DENY='1', JAC_RO_WALKERS='')
    env_base.pop('JAC_LAZY_TXN', None)
    env_base.pop('JAC_EDGE_ONLY_DIRTY', None)
    runtime_commit = subprocess.check_output(['git', '-C', str(lx.SOURCE), 'rev-parse', 'HEAD'], text=True).strip()

    def persist():
        (output / 'progress.json').write_text(json.dumps(records, indent=2))

    for arm in arms:
        server = None
        env = env_base.copy()
        try:
            if arm == 'postgres':
                with psycopg.connect(lx.SQL_ADMIN_DSN, autocommit=True) as conn:
                    if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s', (lx.SQL_DB,)).fetchone():
                        conn.execute('CREATE DATABASE ' + lx.SQL_DB)
                server = lx.launch(['taskset', '-c', lx.SQL_APP_CORES, lx.SQL_PYTHON,
                                    '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '18121',
                                    '--no-access-log'], lx.HERE / 'postgres', env,
                                   output / 'postgres-server.log', 18121, '/docs')
            for phase, tier, operations in cohorts(arm):
                label = '_'.join((arm, phase, tier, operations[0] if phase == 'W3' else 'cohort'))
                folder = output / label
                folder.mkdir()
                tokens = folder / 'tokens'
                tokens.mkdir()
                seed = seed_path(tier)
                references = []
                for op in operations:
                    reference = lx.HERE / 'data' / '_'.join((phase, tier, arm, op)) / 'complete.json'
                    prior = json.loads(reference.read_text())
                    if not (Path(prior['results']).parent / 'oracle.log').exists():
                        raise RuntimeError('Missing independent prevalidation evidence: ' + str(reference))
                    references.append(str(reference))
                if arm == 'jaseci':
                    if tier not in historical_proofs:
                        historical_proofs[tier] = validate_historical_fixture(tier, seed, env)
                    historical_proof = historical_proofs[tier]
                    # Original PG wrapper restarts per W3fraction/W1tier/W2tier.
                    app, fixture_tokens, reset = lx.fixture(tier, seed, env)
                    env = dict(env_base, JAC_PG_APP_DIR=str(app))
                    lx.shutil.copytree(fixture_tokens, tokens, dirs_exist_ok=True)
                    server = lx.launch([lx.BIN, 'start', 'main.jac', '-p', '18120', '--no-client'],
                                       app, env, folder / 'server.log', 18120, '/healthz')
                else:
                    # Original SQL server stays alive across every reset and phase.
                    app = lx.HERE / 'postgres'
                    reset = dict(method='original SQL TRUNCATE/reload; persistent server process')
                    lx.command([lx.SQL_PYTHON, app / 'loader.py', seed], env, log=folder / 'seed.log')
                    for script, target in [('mint_tokens.py', 'tokens.postgres.json'),
                                           ('export_targets.py', 'targets.postgres.json')]:
                        lx.command([lx.DRIVER_PYTHON, lx.HERE / 'harness' / script, '--engine', 'postgres',
                                    '--output', tokens / target], env, log=folder / (script + '.log'))
                try:
                    initial = lx.counts(arm, app, env)
                    expected = dict(tweets=100 * int(tier[1:]), follows=5000, likes=0)
                    if initial != expected:
                        raise RuntimeError(f'Initial cohort count mismatch: {initial} vs {expected}')
                    (folder / 'seed-counts.json').write_text(json.dumps(initial, indent=2))
                    affinity = metadata_affinity(server)
                    if arm == 'postgres' and affinity['server_cpu_affinity'] != list(range(6, 14)):
                        raise RuntimeError('SQL affinity differs from original6-13')
                    common = ['--engines', arm, '--tokens-dir', tokens, '--url-' + arm,
                              'http://127.0.0.1:' + ('18120' if arm == 'jaseci' else '18121')]
                    state = initial.copy()
                    for op in operations:
                        # No reset/restart between W2operations: like→follow→create_tweet.
                        result_dir = folder / op
                        result_dir.mkdir()
                        script = 'run.py' if phase == 'W1' else 'write_run.py' if phase == 'W2' else 'mix_run.py'
                        extra = (['--workloads', 'feed_chain' if arm == 'jaseci' else 'feed'] if phase == 'W1' else
                                 ['--ops', op, '--seed', seed] if phase == 'W2' else ['--write-frac', op, '--seed', seed])
                        n = 1000 if phase == 'W3' else 500
                        csv_path = result_dir / 'results.csv'
                        lx.command([lx.DRIVER_PYTHON, lx.HERE / 'harness' / script, *common, *extra,
                                    '--requests', n, '--warmup', '110', '--output', csv_path,
                                    '--raw-csv', result_dir / 'raw.csv'], env, log=result_dir / 'driver.log')
                        measured = list(csv.DictReader(csv_path.open()))
                        raw_count = sum(1 for _ in csv.DictReader((result_dir / 'raw.csv').open()))
                        if not measured or sum(int(r['requests']) for r in measured) != n or raw_count != n:
                            raise RuntimeError('Incomplete samples: ' + str(csv_path))
                        for row in measured:
                            if int(row.get('errors') or 0) or int(row.get('warmup_errors') or 0):
                                raise RuntimeError('Request errors: ' + str(csv_path))
                            if row['workload'] in ('like', 'follow', 'create_tweet'):
                                if row.get('oracle_ok') != 'True' or row['oracle_expected'] != row['oracle_actual']:
                                    raise RuntimeError('Write-delta oracle failed: ' + str(csv_path))
                            if phase == 'W1' and int(row['warm_count']) != 110:
                                raise RuntimeError('Wrong read warmup count')
                        if phase == 'W2' and 'warmup_errors=0' not in (result_dir / 'driver.log').read_text():
                            raise RuntimeError('Incomplete write warmup')
                        record = dict(cell='_'.join((phase, tier, arm, op)), phase=phase, tier=tier,
                                      arm=arm, operation=op, rows=measured, results=str(csv_path),
                                      cohort=str(folder), reset=reset, initial_seed_counts=initial,
                                      state_before_operation=state.copy(), **affinity,
                                      prevalidation=references, extra_feed_requests_before_warmup=0,
                                      historical_validation=historical_proof if arm == 'jaseci' else None,
                                      sql_dsn=env['DATABASE_URL'], sql_python=str(lx.SQL_PYTHON),
                                      driver_python=str(lx.DRIVER_PYTHON),
                                      dependency_provenance=str(lx.ROOT / 'runtime/littlex-lock-provenance.json'),
                                      dependency_provenance_sha256=hashlib.sha256((lx.ROOT / 'runtime/littlex-lock-provenance.json').read_bytes()).hexdigest(),
                                      runtime_commit=runtime_commit, runtime_source=str(lx.SOURCE),
                                      binary=str(lx.BIN), binary_sha256=hashlib.sha256(lx.BIN.read_bytes()).hexdigest(),
                                      jac_environment={k: v for k, v in env.items() if k.startswith('JAC_') or k == 'PERF'},
                                      app_source=str(lx.APP_SOURCE),
                                      app_sha256=hashlib.sha256((lx.APP_SOURCE / 'app.jac').read_bytes()).hexdigest())
                        records.append(record)
                        persist()
                        for row in measured:
                            if row['workload'] in ('like', 'follow', 'create_tweet'):
                                key = {'like': 'likes', 'follow': 'follows', 'create_tweet': 'tweets'}[row['workload']]
                                state[key] += int(row['oracle_actual'])
                        print(f'PASS original-recipe {len(records)}/40 {record["cell"]}', flush=True)
                    # Independent post-cohort truth check, outside every timed span.
                    actual = lx.counts(arm, app, env)
                    if actual != state:
                        raise RuntimeError(f'Post-cohort truth mismatch: {actual} vs {state}')
                    (folder / 'post-counts.json').write_text(json.dumps(actual, indent=2))
                finally:
                    if arm == 'jaseci':
                        lx.stop(server)
                        server = None
        finally:
            lx.stop(server)
    expected_cells = 20 * len(arms)
    if len(records) != expected_cells:
        raise RuntimeError(f'Expected{expected_cells}cells, got{len(records)}')
    summary = dict(run_id=run_id, complete_cells=len(records), arms=arms,
                   recipe='original process/cohort/order boundaries; historical CONTROL environment',
                   records=records, directory=str(output))
    (output / 'complete.json').write_text(json.dumps(summary, indent=2))
    if len(arms) == 2:
        (lx.HERE / 'original-recipe/latest.json').write_text(json.dumps(summary, indent=2))
    print('Original recipe complete: ' + str(output), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--arms', default='postgres,jaseci')
    args = parser.parse_args()
    arms = args.arms.split(',')
    if set(arms) - {'postgres', 'jaseci'}:
        parser.error('Supported arms: postgres,jaseci')
    if args.run:
        with lx.fixture_lock():
            run_suite(arms)
    else:
        print(json.dumps({a: list(cohorts(a)) for a in arms}, indent=2))
