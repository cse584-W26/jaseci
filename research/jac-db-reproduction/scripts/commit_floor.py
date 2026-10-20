"""One-row INSERT+COMMIT diagnostic on reproduction-owned PostgreSQL clusters.

Default is a read-only plan (no database connections). Pass --execute only in
an allocated profiling window. No PostgreSQL settings or workload tables change.
"""
import argparse
import csv
import datetime
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import uuid

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

ROOT = Path(__file__).resolve().parents[1]
NATIVE_SOCKET = '/tmp/jacpg-d6275e76eb'
DEFAULTS = {
    'pg16': 'postgresql://postgres@127.0.0.1:55436/postgres',
    'native': f'host={NATIVE_SOCKET} user=jac dbname=postgres',
}
SETTINGS = ['server_version', 'fsync', 'synchronous_commit', 'wal_sync_method',
            'full_page_writes', 'checkpoint_timeout', 'max_wal_size',
            'log_statement', 'log_min_duration_statement', 'data_directory']


def validate(arm, dsn):
    cfg = conninfo_to_dict(dsn)
    assert cfg.get('dbname') == 'postgres', 'Use owned cluster maintenance DB postgres'
    if arm == 'pg16':
        assert cfg.get('host') == '127.0.0.1' and cfg.get('port') == '55436', cfg
    else:
        assert cfg.get('host') == NATIVE_SOCKET and cfg.get('port', '5432') == '5432', cfg
    return {k: v for k, v in cfg.items() if 'password' not in k.lower()}


