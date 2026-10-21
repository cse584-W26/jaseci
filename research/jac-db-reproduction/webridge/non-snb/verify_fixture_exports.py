#!/usr/bin/env python3
"""Rehash littleX exports and independently check graph closure/cardinality."""
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    receipts = sorted((HERE / 'littlex/fixtures').glob('*/export.json'))
    assert len(receipts) == 4, 'All four fixture exports are required'
    checked = []
    for receipt in receipts:
        data = json.loads(receipt.read_text())
        tables = {}
        for name, meta in data['tables'].items():
            path = Path(meta['path'])
            content = path.read_bytes()
            assert hashlib.sha256(content).hexdigest() == meta['sha256'], path
            assert content.count(b'\n') == meta['rows'], path
            tables[name] = {'rows': meta['rows'], 'sha256': meta['sha256']}
        rows = [line.split(b'\t') for line in Path(data['tables']['anchors']['path']).read_bytes().splitlines()]
        assert all(len(row) == 14 for row in rows)
        ids = {row[0] for row in rows}
        assert len(ids) == len(rows), 'Duplicate anchor IDs'
        null = b'\\N'
        assert all(row[5] == null or row[5] in ids for row in rows), 'Missing graph owner'
        edges = [row for row in rows if row[1] == b'EdgeAnchor']
        assert all(row[6] in ids and row[7] in ids for row in edges), 'Missing edge endpoint'
        counts = Counter((row[1].decode(), row[2].decode()) for row in rows)
        assert [[*key, value] for key, value in sorted(counts.items())] == data['types']
        tier = int(receipt.parent.name[1:])
        for kind, name, count in [('NodeAnchor', 'Profile', 100),
                                   ('NodeAnchor', 'Tweet', tier * 100),
                                   ('EdgeAnchor', 'Post', tier * 100),
                                   ('EdgeAnchor', 'Follow', 5000)]:
            assert counts[(kind, name)] == count, (receipt.parent.name, name)
        checked.append({'tier': receipt.parent.name,
                        'export_receipt_sha256': hashlib.sha256(receipt.read_bytes()).hexdigest(),
                        'tables': tables, 'unique_anchors': len(ids),
                        'edges_with_verified_endpoints': len(edges),
                        'missing_owners': 0, 'missing_edge_endpoints': 0})
    result = {'status': 'PASS', 'scope': 'Exact export bytes and complete littleX graph closure',
              'fixtures': checked}
    (HERE / 'fixture-exports-verified.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'tiers': len(checked),
                      'anchors_checked': sum(item['unique_anchors'] for item in checked)}))


if __name__ == '__main__':
    main()
