#!/usr/bin/env python3
"""Independently check all three direct Java original-plan executions."""
from datetime import datetime, timezone
import json
import argparse
from pathlib import Path
import subprocess
import sys
import time
from measurement_lease import lease

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--suffix', default='')
args = parser.parse_args()
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + str(time.time_ns())
out = HERE / 'tpcc/independent-audits' / stamp
out.mkdir(parents=True)
with lease('Independent matched Java 900-request state models', out / 'lease.json'):
    commands = []
    for gate in ['gate-jac-seed900', 'gate-graph-full-900', 'gate-graph-pruned-900']:
        command = [sys.executable, str(HERE / 'verify_tpcc_model.py'), '--seed-projection', 'jac', '--gate', str(HERE / 'tpcc' / (gate + args.suffix))]
        with (out / (gate + '.stdout')).open('w') as stdout, (out / (gate + '.stderr')).open('w') as stderr:
            result = subprocess.run(command, stdout=stdout, stderr=stderr)
        commands.append({'argv': command, 'returncode': result.returncode})
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        result.check_returncode()
        print(gate, 'independent model PASS', flush=True)
