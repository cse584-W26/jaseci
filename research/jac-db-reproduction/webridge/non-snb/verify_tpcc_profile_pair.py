#!/usr/bin/env python3
"""Check matched repeated-profile results, affected-row states and global counts."""
import argparse
import hashlib
import gzip
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('jobs', type=Path)
a = p.parse_args()
def resolve_path(value):
    path = Path(value)
    if path.exists():
        return path
    marker = '/non-snb/'
    assert marker in str(path), path
    return Path(__file__).resolve().parent / str(path).split(marker, 1)[1]

def raw_bytes(path):
    if path.exists():
        return path.read_bytes()
    return gzip.decompress(path.with_suffix(path.suffix + '.gz').read_bytes())

jobs = json.loads(a.jobs.read_text())
assert len(jobs) == 2 and {j['phase'] for j in jobs} == {'baseline', 'sp'}
roots = {j['phase']: resolve_path(j['out']) for j in jobs}
rows = {}
cases = {}
for phase, root in roots.items():
    receipt = json.loads((resolve_path(next(j['input'] for j in jobs if j['phase'] == phase)) / 'source-case.json').read_text())
    cases[phase] = receipt['case']
    assert json.loads((root / 'analysis.json').read_text())['status'] == 'PASS'
    rows[phase] = [json.loads(line) for line in raw_bytes(root / 'run/rows.jsonl').decode().splitlines()]
assert cases['baseline'] == cases['sp']
assert len(rows['baseline']) == len(rows['sp'])
for b, s in zip(rows['baseline'], rows['sp']):
    assert b['iteration'] == s['iteration'] and b['warmup'] == s['warmup']
    assert b['result'] == s['result'], b['iteration']
checks = {}
for when in ['before', 'after']:
    observed = {}
    for phase, root in roots.items():
        folder = root / 'run' / when
        manifest = json.loads((folder / 'manifest.json').read_text())
        assert len(manifest) == 8
        observed[phase] = {}
        for relation, item in manifest.items():
            data = raw_bytes(folder / (relation + '.jsonl'))
            assert hashlib.sha256(data).hexdigest() == item['sha256']
            assert len(data.splitlines()) == item['rows']
            observed[phase][relation] = {k: item[k] for k in ['rows', 'sha256']}
        observed[phase]['global_counts'] = json.loads((folder / 'global-counts.json').read_text())
    assert observed['baseline'] == observed['sp'], when
    checks[when] = observed['baseline']
receipt = {'status': 'PASS', 'requests_compared': len(rows['baseline']), 'scope': 'Every evolving result, all retained affected-row snapshots in eight business relations, plus complete global entity counts; full eight-table procedure gates are separate.', 'case': cases['sp'], 'checks': checks, 'profiles': {k: str(v) for k, v in roots.items()}}
(roots['sp'] / 'paired-results-and-state.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': 'PASS', 'requests_compared': len(rows['baseline'])}))
