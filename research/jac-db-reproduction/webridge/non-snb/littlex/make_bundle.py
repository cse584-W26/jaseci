#!/usr/bin/env python3
"""Combine independently generated API definitions without changing generated procedures."""
import pathlib,json,argparse,shutil,hashlib,time
H=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--cases',required=True,type=pathlib.Path,help='JSON mapping operation or operation/region to successful frozen case path');p.add_argument('--out',type=pathlib.Path);a=p.parse_args();cases=json.loads(a.cases.read_text());out=a.out or H/'bundles'/str(time.time_ns());out.mkdir(parents=True,exist_ok=False);(out/'generated/sql').mkdir(parents=True);operations={};sources=[];provenance=[]
for key,name in cases.items():
 c=pathlib.Path(name);m=json.loads((c/'metadata.json').read_text());api=m['api'];operations[key]=api;src=c/'generated/sql'/api;assert src.exists();shutil.copytree(src,out/'generated/sql'/api)
 for f in sorted(src.rglob('*')):
  if f.is_file():sources.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'copied_path':str(out/'generated/sql'/api/f.relative_to(src))})
 provenance.append({'operation':key,'case':str(c),'metadata_sha256':hashlib.sha256((c/'metadata.json').read_bytes()).hexdigest()})
 shutil.copy2(c/'aligned.conf',out/(api+'.conf'))
shutil.copy2(pathlib.Path(next(iter(cases.values())))/'aligned.conf',out/'aligned.conf')
(out/'metadata.json').write_text(json.dumps({'operations':operations,'sources':provenance,'generated_sources':sources},indent=2)+'\n');(out/'generated-sources.json').write_text(json.dumps([x['copied_path']for x in sources if x['path'].endswith('.sql')],indent=2)+'\n');print(out)
