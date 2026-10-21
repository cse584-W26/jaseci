#!/usr/bin/env python3
"""Freeze baseline/SP profile inputs from accepted final compiler cases."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('tpcc_timer', HERE / 'tpcc/timing_command.py')
timer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timer)
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--workload', required=True)
p.add_argument('--program', choices=['conventional', 'graph'], required=True)
p.add_argument('--variant', choices=['full', 'pruned'], default='full')
p.add_argument('--baseline-only', action='store_true')
a = p.parse_args()
selected = [r for r in json.loads((HERE / 'tpcc/case-status.json').read_text())
            if r['workload'] == a.workload and r['program'] == a.program and r['variant'] == a.variant]
assert len(selected) == 1 and selected[0]['baseline_ready']
if not a.baseline_only:
    assert selected[0]['status'] == 'success' and selected[0]['sp_ready']
case = Path(selected[0]['case'])
meta = json.loads((case / 'metadata.json').read_text())
label = f'tpcc-final-{a.program}-{a.variant}-{a.workload}-{time.time_ns()}'
jobs = []
for phase in (['baseline'] if a.baseline_only else ['baseline', 'sp']):
    inputs = HERE / 'profile-inputs' / (label + '-' + phase)
    out = HERE / 'profiles' / (label + '-' + phase)
    inputs.mkdir()
    def save(name, value):
        (inputs / name).write_text(json.dumps(value, indent=2) + '\n')
    save('command.json', timer.command(case, '{profile_output}', phase, 10, 3, '{endpoint}'))
    save('prepare-command.json', [sys.executable, str(HERE / 'tpcc/reset_cell.py'),
         '--case', str(case), '--phase', phase, '--receipt', str(out / 'prepare-reset.json')])
    save('source-case.json', {'case': str(case), 'metadata': meta, 'profile_output': str(out)})
    save('generated-sources.json', [str(f) for f in sorted((case / 'generated/sql').rglob('*.sql'))])
    jobs.append({'phase': phase, 'input': str(inputs), 'out': str(out), 'database': meta['database']})
target = HERE / 'profile-inputs' / (label + '-jobs.json')
target.write_text(json.dumps(jobs, indent=2) + '\n')
print(target)
