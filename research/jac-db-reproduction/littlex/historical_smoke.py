#!/usr/bin/env python3
"""Validate historical ad469CONTROL before the original40-cell recipe."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import subprocess

import run as lx
from original_recipe import validate_historical_fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print('Historical t20: original HTTPseed;100-user full/page validation;reset;110warm+10timed W1/like/follow/create;reset')
        return
    commit = subprocess.check_output(['git', '-C', str(lx.SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    assert commit.startswith('ad469c988')
    assert hashlib.sha256((lx.APP_SOURCE / 'app.jac').read_bytes()).hexdigest() == '89366720a196c275712ccda73c2db06b17ea509c645a87c87ef84e5409821df0'
    e = lx.environment()
    e.update(PERF='1', JAC_STREAM_LATERAL='1', JAC_SQL_ACL='1', JAC_FUSED_FEED='1',
             JAC_STICKY_DENY='1', JAC_RO_WALKERS='')
    folder = lx.HERE / 'historical-smoke' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder.mkdir(parents=True)
    seed = lx.HERE / 'dataset/t20_seed.json'
    with lx.fixture_lock():
        proof = validate_historical_fixture('t20', seed, e)
        app, tokens, reset = lx.fixture('t20', seed, e)
        env = dict(e, JAC_PG_APP_DIR=str(app))
        p = None
        try:
            p = lx.launch([lx.BIN, 'start', 'main.jac', '-p', '18120', '--no-client'], app, env,
                          folder / 'server.log', 18120, '/healthz')
            common = ['--engines', 'jaseci', '--tokens-dir', tokens,
                      '--url-jaseci', 'http://127.0.0.1:18120', '--requests', '10', '--warmup', '110']
            lx.command([lx.DRIVER_PYTHON, lx.HERE / 'harness/run.py', *common,
                        '--workloads', 'feed_chain', '--output', folder / 'read.csv'], env, log=folder / 'read.log')
            lx.command([lx.DRIVER_PYTHON, lx.HERE / 'harness/write_run.py', *common,
                        '--ops', 'like,follow,create_tweet', '--seed', seed,
                        '--output', folder / 'writes.csv'], env, log=folder / 'writes.log')
            read = list(csv.DictReader((folder / 'read.csv').open()))
            writes = list(csv.DictReader((folder / 'writes.csv').open()))
            assert len(read) == 1 and int(read[0]['requests']) == 10 and int(read[0]['errors']) == 0
            assert len(writes) == 3
            for r in writes:
                assert int(r['requests']) == 10 and int(r['errors']) == 0
                assert r['oracle_ok'] == 'True' and int(r['oracle_actual']) == int(r['oracle_expected']) == 120
            after = lx.counts('jaseci', app, env)
            assert after == dict(tweets=2120, follows=5120, likes=120)
        finally:
            lx.stop(p)
        lx.fixture('t20', seed, e)
        report = dict(runtime_commit=commit, app_sha256=hashlib.sha256((lx.APP_SOURCE / 'app.jac').read_bytes()).hexdigest(),
                      historical_validation=proof, reset=reset, post_counts=after,
                      role='diagnostic historical compatibility smoke', reads=read, writes=writes)
        (folder / 'complete.json').write_text(json.dumps(report, indent=2))
        print('Historical CONTROL smoke passed: ' + str(folder), flush=True)


if __name__ == '__main__':
    main()
