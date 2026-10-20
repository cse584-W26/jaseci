#!/usr/bin/env python3
"""Normalize fixed original SNB parameters for the MySQL UUID representation."""
import hashlib,json,pathlib,uuid
H=pathlib.Path(__file__).resolve().parent;E=H.parent
original=E/'inputs-all20.json';data=json.loads(original.read_text());print(type(data).__name__)
if isinstance(data,dict):groups=data
else:
 groups={}
 for row in data:groups.setdefault(row['query'],[]).append(row)
for query,rows in groups.items():
 if isinstance(rows,dict):rows=[rows]
 out=[]
 for row in rows:
  x={'query':query,'original_idx':row['idx'],**row['body']}
  for k,v in list(x.items()):
   if k.endswith('_jid'):x[k]=str(uuid.UUID(v))
  x['expected_canonical_sha256']=row.get('expected_canonical_sha256');oracle=E/'native/gates/baseline-canonical'/f'{query}-oracles.json'
  if oracle.exists():
   values=json.loads(oracle.read_text());x['expected']=values[row['idx']]
  out.append(x)
 p=H/'inputs'/f'{query}.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(out,indent=2))
(H/'inputs/provenance.json').write_text(json.dumps({'source':str(original),'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'adaptation':'UUID display hyphens only; business parameters unchanged','outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((H/'inputs').glob('*.json')) if p.name!='provenance.json'}},indent=2))
