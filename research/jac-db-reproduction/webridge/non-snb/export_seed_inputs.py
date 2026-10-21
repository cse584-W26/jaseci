#!/usr/bin/env python3
"""Retain the exact synthetic seed and generator for standalone state audits."""
import hashlib
import json
from pathlib import Path
import shutil
from measurement_lease import lease

ROOT = Path(__file__).resolve().parent
source = ROOT.parents[1] / 'benchmark/tpcc'
out = ROOT / 'seed-inputs'
out.mkdir(exist_ok=True)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


with lease('Export synthetic seed for portable independent state verification', out / 'export-lease.json'):
    manifest = json.loads((source / 'data/manifest.json').read_text())
    records = []
    for entry in manifest['files']:
        original, target = source / 'data' / entry['file'], out / entry['file']
        assert sha(original) == entry['sha256']
        shutil.copy2(original, target)
        assert sha(target) == entry['sha256']
        records.append({'file': entry['file'], 'bytes': target.stat().st_size, 'sha256': entry['sha256']})
    assert sha(source / 'gendata.py') == manifest['generator_sha256']
    shutil.copy2(source / 'gendata.py', out / 'gendata.py')
    shutil.copy2(source / 'data/manifest.json', out / 'manifest.json')
    result = {'status': 'PASS', 'files': records, 'generator_sha256': manifest['generator_sha256'], 'manifest_sha256': sha(out / 'manifest.json'), 'scope': 'Synthetic seed-42, one warehouse; exact original JSONL bytes for standalone state-model audits'}
    (out / 'export-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'files': len(records)}))
