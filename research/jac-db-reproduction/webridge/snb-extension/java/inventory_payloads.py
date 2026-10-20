#!/usr/bin/env python3
"""Retain exact size/SHA receipts for large/identity-bearing native payloads omitted from Git."""
import hashlib,json,pathlib
H=pathlib.Path(__file__).resolve().parent;E=H.parent;rows=[]
for case in sorted((E/'webridge-cases').iterdir()):
 if not case.is_dir():continue
 for path in sorted(case.rglob('*')):
  if not path.is_file()or not(path.name=='graph.json'or path.name.startswith('record-')and path.suffix=='.bin'):continue
  h=hashlib.sha256()
  with path.open('rb')as f:
   for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
  rows.append({'path':str(path),'bytes':path.stat().st_size,'sha256':h.hexdigest(),'kind':'original_native_graph'if path.name=='graph.json'else'original_JDBC_recording','git_payload_policy':'SHA receipt retained; binary/native result payload omitted; may contain fixed fixture identity documents'})
(H/'native-payload-inventory.json').write_text(json.dumps(rows,indent=2));print(len(rows),'payloads',sum(x['bytes']for x in rows),'bytes')
