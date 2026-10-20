#!/usr/bin/env python3
"""Isolated littleX Jac/SQL reproduction using unchanged colleague drivers.

Preparation and plan inspection never launch services. `--run` explicitly
executes the matrix; each cell gets a fresh database/application and tokens.
"""
import argparse
from contextlib import contextmanager
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parent / "DBHarness"
APP_SOURCE = Path(os.environ.get('LITTLEX_APP_SOURCE', str(REPO / 'littleXs/jaseci-pg'))).absolute()
SOURCE = Path(os.environ.get('LITTLEX_RUNTIME_SOURCE', str(ROOT.parent / "jac-db/jac"))).absolute()
BIN = Path(os.environ.get('LITTLEX_JAC_BIN', str(ROOT / "runtime/bin/jac"))).resolve()
PYTHON = Path(os.environ.get('LITTLEX_PYTHON', str(ROOT / "runtime/venv/bin/python"))).absolute()
SQL_PYTHON = Path(os.environ.get('LITTLEX_SQL_PYTHON', str(ROOT / 'runtime/venv-littlex-sql-locked/bin/python'))).absolute()
DRIVER_PYTHON = Path(os.environ.get('LITTLEX_DRIVER_PYTHON', str(ROOT / 'runtime/venv-littlex-driver-locked/bin/python'))).absolute()
CACHE = ROOT / "dbcache"
SOCK = Path('/tmp') / ('jacpg-' + hashlib.sha1(str(CACHE / 'pg/main').encode()).hexdigest()[:10])
SQL_DB = "littlex_reproduction_sql"
SQL_APP_CORES = os.environ.get('LITTLEX_SQL_APP_CORES', '6-13')
SQL_ADMIN_DSN = os.environ.get('LITTLEX_SQL_ADMIN_DSN', 'postgresql://postgres@127.0.0.1:55436/littleX')


def prepare():
    (HERE / "data").mkdir(parents=True, exist_ok=True)
    # Copy the entire Python harness so imports and token defaults remain local.
    shutil.copytree(REPO / "harness", HERE / "harness", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("tokens*", ".venv", ".run", "results", "__pycache__"))
    shutil.copytree(REPO / "littleXs/postgres", HERE / "postgres", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".venv", "__pycache__"))
    shutil.copytree(REPO / "dataset", HERE / "dataset", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("*_seed.json", "__pycache__"))


def environment():
    from psycopg.conninfo import make_conninfo
    e = os.environ.copy()
    for key in list(e):
        if key.startswith('JAC_') or key in ('FEED_WALKER', 'BASELINE_FEED'):
            e.pop(key)
    e.update(PYTHONUNBUFFERED='1', JAC_CACHE_HOME=str(CACHE), JAC_PG_VERSION='18',
             JAC_PG_DIST='/home/baichuan/.cache/jac/pg/dist/linux-amd64-18.6.0',
             JAC_API_LEAN_RESPONSE='1', JAC_ACCESS_LOG='0', JAC_REPORT_ECHO='0',
             JAC_TIMING_HEADERS='1', JAC_PG_POOL='1', JAC_PG_ENSURE_CACHE='1',
             JAC_PG_DRIVER='psycopg', JAC_PG_ARM='1', JAC_PG_BIN=str(BIN),
             DATABASE_URL=make_conninfo(SQL_ADMIN_DSN, dbname=SQL_DB),
             GLIBC_TUNABLES='glibc.rtld.execstack=2')
    return e


