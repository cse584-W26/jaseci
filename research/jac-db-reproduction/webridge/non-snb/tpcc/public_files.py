#!/usr/bin/env python3
"""Generate an explicit public archive allowlist and retained omission inventory."""
import hashlib,json,pathlib,time
H=pathlib.Path(__file__).resolve().parent

def sha(path):
 digest=hashlib.sha256()
 with path.open('rb')as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
 return digest.hexdigest()

compression=H/'public-state-compression.json';compressed={r['source']for r in json.loads(compression.read_text())['files']}if compression.exists()else set()
included=[];omitted=[]
for path in sorted(H.rglob('*')):
 if not path.is_file()or path.name=='PUBLIC_FILES.json':continue
 relative=path.relative_to(H);parts=relative.parts;name=path.name
 if str(relative)in compressed:reason='Verified gzip copy selected; uncompressed SHA and decompression proof retained in public-state-compression.json'
 elif '__pycache__'in parts:reason='Rebuildable Python cache'
 elif any(p.startswith('relational-fixture')for p in parts):reason='Large source fixture; source SHA and import recipe retained separately'
 elif name=='graph-context.json':reason='Private fixture identity/mapping context; source hash retained in immutable metadata'
 elif name in ['record.bin','record.json','graph.json']or name.startswith('graph-')and path.suffix=='.json'and('generated'in parts or name not in ['graph-load.json','graph-reset.json']):reason='Serialized recorder/symbolic graph payload; stage receipt and SHA retained'
 elif path.suffix in ['.jar','.so','.tsv','.bin','.ser']:reason='Rebuildable binary/serialized fixture or compiler payload'
 elif path.suffix in ['.java','.py','.class','.sql','.json','.jsonl','.gz','.log','.txt','.conf','.md','.stdout','.stderr']or name in ['stdout','stderr']:reason=None
 else:reason='Unclassified; excluded until explicit review'
 entry={'path':str(relative),'bytes':path.stat().st_size,'sha256':sha(path)}
 if reason:entry['reason']=reason;omitted.append(entry)
 else:included.append(entry)
(H/'PUBLIC_FILES.json').write_text(json.dumps({'generated_wall_ns':time.time_ns(),'root':str(H),'included':included,'omitted':omitted,'policy':'Explicit allowlist; no authentication/identity TSVs, private graph fixture context, serialized records or symbolic graphs. Regenerate after final experiments.'},indent=2))
print(json.dumps({'included':len(included),'omitted':len(omitted)}))
