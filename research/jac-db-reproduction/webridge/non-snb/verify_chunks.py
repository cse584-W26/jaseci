#!/usr/bin/env python3
"""Independently reconstruct public JSONL streams in their indexed part order."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('root', type=Path)
args = parser.parse_args()
root = args.root.resolve()
receipts = []
for index in sorted(set(root.rglob('rows.chunks.json')) | set(root.rglob('index.json'))):
    meta = json.loads(index.read_text())
    if not isinstance(meta, dict):
        continue
    native = index.name == 'rows.chunks.json' and 'uncompressed_sha256' in meta
    if not native and meta.get('format') != 'littlex-jsonl-gzip-chunks-v1':
        continue
    whole = hashlib.sha256()
    total_rows = total_bytes = 0
    for part in meta['parts']:
        path = index.parent / (part['path'] if native else part['file'])
        assert path.resolve().is_relative_to(root) and path.is_file(), path
        compressed = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                compressed.update(block)
        assert compressed.hexdigest() == part['compressed_sha256' if native else 'sha256'], path
        raw = hashlib.sha256()
        rows = size = 0
        if not native:
            assert part['first_plan_ordinal'] == total_rows
        with gzip.open(path, 'rb') as stream:
            for line in stream:
                assert line.endswith(b'\n'), ('Incomplete JSONL row', path)
                raw.update(line)
                whole.update(line)
                rows += 1
                size += len(line)
        assert rows == part['rows'] and size == part['uncompressed_bytes'], path
        if native:
            assert raw.hexdigest() == part['uncompressed_sha256'], path
        else:
            assert part['last_plan_ordinal'] == total_rows + rows - 1
        total_rows += rows
        total_bytes += size
    assert total_rows == meta['rows'] and whole.hexdigest() == meta['uncompressed_sha256'], index
    if 'uncompressed_bytes' in meta:
        assert total_bytes == meta['uncompressed_bytes'], index
    receipts.append({'index': str(index.relative_to(root)), 'parts': len(meta['parts']), 'rows': total_rows, 'uncompressed_bytes': total_bytes, 'uncompressed_sha256': whole.hexdigest()})
assert receipts, 'No public chunk indexes found'
result = {'status': 'PASS', 'streams': len(receipts), 'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'verified': receipts}
(root / 'chunk-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'verified'}))