def command(args, env, cwd=HERE, log=None):
    args = [str(a) for a in args]
    if log:
        with Path(log).open('w') as f:
            subprocess.run(args, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
    else:
        subprocess.run(args, cwd=cwd, env=env, check=True)


def launch(args, cwd, env, log, port, route):
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError(f'Port {port} already occupied; existing process left untouched')
    with log.open('w') as f:
        p = subprocess.Popen([str(a) for a in args], cwd=cwd, env=env,
                             stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
    (log.parent / 'server.pid').write_text(str(p.pid))
    for _ in range(240):
        if p.poll() is not None:
            raise RuntimeError(f'Server exited {p.returncode}: {log}')
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}{route}', timeout=2) as r:
                if r.status == 200:
                    return p
        except Exception:
            pass
        time.sleep(1)
    stop(p)
    raise RuntimeError(f'Server readiness timeout: {log}')


def stop(p):
    if p is None or p.poll() is not None:
        return
    os.killpg(p.pid, signal.SIGTERM)
    try:
        p.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.wait()


def matrix(arms, tiers, phases):
    for phase in phases:
        for tier in (tiers if phase != 'W3' else ['t200']):
            for arm in arms:
                for op in (['feed'] if phase == 'W1' else
                           ['create_tweet', 'follow', 'like'] if phase == 'W2' else ['0', '5', '15', '30']):
                    yield phase, tier, arm, op


def counts(arm, app, env):
    # Reuse the colleague's before/after DB-truth counters outside timed spans.
    code = 'import json; from write_run import COUNTERS; print(json.dumps(COUNTERS[' + repr(arm) + ']()))'
    p = subprocess.run([str(DRIVER_PYTHON), '-c', code], cwd=HERE / 'harness', env=env,
                       text=True, capture_output=True, check=True)
    return json.loads(p.stdout.strip().splitlines()[-1])


def copy_app(destination, project_name=None):
    shutil.copytree(APP_SOURCE, destination,
                    ignore=shutil.ignore_patterns('.jac', '__pycache__'))
    import re
    manifest = (destination / 'jac.toml').read_text()
    manifest = re.sub(r'jaclang_source = ".*?"', f'jaclang_source = "{SOURCE}"', manifest)
    if project_name:
        manifest = re.sub(r'(?m)^name = ".*?"', f'name = "{project_name}"', manifest)
    (destination / 'jac.toml').write_text(manifest)


@contextmanager
def fixture_lock():
    import fcntl
    folder = HERE / 'fixtures'
    folder.mkdir(exist_ok=True)
    with (folder / '.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def fixture(tier, seed, env):
    """Seed once, then clone only owned DBs while every application is stopped."""
    import psycopg
    from psycopg import sql
    app_sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(APP_SOURCE.glob('*.jac'))}
    basis = dict(seed_sha256=hashlib.sha256(seed.read_bytes()).hexdigest(),
                 app_sources=app_sources,
                 manifest_sha256=hashlib.sha256((APP_SOURCE / 'jac.toml').read_bytes()).hexdigest(),
                 seed_driver_sha256=hashlib.sha256((HERE / 'harness/seed_jac.py').read_bytes()).hexdigest(),
                 binary_sha256=hashlib.sha256(BIN.read_bytes()).hexdigest(),
                 runtime_commit=subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip())
    digest = hashlib.sha256(json.dumps(basis, sort_keys=True).encode()).hexdigest()[:12]
    folder = HERE / 'fixtures' / tier / digest
    folder.mkdir(parents=True, exist_ok=True)
    app = folder / 'app'
    tokens = folder / 'tokens'
    metadata = folder / 'fixture.json'
    project = 'lx_repro_fixture_' + tier
    database = 'jac_' + project + '_' + hashlib.sha1(str(app.absolute()).encode()).hexdigest()[:8]
    snapshot = 'lx_repro_snapshot_' + tier + '_' + digest
    # Exact computed project DB is the only DB this helper can drop.
    assert app.is_relative_to(HERE / 'fixtures')
    assert database.startswith('jac_lx_repro_fixture_')
    assert snapshot.startswith('lx_repro_snapshot_')
    env = dict(env, JAC_PG_APP_DIR=str(app))

    def clone(conn, target, source):
        for db in (target, source):
            sessions = conn.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=%s', (db,)).fetchone()[0]
            if sessions:
                raise RuntimeError(f'Fixture database {db} has {sessions} active connections; stop its app first')
        conn.execute(sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(sql.Identifier(target), sql.Identifier(source)))

    with psycopg.connect(f'host={SOCK} user=jac dbname=postgres', autocommit=True) as admin:
        if not metadata.exists():
            if app.exists():
                raise RuntimeError(f'Incomplete fixture {folder}; inspect before reusing it')
            copy_app(app, project)
            tokens.mkdir()
            p = None
            try:
                p = launch([BIN, 'start', 'main.jac', '-p', '18120', '--no-client'], app, env,
                           folder / 'seed-server.log', 18120, '/healthz')
                command([DRIVER_PYTHON, HERE / 'harness/seed_jac.py', '--base-url', 'http://127.0.0.1:18120',
                         '--seed', seed, '--tokens-dir', tokens], env, log=folder / 'seed.log')
                seeded_counts = counts('jaseci', app, env)
                data = json.loads(seed.read_text())
                expected = dict(tweets=len(data['tweets']), follows=len(data['follows']), likes=0)
                if seeded_counts != expected:
                    raise RuntimeError(f'Fixture count mismatch {seeded_counts} vs {expected}')
            finally:
                stop(p)
            # Fresh source DB naming also proves the app used the intended manifest/path.
            if not admin.execute('SELECT 1 FROM pg_database WHERE datname=%s', (database,)).fetchone():
                raise RuntimeError(f'App database name mismatch: expected {database}')
            clone(admin, snapshot, database)
            admin.execute(sql.SQL('ALTER DATABASE {} ALLOW_CONNECTIONS false').format(sql.Identifier(snapshot)))
            token_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(tokens.glob('*.json'))}
            metadata.write_text(json.dumps(dict(**basis, database=database, snapshot=snapshot,
                                                seed_counts=seeded_counts, token_hashes=token_hashes), indent=2))
        saved = json.loads(metadata.read_text())
        for key, value in basis.items():
            if saved.get(key) != value:
                raise RuntimeError(f'Fixture provenance mismatch: {key}')
        for name, digest in saved['token_hashes'].items():
            if hashlib.sha256((tokens / name).read_bytes()).hexdigest() != digest:
                raise RuntimeError(f'Fixture token map changed: {name}')
        snapshot_state = admin.execute('SELECT datallowconn FROM pg_database WHERE datname=%s', (snapshot,)).fetchone()
        if snapshot_state is None or snapshot_state[0]:
            raise RuntimeError(f'Fixture snapshot missing or allows client connections: {snapshot}')
        if admin.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=%s', (database,)).fetchone()[0]:
            raise RuntimeError(f'Fixture app still connected to {database}')
        admin.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(database)))
        clone(admin, database, snapshot)
    return app, tokens, dict(method='PostgreSQL CREATE DATABASE TEMPLATE restore',
                             fixture=str(metadata), database=database, snapshot=snapshot,
                             fixture_sha256=hashlib.sha256(metadata.read_bytes()).hexdigest())


