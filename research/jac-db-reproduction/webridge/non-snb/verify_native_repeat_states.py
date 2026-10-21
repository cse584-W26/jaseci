#!/usr/bin/env python3
"""Verify all 42 native representative states against independently checked controls."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = {
    'payment_name_GC': 0, 'new_order_rollback': 1, 'payment_id_GC': 3,
    'new_order_5': 28, 'new_order_15': 35, 'payment_name_BC': 50,
    'payment_id_BC': 54,
}


def digest(path):
    h = hashlib.sha256()
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-payload-hashes', action='store_true')
    args = parser.parse_args()
    root = HERE / 'native/tpcc-timing'
    receipts = []
    for label, index in CASES.items():
        control = root / 'delay-0ms/baseline' / label
        independent = json.loads((control / 'independent-model-verification.json').read_text())
        assert independent['status'] == 'PASS' and independent['requests_checked'] == 40
        assert independent['repeated_original_plan_index'] == index
        assert digest(control / 'rows.jsonl') == independent['request_log_sha256']
        expected = json.loads((control / 'after40-state/manifest.json').read_text())
        for delay in [0, 2, 10]:
            for variant in ['baseline', 'final']:
                cell = root / f'delay-{delay}ms' / variant / label
                summary = json.loads((cell / 'summary.json').read_text())
                assert summary['warm'] == 10 and summary['n'] == 30
                assert summary['logging_restored'] and summary['service_stopped']
                manifest = json.loads((cell / 'after40-state/manifest.json').read_text())
                assert manifest.keys() == expected.keys() and len(manifest) == 8
                files = []
                for relation, entry in manifest.items():
                    assert entry['rows'] == expected[relation]['rows']
                    assert entry['canonical_cents_sha256'] == expected[relation]['canonical_cents_sha256'], (cell, relation)
                    for path_key, hash_key in [('path', 'sha256'), ('canonical_cents_path', 'canonical_cents_sha256')]:
                        saved = Path(entry[path_key])
                        path = cell / 'after40-state' / saved.name
                        if not path.exists():
                            path = path.with_suffix(path.suffix + '.gz')
                        if not args.skip_payload_hashes:
                            assert digest(path) == entry[hash_key], path
                        files.append({'relation': relation, 'path': str(path.relative_to(HERE)), 'sha256_uncompressed': entry[hash_key]})
                rows = [json.loads(line) for line in (cell / 'rows.jsonl').read_text().splitlines()]
                assert len(rows) == 40
                assert all(row['iteration'] == i and row['original_plan_index'] == index for i, row in enumerate(rows))
                receipts.append({'path': str(cell.relative_to(HERE)), 'state': 'matches independently modelled 40-request control', 'files': files})
    out = {'status': 'PASS', 'verified_cells': len(receipts), 'payload_hashes_verified': not args.skip_payload_hashes, 'cells': receipts}
    (root / 'independent-repeat-state-verification.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'verified_cells': len(receipts)}))


if __name__ == '__main__':
    main()
