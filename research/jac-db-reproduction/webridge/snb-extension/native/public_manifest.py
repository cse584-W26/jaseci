"""Explicit payload-free native experiment archive whitelist."""
import pathlib,json,hashlib
R=pathlib.Path(__file__).resolve().parent;files=[]
for p in sorted(R.rglob('*')):
 if not p.is_file()or'__pycache__'in p.parts or p.name in ['PUBLIC_FILES.json','events.jsonl']:continue
 if p.suffix in ['.py','.md','.json','.jsonl']or p.name.endswith('.log.gz')or p.name=='events.jsonl.gz':files.append({'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(R/'PUBLIC_FILES.json').write_text(json.dumps({'root':str(R),'files':files,'raw_protocol_binary_private':True,'frame_event_metadata_payload_free':True},indent=2));print(len(files),sum(x['bytes']for x in files))
