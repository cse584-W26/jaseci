"""List the public native reproduction artifacts; payload and credential files remain local."""
import json,pathlib,sys
R=pathlib.Path(__file__).resolve().parent
include=[];omitted=[]
for p in sorted(R.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(R);parts=rel.parts
 reason=None
 if '__pycache__'in parts or p.suffix=='.pyc':reason='interpreter cache'
 elif parts[0]in ('baseline','final'):reason='mutable live application, private targets and credentials; frozen sources/launches retained per attempt'
 elif parts[0]=='tpcc-fixture':reason='private full graph and identity export; public export receipt retained separately'
 elif p.name=='rows.jsonl.gz'and(p.parent/'rows.chunks.json').exists():reason='line-preserving public chunks/index retain exact logical raw JSONL; monolith remains collection-local'
 elif p.name=='events.jsonl'and(p.parent/'events.jsonl.gz').exists():reason='exact frame/chunk metadata retained as deterministic public gzip with streaming hash receipt'
 elif p.suffix=='.bin':reason='private PostgreSQL payload capture; frame metadata retained'
 elif any(x in ('tokens','targets','identity_users.tsv','identity_lookups.tsv')for x in parts):reason='authentication or identity payload'
 elif p.name in ('PUBLIC_FILES.json','OMITTED_FILES.json'):continue
 elif p.suffix in ('.py','.md','.json','.jsonl','.gz','.sql','.log','.jac','.stdout','.txt'):
  include.append(str(rel));continue
 else:reason='collection-local process/control artifact'
 omitted.append({'path':str(rel),'bytes':p.stat().st_size,'reason':reason})
include=sorted(set(include+['PUBLIC_FILES.json','OMITTED_FILES.json']))
(R/'PUBLIC_FILES.json').write_text(json.dumps(include,indent=2)+'\n')
(R/'OMITTED_FILES.json').write_text(json.dumps(omitted,indent=2)+'\n')
oversize=[{'path':x,'bytes':(R/x).stat().st_size}for x in include if(R/x).stat().st_size>90*1024**2];print(json.dumps({'public':len(include),'omitted':len(omitted),'public_over_90MiB':oversize}));assert '--strict'not in sys.argv or not oversize,oversize
