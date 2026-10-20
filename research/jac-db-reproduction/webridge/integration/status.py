#!/usr/bin/env python3
"""Summarize retained integration evidence without issuing SQL."""
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
entries=[]
for case in sorted((R/'cases').iterdir()):
 if not case.is_dir():continue
 item=dict(case=str(case),metadata=json.loads((case/'metadata.json').read_text()) if (case/'metadata.json').exists() else {},attempts=[])
 for d in sorted(case.iterdir()):
  if not d.is_dir():continue
  a=dict(directory=str(d))
  for f in ('process-result.json','error.json','report.json','report-0.json','gate-verification.json'):
   if (d/f).exists():a[f]=json.loads((d/f).read_text())
  for name in ('graph.json','engine-graph-early.json'):
   if (d/name).exists():a[name]=dict(bytes=(d/name).stat().st_size,path=str(d/name))
  if len(a)>1:item['attempts'].append(a)
 entries.append(item)
(R/'STATUS.json').write_text(json.dumps(dict(cases=entries,all20_derivative_gate={p.parent.parent.name:json.loads(p.read_text())['all_passed'] for p in (R/'cases').glob('*/gate-*/gate-verification.json')},jac_only_overhead_removals_in_full_stage=[],upstream_graph_or_synthesis_algorithm_edits=[]),indent=2))
print(R/'STATUS.json')