def percentiles(values):
    ordered = sorted(values)
    return {'n': len(values), 'mean_ms': statistics.mean(values),
            'median_ms': statistics.median(values),
            'upper_middle_ms': ordered[len(ordered)//2],
            'p95_upper_index_ms': ordered[min(len(ordered)-1, int(.95*len(ordered)))],
            'min_ms': min(values), 'max_ms': max(values)}


def host_metadata():
    commands = [
        ['findmnt', '-J', '-T', str(ROOT), '-o', 'SOURCE,TARGET,FSTYPE,OPTIONS'],
        ['lsblk', '-J', '-o', 'NAME,TYPE,SIZE,ROTA,MOUNTPOINTS'],
        ['docker', 'inspect', 'jac-db-reproduction-pg16', '--format', '{{json .Mounts}}'],
    ]
    data = []
    for cmd in commands:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            data.append({'command': cmd, 'exit': r.returncode,
                         'stdout': r.stdout, 'stderr': r.stderr})
        except (OSError, subprocess.TimeoutExpired) as exc:
            data.append({'command': cmd, 'error': str(exc)})
    return data


def run_arm(arm, dsn, args, runid):
    table = f'commit_floor_{runid}_{arm}'
    target = sql.Identifier('repro_scratch', table)
    result = {'arm': arm, 'connection': validate(arm, dsn),
              'scratch_table': 'repro_scratch.'+table, 'rows': [],
              'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    record = args.out_dir / f'{arm}.summary.json'
    created = False
    with psycopg.connect(dsn, autocommit=True, application_name='jac-db-repro-commit-floor') as conn:
        result['backend'] = dict(zip(['database', 'user', 'session_user', 'backend_pid', 'role_superuser'],
            conn.execute('SELECT current_database(),current_user,session_user,pg_backend_pid(),'
                         '(SELECT rolsuper FROM pg_roles WHERE rolname=current_user)').fetchone()))
        result['settings'] = {name: conn.execute(sql.SQL('SHOW {}').format(sql.Identifier(name))).fetchone()[0] for name in SETTINGS}
        result['server_version_num'] = conn.info.server_version
        result['prepare_threshold'] = conn.prepare_threshold
        result['driver_version'] = psycopg.__version__
        if args.host_metadata:
            result['host_storage_metadata'] = host_metadata()
        conn.execute('CREATE SCHEMA IF NOT EXISTS repro_scratch')
        conn.execute(sql.SQL('CREATE TABLE {} (sample integer NOT NULL, payload text NOT NULL)').format(target))
        created = True
        persistence, relationpath = conn.execute(
            'SELECT relpersistence,pg_relation_filepath(oid) FROM pg_class WHERE oid=%s::regclass',
            ('repro_scratch.'+table,)).fetchone()
        assert persistence == 'p', 'Scratch relation must be ordinary persistent/logged table'
        result['relation_persistence'] = persistence
        result['relation_filepath'] = relationpath
        conn.autocommit = False
        try:
            with (args.out_dir / f'{arm}.raw.csv').open('x', newline='') as handle:
                fields = ['arm', 'phase', 'sample', 'execute_ms', 'commit_ms', 'total_ms', 'rowcount', 'call_start_unix_ns', 'call_end_unix_ns']
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                insert = sql.SQL('INSERT INTO {} (sample,payload) VALUES (%s,%s)').format(target)
                for i in range(args.warmup + args.samples):
                    phase = 'warm' if i < args.warmup else 'timed'
                    wall_begin = time.time_ns()
                    begin = time.perf_counter_ns()
                    cursor = conn.execute(insert, (i, 'x'))
                    after_execute = time.perf_counter_ns()
                    conn.commit()
                    end = time.perf_counter_ns()
                    wall_end = time.time_ns()
                    row = {'arm': arm, 'phase': phase,
                           'sample': i if phase == 'warm' else i-args.warmup,
                           'execute_ms': (after_execute-begin)/1e6,
                           'commit_ms': (end-after_execute)/1e6,
                           'total_ms': (end-begin)/1e6, 'rowcount': cursor.rowcount,
                           'call_start_unix_ns': wall_begin, 'call_end_unix_ns': wall_end}
                    assert row['rowcount'] == 1
                    writer.writerow(row);handle.flush();result['rows'].append(row)
            timed = [r for r in result['rows'] if r['phase'] == 'timed']
            result['timed_summary'] = {k: percentiles([r[k] for r in timed]) for k in ('execute_ms','commit_ms','total_ms')}
            # Validation is outside every timed transaction.
            actual = conn.execute(sql.SQL('SELECT count(*) FROM {}').format(target)).fetchone()[0]
            conn.commit()
            assert actual == args.warmup+args.samples
            result['validated_insert_count'] = actual
            result['ok'] = True
        except BaseException as exc:
            conn.rollback();result['ok'] = False;result['error'] = str(exc)
            raise
        finally:
            conn.autocommit = True
            if created and not args.keep_table:
                conn.execute(sql.SQL('DROP TABLE {}').format(target))
                result['scratch_table_removed'] = True
            else:
                result['scratch_table_removed'] = False
            result['ended_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            record.write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--arm', choices=['both','pg16','native'], default='both')
    p.add_argument('--pg16-dsn', default=DEFAULTS['pg16'])
    p.add_argument('--native-dsn', default=DEFAULTS['native'])
    p.add_argument('--warmup', type=int, default=5)
    p.add_argument('--samples', type=int, default=40)
    p.add_argument('--out-dir', type=Path, default=ROOT/'results/commit-floor')
    p.add_argument('--host-metadata', action='store_true')
    p.add_argument('--keep-table', action='store_true')
    args = p.parse_args()
    assert args.warmup >= 0 and args.samples > 0
    arms = ['pg16','native'] if args.arm=='both' else [args.arm]
    dsns = {'pg16': args.pg16_dsn, 'native': args.native_dsn}
    plan = {'arms': {a:validate(a, dsns[a]) for a in arms}, 'warmup':args.warmup,
            'samples':args.samples, 'out_dir':str(args.out_dir),
            'method':'One reused connection per arm; persistent logged scratch relation; sequential one-row INSERT then conn.commit per transaction. execute_ms includes psycopg implicit BEGIN plus INSERT; commit_ms wraps conn.commit; total_ms covers execute start through COMMIT return. DDL, metadata, validation and cleanup are untimed. No CHECKPOINT or configuration changes.',
            'history':'night0823/PROGRESS.log line10: n40 COMMIT-inclusive median6.3992ms Docker /6.3395ms native. Original scratch script/raw CSV not found in inspected tracked files; exact warmup/timing boundary unknown. Default5warm+40timed is the explicitly documented reproduction method.',
            'python':sys.version}
    print(json.dumps(plan,indent=2),flush=True)
    if not args.execute:return
    args.out_dir.mkdir(parents=True,exist_ok=True)
    for arm in arms:
        if (args.out_dir/f'{arm}.summary.json').exists() or (args.out_dir/f'{arm}.raw.csv').exists():
            raise RuntimeError('Choose a fresh output directory; previous evidence is retained')
    runid = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_')+uuid.uuid4().hex[:8]
    (args.out_dir/'method.json').write_text(json.dumps(plan,indent=2)+'\n')
    results=[run_arm(arm, dsns[arm], args, runid) for arm in arms]
    summary={'method':plan,'arms':{r['arm']:r['timed_summary'] for r in results}}
    (args.out_dir/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
