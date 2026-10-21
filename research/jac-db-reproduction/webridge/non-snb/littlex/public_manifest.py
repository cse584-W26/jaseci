#!/usr/bin/env python3
"""Inventory public evidence and every omitted payload; run outside quiet windows."""
import pathlib,json,hashlib,gzip,shutil
H=pathlib.Path(__file__).resolve().parent;files=[];omitted=[]
required_scope_evidence={str(H/'native/census'/stamp/name)for stamp in ['20261020T232351Z-baseline','20261020T233449Z-final']for name in ['sql-census.json',*[f'feed/profile-{i}.log.gz'for i in range(3)]]}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
for p in sorted(H.rglob('*')):
 if not p.is_file()or p.name=='PUBLIC_FILES.json':continue
 r=p.relative_to(H);n=p.stat().st_size;reason=None
 if '__pycache__'in r.parts:reason='rebuildable Python bytecode'
 elif p.suffix=='.tsv':reason='private fixture or projected-row payload'
 elif p.suffix=='.bin':reason='private original WeBridge serialized result-set payload'
 elif p.name.endswith(('-seed-oracles.json','-gate-inputs.json')):reason='private seed-derived identity input catalog'
 elif p.name in ['graph.json','recorded-resultsets.json']:reason='private symbolic graph or recorded row payload'
 elif p.suffix=='.class'and'snapshots'not in r.parts and'build-snapshots'not in r.parts:reason='rebuildable current Java class; frozen capture classes retained'
 if str(p)in required_scope_evidence:reason=None
 if reason:
  omitted.append({'path':str(p),'bytes':n,'reason':reason,'sha256':sha(p)if n<16*1024**2 else None,'hash_scope':'compact payload'if n<16*1024**2 else'large local payload; source receipt records hash when available'});continue
 if p.name=='full-results.jsonl.gz'and n>80*1024**2:
  from result_chunks import export
  indexpath=export(p,p.with_name('full-results-public-chunks'));index=json.loads(indexpath.read_text())
  for chunk in [indexpath,*[indexpath.parent/x['file']for x in index['parts']]]:files.append({'path':str(chunk),'bytes':chunk.stat().st_size,'sha256':sha(chunk)})
  omitted.append({'path':str(p),'bytes':n,'reason':'lossless ordered complete-response public chunks','sha256':index['source_sha256'],'public_index':str(indexpath)});continue
 # Large raw diagnostics are included with deterministic gzip encoding.
 if n>10*1024**2 and p.suffix not in ['.gz','.zip']:
  z=p.with_name(p.name+'.public.gz')
  # Refresh derived gzip when an append-only diagnostic has changed.
  with p.open('rb')as src,z.open('wb')as dst,gzip.GzipFile(filename='',fileobj=dst,mode='wb',mtime=0)as out:shutil.copyfileobj(src,out,1024*1024)
  omitted.append({'path':str(p),'bytes':n,'reason':'public lossless compressed counterpart','sha256':sha(p),'public_path':str(z)});p=z;n=z.stat().st_size
 files.append({'path':str(p),'bytes':n,'sha256':sha(p)})
unique={r['path']:r for r in files}
assert required_scope_evidence<=set(unique),('Required scope evidence missing',sorted(required_scope_evidence-set(unique)))
(H/'PUBLIC_FILES.json').write_text(json.dumps({'files':list(unique.values()),'omitted_files':omitted,'required_scope_evidence':sorted(required_scope_evidence),'scope':'frozen source/bytecode, generated SQL, raw timing/protocol/state and lifecycle receipts; payload omissions individually inventoried'},indent=2)+'\n')
print('Public files',len(unique),'omissions',len(omitted))
