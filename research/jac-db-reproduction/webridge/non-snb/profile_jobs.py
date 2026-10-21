#!/usr/bin/env python3
"""Execute frozen generic MySQL profile jobs, preserving every stage's outcome."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('jobs', type=Path)
args = parser.parse_args()
batch = HERE / 'profiles' / ('job-batch-' + str(time.time_ns()))
batch.mkdir()
summary = []
for job in json.loads(args.jobs.read_text()):
    inputs, out = Path(job['input']), Path(job['out'])
    commands = [[sys.executable, str(HERE / 'profile_mysql.py'), '--command-json', str(inputs / 'command.json'), '--prepare-command-json', str(inputs / 'prepare-command.json'), '--database', job['database'], '--out', str(out), '--delay-ms', '2'], [sys.executable, str(HERE / 'analyze_mysql_profile.py'), str(out), '--generated-sources-json', str(inputs / 'generated-sources.json')]]
    row = {**job, 'commands': []}
    summary.append(row)
    for index, command in enumerate(commands):
        result = subprocess.run(command, capture_output=True, text=True)
        label = str(len(summary)) + '-' + str(index)
        (batch / (label + '.stdout')).write_text(result.stdout)
        (batch / (label + '.stderr')).write_text(result.stderr)
        row['commands'].append({'argv': command, 'returncode': result.returncode})
        if result.returncode:
            row['status'] = 'failed-stage'
            break
    else:
        row['status'] = 'PASS'
    (batch / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(job.get('phase'), out.name, row['status'], flush=True)
print(batch, flush=True)
