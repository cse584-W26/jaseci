#!/usr/bin/env python3
"""Archive completed public non-SNB evidence using each owner's explicit whitelist."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()



def payload_sha(path):
    digest = hashlib.sha256()
    with gzip.open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def archive_one(path, target, destination, objects, byte_exact=False):
    source_hash = sha(path)
    if path.name.endswith('.jsonl.gz') and not byte_exact:
        logical_hash = payload_sha(path)
        stored = destination / '.payloads' / (logical_hash + '.jsonl.gz')
        stored.parent.mkdir(parents=True, exist_ok=True)
        if logical_hash not in objects:
            if not stored.exists():
                shutil.copy2(path, stored)
            assert payload_sha(stored) == logical_hash
            objects[logical_hash] = {'path': str(stored.relative_to(destination)), 'sha256': sha(stored), 'sha256_uncompressed': logical_hash, 'bytes': stored.stat().st_size}
        stored_hash = objects[logical_hash]['sha256']
        if target.exists() or target.is_symlink():
            target.unlink()
        link = os.path.relpath(stored, target.parent)
        target.symlink_to(link)
        assert target.resolve() == stored.resolve()
        return {'bytes': path.stat().st_size, 'sha256': stored_hash, 'source_gzip_sha256': source_hash, 'sha256_uncompressed': logical_hash, 'relative_symlink': link, 'storage': 'content-addressed gzip; all uncompressed bytes preserved'}
    if target.is_symlink():
        target.unlink()
    shutil.copy2(path, target)
    assert sha(target) == source_hash
    return {'bytes': path.stat().st_size, 'sha256': source_hash}


def allowed(tree):
    manifest = tree / 'PUBLIC_FILES.json'
    document = json.loads(manifest.read_text())
    items = document if isinstance(document, list) else document.get('files', document.get('allowed_files', document.get('included', [])))
    assert isinstance(items, list) and items, ('Empty or unsupported public whitelist', manifest)
    paths = set()
    for item in items:
        name = item if isinstance(item, str) else item['path']
        path = Path(name)
        if not path.is_absolute():
            path = tree / path
        assert path.resolve().is_relative_to(tree.resolve()), path
        assert path.is_file(), path
        paths.add(path.resolve())
    paths.add(manifest.resolve())
    omitted = tree / 'OMITTED_FILES.json'
    if omitted.exists():
        paths.add(omitted.resolve())
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    destination = args.destination.resolve()
    assert destination != ROOT and not destination.is_relative_to(ROOT)
    results = json.loads((ROOT / 'results.json').read_text())
    assert results['metric'] == 'rtt', 'Archive the completed primary SQL round-trip study'
    assert results['coverage']['terminal_cells'] == 648 and results['coverage']['pending_cells'] == 0
    selected = set()
    for name in ['native', 'tpcc', 'littlex']:
        selected.update(allowed(ROOT / name))
    selected.update(p.resolve() for p in ROOT.iterdir() if p.is_file() and not p.name.startswith('.'))
    for name in ['profiles', 'profile-inputs', 'verifier-source-snapshots', 'seed-inputs']:
        selected.update(p.resolve() for p in (ROOT / name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files = []
    objects = {}
    identical_compressed_copies = []
    # Chunk readers verify the original compressed part hashes. Preserve those
    # exact gzip bytes, including headers, rather than normalizing their storage.
    byte_exact = set()
    for index in selected:
        if index.name not in {'rows.chunks.json', 'index.json'}:
            continue
        document = json.loads(index.read_text())
        if not isinstance(document, dict):
            continue
        if document.get('format') == 'littlex-jsonl-gzip-chunks-v1' or index.name == 'rows.chunks.json':
            for part in document['parts']:
                chunk = (index.parent / part.get('path', part.get('file'))).resolve()
                assert chunk in selected, ('Chunk omitted from public whitelist', index, chunk)
                byte_exact.add(chunk)
    for path in sorted(selected):
        relative = path.relative_to(ROOT)
        compressed = path.with_suffix(path.suffix + '.gz')
        if path.suffix == '.jsonl' and compressed in selected:
            h = hashlib.sha256()
            with gzip.open(compressed, 'rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(block)
            assert h.hexdigest() == sha(path), path
            identical_compressed_copies.append({'path': str(relative), 'retained': str(compressed.relative_to(ROOT)), 'sha256_uncompressed': h.hexdigest()})
            continue
        assert path.name not in {'svc_token.json', 'request-context.json', 'identity_users.tsv', 'identity_lookups.tsv', 'kv_state.tsv'}, path
        assert path.suffix not in {'.bin', '.pyc'}, path
        size = path.stat().st_size
        assert size < 95_000_000, ('Compress this public artifact before archiving', path, size)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        value = archive_one(path, target, destination, objects, byte_exact=path in byte_exact)
        files.append({'path': str(relative), **value})
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'archive-manifest.json').write_text(json.dumps({'collection_root': str(ROOT), 'primary_metric': 'Summed SQL round-trip time per request', 'files': files, 'identical_compressed_copies': identical_compressed_copies, 'payload_objects': list(objects.values()), 'selection': 'Completed primary RTT TPC-C and littleX study; per-owner public whitelists, raw accepted/failing measurements, source, generated SQL, profiling and state evidence. Earlier application and server-only measurements retain their own coverage and timer definitions.'}, indent=2) + '\n')
    print(json.dumps({'files': len(files), 'logical_compressed_bytes': sum(x['bytes'] for x in files), 'physical_bytes': sum(x['bytes'] for x in files if 'relative_symlink' not in x) + sum(x['bytes'] for x in objects.values()), 'destination': str(destination)}))


if __name__ == '__main__':
    main()
