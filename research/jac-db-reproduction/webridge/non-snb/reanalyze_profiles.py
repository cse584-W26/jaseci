#!/usr/bin/env python3
"""Recompute classifications from successful raw profiles, retaining prior hashes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from aggregate_results import HERE, local
from measurement_lease import lease

source = HERE / 'analyze_mysql_profile.py'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
batch = HERE / 'profiles' / ('reanalysis-' + str(time.time_ns()))
batch.mkdir()
(batch / 'analyzer-source.py').write_bytes(source.read_bytes())
summary = []
for receipt in sorted((HERE / 'profiles').rglob('collection.json')):
    if json.loads(receipt.read_text())['status'] != 'PASS':
        continue
    out = receipt.parent
    old_file = out / 'analysis.json'
    old = json.loads(old_file.read_text()) if old_file.exists() else {}
    if old.get('status') == 'PASS' and old.get('analyzer_source_sha256') == source_hash:
        continue
    config = json.loads((out / 'config.json').read_text())
    inputs = local(config['command_json']).parent
    command = [sys.executable, str(batch / 'analyzer-source.py'), str(out)]
    generated = inputs / 'generated-sources.json'
    if generated.exists():
        command += ['--generated-sources-json', str(generated)]
    index = str(len(summary))
    previous = hashlib.sha256(old_file.read_bytes()).hexdigest() if old_file.exists() else None
    with lease('Reclassify recorded SQL ' + out.name, batch / (index + '-lease.json')):
        result = subprocess.run(command, capture_output=True, text=True)
    (batch / (index + '-stdout.json')).write_text(result.stdout)
    (batch / (index + '-stderr.log')).write_text(result.stderr)
    summary.append({'profile': str(out), 'prior_analysis_sha256': previous,
                    'prior_analyzer_source_sha256': old.get('analyzer_source_sha256'),
                    'current_analyzer_source_sha256': source_hash,
                    'command': command, 'returncode': result.returncode})
    (batch / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out.name, result.returncode, flush=True)
print(batch, flush=True)
if any(r['returncode'] for r in summary):
    sys.exit(1)
