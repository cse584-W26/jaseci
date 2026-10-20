#!/usr/bin/env python3
"""Plan or explicitly run the serialized fixture reset diagnostic, never full matrix."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    env = os.environ.copy()
    env.setdefault('LITTLEX_JAC_BIN', str(ROOT / 'runtime/bin/jac314'))
    env.setdefault('LITTLEX_PYTHON', str(ROOT / 'runtime/venv314/bin/python'))
    env.setdefault('LITTLEX_SQL_PYTHON', str(ROOT / 'runtime/venv-littlex-sql-locked/bin/python'))
    env.setdefault('LITTLEX_DRIVER_PYTHON', str(ROOT / 'runtime/venv-littlex-driver-locked/bin/python'))
    env.setdefault('LITTLEX_SQL_ADMIN_DSN', 'postgresql://postgres@127.0.0.1:55436/littleX')
    stages = [('restore-before-writes', 'jaseci', 'W1'),
              ('mutate-and-restore-between-ops', 'jaseci', 'W2'),
              ('restore-after-writes', 'jaseci', 'W1'),
              ('sql16-tcp', 'postgres', 'W1')]
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    logs = HERE / 'smoke' / run_id
    if args.execute:
        logs.mkdir(parents=True)
    for stage, arm, phase in stages:
        command = [env['LITTLEX_PYTHON'], str(HERE / 'run.py'), '--run', '--reuse-fixtures',
                   '--arms', arm, '--tiers', 't20', '--phases', phase,
                   '--requests', '10', '--warmup', '110']
        print(stage + ': ' + shlex.join(command), flush=True)
        if not args.execute:
            continue
        operations = ['feed'] if phase == 'W1' else ['create_tweet', 'follow', 'like']
        markers = [HERE / 'data' / f'{phase}_t20_{arm}_{op}' / 'complete.json' for op in operations]
        if any(p.exists() for p in markers):
            raise RuntimeError('Existing canonical completion marker; inspect before smoke')
        with (logs / (stage + '.log')).open('w') as f:
            completed = subprocess.run(command, env=env, stdout=f, stderr=subprocess.STDOUT)
        for marker in markers:
            if not marker.exists():
                continue
            result = json.loads(marker.read_text())
            result['measurement_role'] = 'diagnostic fixture reset smoke; excluded from canonical measurements'
            result['smoke_stage'] = stage
            result['sql_topology'] = 'PostgreSQL16 Docker/TCP 127.0.0.1:55436'
            artifact = logs / (stage + '-' + result['cell'] + '.json')
            artifact.write_text(json.dumps(result, indent=2))
            marker.unlink()
        if completed.returncode:
            raise RuntimeError(f'Smoke stage failed ({completed.returncode}): {logs / (stage + ".log")}')
    if args.execute:
        (logs / 'complete.json').write_text(json.dumps(dict(run_id=run_id, stages=stages), indent=2))
        print('Fixture smoke complete: ' + str(logs), flush=True)


if __name__ == '__main__':
    main()
