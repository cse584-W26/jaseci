#!/usr/bin/env python3
"""Recompute seven independent representative models and verify all 42 snapshots."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

from measurement_lease import lease
from verify_native_repeat_states import CASES

HERE = Path(__file__).resolve().parent
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + str(time.time_ns())
out = HERE / 'native/audits' / stamp
out.mkdir(parents=True)
with lease('Independent native 40-request state models', out / 'lease.json') as receipt:
    commands = []
    for label, index in CASES.items():
        command = [sys.executable, str(HERE / 'verify_tpcc_model.py'), '--native', '--seed-projection', 'jac', '--repeat-index', str(index), '--gate', str(HERE / 'native/tpcc-timing/delay-0ms/baseline' / label)]
        with (out / (label + '.stdout')).open('w') as stdout, (out / (label + '.stderr')).open('w') as stderr:
            result = subprocess.run(command, stdout=stdout, stderr=stderr)
        commands.append({'argv': command, 'returncode': result.returncode})
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        result.check_returncode()
        print(label, 'independent model PASS', flush=True)
    command = [sys.executable, str(HERE / 'verify_native_repeat_states.py')]
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'all-states.stdout').write_text(result.stdout)
    (out / 'all-states.stderr').write_text(result.stderr)
    commands.append({'argv': command, 'returncode': result.returncode})
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    result.check_returncode()
    print(result.stdout, flush=True)
