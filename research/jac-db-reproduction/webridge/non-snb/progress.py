#!/usr/bin/env python3
"""Read published primary coverage without touching live database processes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
latency, references = {}, {}
for owner, name in [('native', 'normalized-rtt-latency.json'), ('tpcc', 'normalized-rtt-latency.json'), ('littlex', 'normalized-rtt-results.json')]:
    document = json.loads((ROOT / owner / name).read_text())
    rows = document if isinstance(document, list) else document['cells']
    latency[owner] = sum(r.get('method') != 'reference' and r.get('status') != 'pending' for r in rows)
    if owner == 'littlex':
        references[owner] = sum(r.get('method') == 'reference' and r.get('status') != 'pending' for r in rows)
for owner, name in [('native', 'normalized-rtt-reference.json'), ('tpcc', 'rtt-reference-900-index.json')]:
    path = ROOT / owner / name
    document = json.loads(path.read_text()) if path.exists() else []
    references[owner] = len(document if isinstance(document, list) else document.get('rows', document.get('cells', [])))
print(json.dumps({'latency': latency, 'latency_total': sum(latency.values()),
                  'references': references, 'references_total': sum(references.values())}))
