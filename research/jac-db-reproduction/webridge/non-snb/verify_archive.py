#!/usr/bin/env python3
"""Verify every archived path, relative link, compressed object and raw payload."""
import json
import os
from pathlib import Path
from archive_evidence import payload_sha, sha

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / 'archive-manifest.json').read_text())
checked = {}
for item in manifest.get('payload_objects', []):
    path = ROOT / item['path']
    assert not path.is_symlink() and path.is_file()
    assert sha(path) == item['sha256']
    assert payload_sha(path) == item['sha256_uncompressed']
    checked[path.resolve()] = item['sha256']
for item in manifest['files']:
    path = ROOT / item['path']
    assert path.is_file() and path.resolve().is_relative_to(ROOT), path
    if 'relative_symlink' in item:
        assert path.is_symlink() and os.readlink(path) == item['relative_symlink'], path
    resolved = path.resolve()
    if resolved not in checked:
        checked[resolved] = sha(path)
    assert checked[resolved] == item['sha256'], path
receipt = {'status': 'PASS', 'paths_verified': len(manifest['files']), 'unique_payloads': len(manifest.get('payload_objects', [])), 'manifest_sha256': sha(ROOT / 'archive-manifest.json'), 'verifier_sha256': sha(Path(__file__).resolve())}
(ROOT / 'archive-verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
