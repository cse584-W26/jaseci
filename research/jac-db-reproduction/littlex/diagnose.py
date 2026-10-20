#!/usr/bin/env python3
"""Run owned-cluster commit floor, source×lazy read controls and write diagnostics."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import run as lx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--historical-rr',action='store_true',help='Historical fixture final read and oldCTRL page original warm/user controls')
    parser.add_argument('--round-robin', action='store_true', help='Original110warm round-robin controls;50timed')
    parser.add_argument('--final-fixture', action='store_true', help='Final original fresh-cell fixture, finalLAZY1 duration on/off')
    parser.add_argument('--off-only', action='store_true', help='Four source/lazy t20 controls with SQL duration logging disabled and50 repeats')
    parser.add_argument('--skip-floor', action='store_true', help='Reuse already completed results/commit-floor evidence')
    args = parser.parse_args()
    variants = [('ad469-control', lx.ROOT / 'runtime/bin/jac314-ad469', None),
                ('ad469-lazy1', lx.ROOT / 'runtime/bin/jac314-ad469', '1'),
                ('final-lazy0', lx.ROOT / 'runtime/bin/jac314', '0'),
                ('final-lazy1', lx.ROOT / 'runtime/bin/jac314', '1')]
    if not args.run:
        print('Commit floor: dedicated PostgreSQL16TCP and native18,5warm+40timed.')
        print('t20samehistoricalfixture read grid:', [(n, v) for n, _, v in variants])
        print('create_tweet100warm+100profiled:ad469CONTROL and finalLAZY1.')
        print('t200representatives:ad469CONTROL and finalLAZY1,feed_chain and feed_page.')
        return
    import psycopg
    from psycopg import sql
    import subprocess
    commit = subprocess.check_output(['git', '-C', str(lx.SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    assert commit.startswith('32c5d1') if args.final_fixture else commit.startswith('ad469c988'), 'Fixture source identity mismatch'
    complete = json.loads((lx.HERE / 'original-recipe/latest.json').read_text())
    assert complete['complete_cells'] == 40
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = lx.HERE / 'diagnostics' / stamp
    output.mkdir(parents=True)
    env = lx.environment()
    env.update(PERF='1', JAC_STREAM_LATERAL='1', JAC_SQL_ACL='1', JAC_FUSED_FEED='1',
               JAC_STICKY_DENY='1', JAC_RO_WALKERS='')
    progress = []

    def profile(name, binary, lazy, tier, workload, writer=False, duration=True):
        seed = lx.HERE / 'dataset' / (tier + '_seed.json')
        # Always reset the same historical physical snapshot, regardless of server variant.
        app, tokens, reset = lx.fixture(tier, seed, env)
        cell = output / name
        cell.mkdir()
        e = dict(env, JAC_PG_APP_DIR=str(app), JAC_PG_BIN=str(binary), JAC_STAGE_HEADERS='1')
        if lazy is not None:
            e['JAC_LAZY_TXN'] = lazy
        else:
            e.pop('JAC_LAZY_TXN', None)
        db = reset['database']
        p = None
        with psycopg.connect(f'host={lx.SOCK} user=jac dbname=postgres', autocommit=True) as admin:
            settings = admin.execute("SELECT setconfig FROM pg_db_role_setting WHERE setrole=0 AND setdatabase=(SELECT oid FROM pg_database WHERE datname=%s)", (db,)).fetchone()
            previous = next((s.split('=', 1)[1] for s in (settings[0] if settings else []) if s.startswith('log_min_duration_statement=')), None)
            admin.execute(sql.SQL('ALTER DATABASE {} SET log_min_duration_statement TO {}').format(sql.Identifier(db), sql.Literal('0' if duration else '-1')))
            try:
                p = lx.launch([binary, 'start', 'main.jac', '-p', '18120', '--no-client'], app, e,
                              cell / 'server.log', 18120, '/healthz')
                tag = 'littlex-diagnostics/' + stamp + '/' + name
                script = 'littlex_write_profile.py' if writer else 'littlex_profile.py'
                command = [lx.DRIVER_PYTHON, lx.ROOT / 'scripts' / script, '--tag', tag, '--tier', tier,
                           '--pid', str(p.pid), '--tokens-dir', tokens, '--database', db, '--seed', seed]
                if writer:
                    command += ['--operation', 'create_tweet', '--app-dir', app, '--jac-bin', binary,
                                '--warmups', '100', '--repeats', '100']
                else:
                    command += ['--workload', workload, '--warmups', '110' if args.round_robin else '10', '--repeats', '50' if args.round_robin or not duration else '10']
                if args.round_robin and not writer:
                    command += ['--round-robin']
                if not duration:
                    command += ['--duration-off']
                lx.command(command, e, log=cell / 'profile.log')
                source_path = lx.SOURCE if binary.name == 'jac314-ad469' else lx.ROOT.parent / 'jac-db/jac'
                report = dict(name=name, tag=tag, reset=reset, binary=str(binary),
                              source_factor='ad469' if binary.name == 'jac314-ad469' else 'final32',
                              runtime_source=str(source_path),
                              runtime_commit=subprocess.check_output(['git', '-C', str(source_path), 'rev-parse', 'HEAD'], text=True).strip(),
                              app_sha256=__import__('hashlib').sha256((app / 'app.jac').read_bytes()).hexdigest(),
                              lazy=lazy if lazy is not None else 'unset', tier=tier, workload=workload,
                              writer=writer, stage_headers=True, sql_duration_logging=duration,
                              environment={k: v for k, v in e.items() if k.startswith('JAC_') or k == 'PERF'})
                (cell / 'complete.json').write_text(json.dumps(report, indent=2))
                progress.append(report)
                (output / 'progress.json').write_text(json.dumps(progress, indent=2))
                print('PASS diagnostic ' + name, flush=True)
            finally:
                lx.stop(p)
                if previous is None:
                    admin.execute(sql.SQL('ALTER DATABASE {} RESET log_min_duration_statement').format(sql.Identifier(db)))
                else:
                    admin.execute(sql.SQL('ALTER DATABASE {} SET log_min_duration_statement TO {}').format(sql.Identifier(db), sql.Literal(previous)))

    with lx.fixture_lock():
        if args.historical_rr:
            profile('t20-historical-fixture-final1-rr',variants[3][1],'1','t20','feed_chain')
            profile('t200-page-ad-control-rr',variants[0][1],None,'t200','feed_page')
            (output/'complete.json').write_text(json.dumps(dict(directory=str(output),profiles=progress),indent=2))
            return
        if args.final_fixture:
            profile('t20-final-fixture-duration-on', variants[3][1], '1', 't20', 'feed_chain')
            profile('t20-final-fixture-duration-off', variants[3][1], '1', 't20', 'feed_chain', duration=False)
            (output / 'complete.json').write_text(json.dumps(dict(directory=str(output), profiles=progress), indent=2))
            print('Final-fixture diagnostics complete: ' + str(output), flush=True)
            return
        if args.off_only:
            for name, binary, lazy in variants:
                profile('t20-duration-off-' + name, binary, lazy, 't20', 'feed_chain', duration=False)
            (output / 'complete.json').write_text(json.dumps(dict(directory=str(output), profiles=progress), indent=2))
            print('Duration-off diagnostics complete: ' + str(output), flush=True)
            return
        if args.skip_floor:
            floor = json.loads((lx.ROOT / 'results/commit-floor/summary.json').read_text())
            assert all(floor['arms'][arm]['total_ms']['n'] == 40 for arm in ('pg16', 'native'))
        else:
            lx.command([lx.DRIVER_PYTHON, lx.ROOT / 'scripts/commit_floor.py', '--execute', '--host-metadata',
                        '--out-dir', lx.ROOT / 'results/commit-floor'], env, log=output / 'commit-floor.log')
        print('PASS commit-floor', flush=True)
        for name, binary, lazy in variants:
            profile('t20-' + name, binary, lazy, 't20', 'feed_chain')
        for name, binary, lazy in [variants[0], variants[3]]:
            profile('write-' + name, binary, lazy, 't20', 'create_tweet', writer=True)
        for name, binary, lazy in [variants[0], variants[3]]:
            for workload in ('feed_chain', 'feed_page'):
                profile('t200-' + workload + '-' + name, binary, lazy, 't200', workload)
    (output / 'complete.json').write_text(json.dumps(dict(directory=str(output), profiles=progress), indent=2))
    print('Diagnostics complete: ' + str(output), flush=True)


if __name__ == '__main__':
    main()
