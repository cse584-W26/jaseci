#!/usr/bin/env python3
"""Freeze one verified source/bytecode/template build for repeatable profile factories."""
import pathlib,json,hashlib,shutil
H=pathlib.Path(__file__).resolve().parent;p=H/'build.json';receipt=json.loads(p.read_text());assert receipt['returncode']==0;sources=receipt.get('sources_sha256',receipt.get('sources'));assert sources
for name,sha in sources.items():assert hashlib.sha256((H/name).read_bytes()).hexdigest()==sha,(name,'source differs from compiled manifest')
for name,expected in receipt.get('classes_sha256',{}).items():assert hashlib.sha256((H/'classes'/name).read_bytes()).hexdigest()==expected,(name,'bytecode differs from compiled manifest')
key=hashlib.sha256(p.read_bytes()).hexdigest();out=H/'build-snapshots'/key
if not out.exists():
 (out/'source').mkdir(parents=True);shutil.copytree(H/'classes',out/'classes')
 for name in sources:shutil.copy2(H/name,out/'source'/name)
 for name in ['build.json','native-templates.json']:shutil.copy2(H/name,out/name)
 (out/'snapshot-sha256.json').write_text(json.dumps({str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest()for f in out.rglob('*')if f.is_file()},indent=2)+'\n')
print(out)
