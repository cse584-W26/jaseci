#!/usr/bin/env python3
"""Independently model every repeated request in final Java protocol profiles."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from aggregate_results import HERE, local
from measurement_lease import lease

status = json.loads((HERE / 'tpcc/case-status.json').read_text())
selected = {r['case'] for r in status if r.get('case')}
batch = HERE / 'profiles' / ('independent-model-audits-' + str(time.time_ns()))
batch.mkdir()
summary = []
verifier = HERE / 'verify_tpcc_model.py'
source_hash = hashlib.sha256(verifier.read_bytes()).hexdigest()
(batch / 'verifier-source.py').write_bytes(verifier.read_bytes())
for inputs in sorted((HERE / 'profile-inputs').glob('tpcc-*')):
    source = inputs / 'source-case.json'
    if not source.exists():
        continue
    receipt = json.loads(source.read_text())
    if receipt['case'] not in selected:
        continue
    out = local(receipt['profile_output'])
    if not (out / 'analysis.json').exists() or json.loads((out / 'analysis.json').read_text())['status'] != 'PASS':
        continue
    previous = out / 'run/independent-model-verification.json'
    if previous.exists() and json.loads(previous.read_text()).get('verifier_source_sha256') == source_hash:
        continue
    command = [sys.executable, str(verifier), '--gate', str(out / 'run'), '--seed-projection', 'jac', '--profile-case', str(local(receipt['case']))]
    stem = str(len(summary))
    with lease('Independent repeated TPC-C profile model ' + out.name, batch / (stem + '-lease.json')):
        result = subprocess.run(command, capture_output=True, text=True)
        (batch / (stem + '-stdout.json')).write_text(result.stdout)
        (batch / (stem + '-stderr.log')).write_text(result.stderr)
    summary.append({'profile': str(out), 'command': command, 'returncode': result.returncode, 'status': 'PASS' if result.returncode == 0 else 'failed-stage'})
    (batch / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out.name, summary[-1]['status'], flush=True)
print(batch, flush=True)
if any(r['returncode'] for r in summary):
    sys.exit(1)
