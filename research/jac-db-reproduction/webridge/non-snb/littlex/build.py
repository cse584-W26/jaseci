#!/usr/bin/env python3
"""Compile an immutable Java source input set and record its exact class hashes."""
import pathlib,importlib.util,subprocess,json,hashlib,time,shutil
H=pathlib.Path(__file__).resolve().parent;W=H.parents[1];s=importlib.util.spec_from_file_location('c',W/'integration/control.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c);sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in H.glob('*.java')};key=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest();src=H/'build-inputs'/key
if not src.exists():
 src.mkdir(parents=True)
 for name in sources:shutil.copy2(H/name,src/name)
for name,sha in sources.items():assert hashlib.sha256((src/name).read_bytes()).hexdigest()==sha
out=H/'classes';out.mkdir(exist_ok=True);cmd=['taskset','-c','9,19',str(c.SERVER/'bin/javac'),'-cp',c.CP,'-d',str(out),*map(str,sorted(src.glob('*.java')))];r=subprocess.run(cmd,capture_output=True,text=True);changed=[name for name,sha in sources.items()if hashlib.sha256((H/name).read_bytes()).hexdigest()!=sha];receipt={'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'sources_sha256':sources,'immutable_source_directory':str(src),'source_changed_during_build':changed,'classes_sha256':{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*.class')},'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())};(H/'build.json').write_text(json.dumps(receipt,indent=2));print(r.stdout+r.stderr);assert not changed,changed;raise SystemExit(r.returncode)
