#!/usr/bin/env python3
"""Refresh final small native launcher metadata without rereading measured payloads."""
import hashlib,json,pathlib,time
H=pathlib.Path(__file__).resolve().parent;P=H/'PUBLIC_FILES.json';data=json.loads(P.read_text());files={r['path']:r for r in data['files']};omitted={r['path']:r for r in data['omitted_files']};native=H/'native';added=changed=removed=0
for name in list(files):
 p=pathlib.Path(name)
 if p.is_relative_to(native)and not p.is_file():
  files.pop(name);removed+=1
for p in sorted(native.rglob('*')):
 if not p.is_file():continue
 size=p.stat().st_size;assert size<10*1024**2,('Launcher metadata size guard',p,size)
 private=p.suffix in {'.tsv','.bin','.pyc'}or'__pycache__'in p.parts or p.name in {'svc_token.json','request-context.json','graph.json','recorded-resultsets.json'}
 sha=hashlib.sha256(p.read_bytes()).hexdigest()
 if private:
  files.pop(str(p),None);omitted[str(p)]={'path':str(p),'bytes':size,'sha256':sha,'reason':'private or rebuildable native launcher artifact','hash_scope':'compact payload'};continue
 row={'path':str(p),'bytes':size,'sha256':sha};old=files.get(str(p));added+=old is None;changed+=old is not None and old!=row;files[str(p)]=row
normalized=json.loads((H/'normalized-rtt-results.json').read_text());assert normalized['latency_cells']==360 and normalized['reference_cells']==120
required=set()
for r in normalized['cells']:
 if r['status']!='accepted':continue
 for key in ['requests_artifact','rtt_summary_artifact','compact_trace_artifact','source_result_oracle','state_result_gate']:required.add(r[key])
 required.add(r.get('public_full_results_chunk_index')or r['full_results_logical_monolith'])
indexes=list((H/'primary-rtt/complete-final/matrix').rglob('full-results-public-chunks/index.json'));parts=0
for index in indexes:
 required.add(str(index));document=json.loads(index.read_text())
 for part in document['parts']:required.add(str(index.parent/part['file']));parts+=1
assert not(required-set(files)),('Required primary public artifacts missing',sorted(required-set(files)))
assert all(pathlib.Path(name).is_file()for name in required)
receipt={'status':'PASS','wall_ns':time.time_ns(),'scope':'Metadata-only final native launcher history refresh; existing primary payload hashes retained','native_public_added':added,'native_public_updated':changed,'native_obsolete_paths_removed':removed,'required_primary_artifacts_checked':len(required),'chunk_indexes':len(indexes),'chunk_parts':parts,'primary_cells':480,'native_collection_complete':True}
q=H/'final-public-refresh.json';q.write_text(json.dumps(receipt,indent=2)+'\n')
for p in [q,pathlib.Path(__file__).resolve()]:files[str(p)]={'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
data['files']=list(files.values());data['omitted_files']=list(omitted.values());P.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({**receipt,'public_files':len(files),'omissions':len(omitted)}))