def cell(spec, args):
    phase, tier, arm, op = spec
    name = '_'.join(spec)
    cell_dir = HERE / 'data' / name
    cell_dir.mkdir(parents=True, exist_ok=True)
    done = cell_dir / 'complete.json'
    if done.exists() and not args.rerun:
        print(f'SKIP {name}', flush=True)
        return
    # A fresh namespace on retry preserves previous data and avoids dropping DBs.
    attempt = 1
    while (cell_dir / f'attempt-{attempt}').exists():
        attempt += 1
    work = cell_dir / f'attempt-{attempt}'
    work.mkdir()
    tokens = work / 'tokens'
    tokens.mkdir()
    seed = HERE / 'dataset' / (('uniform' if tier == 't50' else tier) + '_seed.json')
    e = environment()
    app = work / 'app'
    reset = dict(method='fresh application directory and original HTTP seed')
    p = None
    try:
        if arm == 'jaseci':
            if args.reuse_fixtures:
                app, fixture_tokens, reset = fixture(tier, seed, e)
                shutil.copytree(fixture_tokens, tokens, dirs_exist_ok=True)
            else:
                copy_app(app)
            e['JAC_PG_APP_DIR'] = str(app)
            p = launch([BIN, 'start', 'main.jac', '-p', '18120', '--no-client'], app, e,
                       work / 'server.log', 18120, '/healthz')
            if not args.reuse_fixtures:
                command([DRIVER_PYTHON, HERE / 'harness/seed_jac.py', '--base-url', 'http://127.0.0.1:18120',
                         '--seed', seed, '--tokens-dir', tokens], e, log=work / 'seed.log')
        else:
            reset = dict(method='original hand-SQL loader TRUNCATE and reload')
            import psycopg
            with psycopg.connect(SQL_ADMIN_DSN, autocommit=True) as c:
                if not c.execute('SELECT 1 FROM pg_database WHERE datname=%s', (SQL_DB,)).fetchone():
                    c.execute('CREATE DATABASE ' + SQL_DB)
            command([SQL_PYTHON, HERE / 'postgres/loader.py', seed], e, log=work / 'seed.log')
            for script, output in [('mint_tokens.py', 'tokens.postgres.json'),
                                   ('export_targets.py', 'targets.postgres.json')]:
                command([DRIVER_PYTHON, HERE / 'harness' / script, '--engine', 'postgres', '--output', tokens / output], e)
            p = launch(['taskset', '-c', SQL_APP_CORES, SQL_PYTHON, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '18121',
                        '--no-access-log'], HERE / 'postgres', e, work / 'server.log', 18121, '/docs')
        affinity = dict(server_cpu_affinity=sorted(os.sched_getaffinity(p.pid)),
                        driver_cpu_affinity=sorted(os.sched_getaffinity(0)),
                        sql_app_cores=SQL_APP_CORES if arm == 'postgres' else None)
        (work / 'affinity.json').write_text(json.dumps(affinity, indent=2))
        got = counts(arm, app, e)
        source_seed = json.loads(seed.read_text())
        expected = dict(tweets=len(source_seed['tweets']), follows=len(source_seed['follows']), likes=0)
        if got != expected:
            raise RuntimeError(f'Seed count mismatch {got} vs {expected}')
        (work / 'seed-counts.json').write_text(json.dumps(got, indent=2))
        common = ['--engines', arm, '--tokens-dir', tokens,
                  '--url-' + arm, 'http://127.0.0.1:' + ('18120' if arm == 'jaseci' else '18121')]
        # Gate feed semantics against independent seed-derived expectations.
        oracle = [DRIVER_PYTHON, HERE / 'harness/oracle.py', *common, '--seed', seed]
        if phase != 'W1':
            oracle += ['--page']
        elif arm == 'jaseci':
            oracle += ['--walker', 'load_feed_chain']
        command(oracle, e, log=work / 'oracle.log')
        script = 'run.py' if phase == 'W1' else 'write_run.py' if phase == 'W2' else 'mix_run.py'
        extra = (['--workloads', 'feed_chain' if arm == 'jaseci' else 'feed'] if phase == 'W1' else
                 ['--ops', op, '--seed', seed] if phase == 'W2' else ['--write-frac', op, '--seed', seed])
        n = args.requests or (1000 if phase == 'W3' else 500)
        output = work / 'results.csv'
        command([DRIVER_PYTHON, HERE / 'harness' / script, *common, *extra, '--requests', n,
                 '--warmup', args.warmup, '--output', output, '--raw-csv', work / 'raw.csv'],
                e, log=work / 'driver.log')
        rows = list(csv.DictReader(output.open()))
        if (not rows or any(int(r.get('errors', 0)) or int(r.get('warmup_errors', 0))
                            or r.get('oracle_ok', 'True') not in ('', 'True', '1') for r in rows)
                or sum(int(r['requests']) for r in rows) != n):
            raise RuntimeError(f'Request/oracle failure: {output}')
        if phase == 'W2' and 'warmup_errors=0' not in (work / 'driver.log').read_text():
            raise RuntimeError(f'Write warmup incomplete: {work / "driver.log"}')
        result = dict(cell=name, phase=phase, tier=tier, arm=arm, operation=op,
                      runtime_commit='32c5d1dbb9507571235783e78e35b1022cacc4e4',
                      binary=str(BIN), binary_sha256=hashlib.sha256(BIN.read_bytes()).hexdigest(),
                      sql_dsn=e['DATABASE_URL'],
                      sql_python=str(SQL_PYTHON), driver_python=str(DRIVER_PYTHON),
                      sql_lock_sha256=hashlib.sha256((REPO / 'littleXs/postgres/uv.lock').read_bytes()).hexdigest(),
                      driver_lock_sha256=hashlib.sha256((REPO / 'harness/uv.lock').read_bytes()).hexdigest(),
                      dependency_provenance=str(ROOT / 'runtime/littlex-lock-provenance.json'),
                      dependency_provenance_sha256=hashlib.sha256((ROOT / 'runtime/littlex-lock-provenance.json').read_bytes()).hexdigest(),
                      **affinity,
                      reset=reset,
                      app_sha256=hashlib.sha256((REPO / 'littleXs/jaseci-pg/app.jac').read_bytes()).hexdigest(),
                      results=str(output), rows=rows)
        done.write_text(json.dumps(result, indent=2))
        print('PASS ' + name, flush=True)
    finally:
        stop(p)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--arms', default='jaseci,postgres')
    parser.add_argument('--tiers', default='t20,t50,t100,t200')
    parser.add_argument('--phases', default='W1,W2,W3')
    parser.add_argument('--requests', type=int, default=0)
    parser.add_argument('--warmup', type=int, default=110)
    parser.add_argument('--rerun', action='store_true')
    parser.add_argument('--reuse-fixtures', action='store_true',
                        help='Seed each Jac tier once, restore its owned project DB from a template per cell')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    arms, tiers, phases = [x.split(',') for x in (args.arms, args.tiers, args.phases)]
    if set(arms) - {'jaseci', 'postgres'} or set(tiers) - {'t20', 't50', 't100', 't200'} or set(phases) - {'W1', 'W2', 'W3'}:
        parser.error('Unknown arm, tier, or phase')
    plan = list(matrix(arms, tiers, phases))
    print(json.dumps(dict(cells=len(plan), plan=plan), indent=2), flush=True)
    if args.run:
        for tier in tiers + (['t200'] if 'W3' in phases else []):
            profile = 'uniform' if tier == 't50' else tier
            seed = HERE / 'dataset' / (profile + '_seed.json')
            if not seed.exists():
                command([DRIVER_PYTHON, HERE / 'dataset/generate.py', '--profile', profile], environment())
        if args.reuse_fixtures:
            with fixture_lock():
                for spec in plan:
                    cell(spec, args)
        else:
            for spec in plan:
                cell(spec, args)


if __name__ == '__main__':
    main()
