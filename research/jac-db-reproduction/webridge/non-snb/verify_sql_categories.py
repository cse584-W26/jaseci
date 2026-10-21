#!/usr/bin/env python3
"""Check SQL classification against the actual final feed and mutation traces."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from analyze_mysql_profile import category

ROOT = Path(__file__).resolve().parent
checks = []
for implementation in ['LittleXFull', 'LittleXPruned']:
    artifact = ROOT / 'profiles/littlex-batch-1792549879927774846' / ('t20-feed-' + implementation + '-baseline/analysis.json')
    for request in json.loads(artifact.read_text())['requests']:
        if request['warmup']:
            continue
        counts = Counter(category(op['sql']) for op in request['operations'])
        expected = {'transaction.setting': 4, 'traversal.1hop.projection_acl': 2, 'traversal.2hop.projection_acl': 1}
        if implementation == 'LittleXFull':
            expected.update({'transaction.setting': 8, 'hydration.full_anchor': 2, 'type_registry.ancestry': 2, 'acl.root_permissions': 3, 'identity.lookup': 2})
        assert counts == expected, (artifact, counts, expected)
        checks.append({'artifact': str(artifact.relative_to(ROOT)), 'iteration': request['iteration'], 'counts': dict(counts), 'SQL_hashes': [op['sql_sha256'] for op in request['operations']]})
for operation, verb, expected in [('follow', 'insert', 'relational.lx_follows.insert'), ('like', 'update', 'relational.lx_tweets.update')]:
    artifact = ROOT / 'profiles/littlex-batch-1792547993708251332' / ('t20-' + operation + '-LittleXSql-baseline/analysis.json')
    for request in json.loads(artifact.read_text())['requests']:
        if request['warmup']:
            continue
        sql = [op for op in request['operations'] if op['sql'].lower().startswith(verb)]
        assert len(sql) == 1 and category(sql[0]['sql']) == expected
        checks.append({'artifact': str(artifact.relative_to(ROOT)), 'iteration': request['iteration'], 'SQL_hash': sql[0]['sql_sha256'], 'category': expected})
receipt = {'status': 'PASS', 'analyzer_sha256': hashlib.sha256((ROOT / 'analyze_mysql_profile.py').read_bytes()).hexdigest(), 'checks': checks}
(ROOT / 'sql-category-verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': 'PASS', 'request_checks': len(checks)}))
