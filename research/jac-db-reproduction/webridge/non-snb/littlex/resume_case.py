#!/usr/bin/env python3
import contextlib
"""Run subsequent genuine stages from immutable captured bytecode and source metadata."""
import pathlib,json,argparse,importlib.util,fcntl,shutil,subprocess,sys,hashlib
H=pathlib.Path(__file__).resolve().parent;W=H.parents[1];I=W/'integration'
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
c=load('c',I/'control.py');lease=load('lease',H.parent/'measurement_lease.py').lease
p=argparse.ArgumentParser();p.add_argument('--lease-held',action='store_true');p.add_argument('action',choices=['record','replay','synth','optimized','baseline']);p.add_argument('case',type=pathlib.Path);p.add_argument('--graph',type=pathlib.Path);p.add_argument('--overlay',type=pathlib.Path);a=p.parse_args();case=a.case.resolve();
if a.action=='record':assert not(case/'record.bin').exists(),'Preserve original record'
meta=json.loads((case/'metadata.json').read_text());snapshot=pathlib.Path(meta['snapshot']);out=case/(a.action+'-'+c.now());java=(c.ZERO if a.action=='replay'else W/'boot-jdk8'if a.action=='synth'else c.SERVER)/'bin/java';cp=meta['classpath'];cp=str(a.overlay.resolve())+':'+cp if a.overlay else cp
cmd=[str(java),'-Xmx8g','-Xss20m','-Dintegration.dir='+str(case),'-Dexecution.dir='+str(out),'-Dintegration.api='+meta['api'],'-Dintegration.scope=cold','-Daligned.source='+str(snapshot/'source/LittleXSql.java'),'-Dlittlex.implementation='+meta.get('implementation','LittleXSql'),'-Dlittlex.region='+meta.get('region',''),'-Dlittlex.templates='+str(snapshot/'native-templates.json'),'-Dexperiment.input='+str(snapshot/'input.json'),'-Dexperiment.mysql.url=jdbc:mysql://127.0.0.1:55337/'+meta['database']+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true&connectionCollation=utf8mb4_bin','-cp',cp,'LittleXWeBridge',a.action]+([str(a.graph.resolve())]if a.action=='synth'else[])
c.LIMITS={'rss_bytes':12*1024**3,'output_bytes':8*1024**3}
with(contextlib.nullcontext()if a.lease_held else lease('littlex frozen '+a.action,out.parent/(out.name+'-lease.json'))):
 if a.action in ['record','replay','optimized','baseline']:subprocess.run([sys.executable,str(H/'reset_relations.py'),meta['database'].split('_')[2],'--lease-held'],check=True)
 if a.action=='replay':
  assert shutil.disk_usage(H).free>15*1024**3
  with(I/'.engine-graph.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX);c.command(cmd,out,300)
 elif a.action=='optimized':
  wd=load('wd',W/'benchmark-comparison/owned_watchdog.py')
  with(I/'.mysql-sp-profile.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX);r=wd.run(cmd,out,timeout=60,request_limit=15,db=meta['database']);(out/'guard-result.json').write_text(json.dumps(r,indent=2));assert not r['timed_out'],'Generated request censored'
 else:
  try:c.command(cmd,out,300)
  finally:
   if a.action=='synth' and out.exists():
    generated=case/'generated/sql'
    if generated.exists():
     shutil.copytree(generated,out/'emitted-sql-snapshot');(out/'emitted-sql-sha256.json').write_text(json.dumps({str(f.relative_to(generated)):hashlib.sha256(f.read_bytes()).hexdigest()for f in generated.rglob('*')if f.is_file()},indent=2)+'\n')
    if a.overlay:(out/'frontend-overlay-sha256.json').write_text(json.dumps({str(f.relative_to(a.overlay)):hashlib.sha256(f.read_bytes()).hexdigest()for f in a.overlay.rglob('*')if f.is_file()},indent=2)+'\n')
print(out)
