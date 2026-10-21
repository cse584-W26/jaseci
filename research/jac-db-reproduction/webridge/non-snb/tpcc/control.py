#!/usr/bin/env python3
"""Content-addressed TPC-C source through the genuine WeBridge lifecycle."""
from contextlib import nullcontext
import argparse,fcntl,hashlib,importlib.util,json,pathlib,shutil,subprocess
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];I=B/'integration'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('original',I/'control.py');lease=load('lease',H.parent/'measurement_lease.py').lease
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('action',choices=['build','baseline','record','replay','synth','optimized']);p.add_argument('--input',type=pathlib.Path);p.add_argument('--program',choices=['conventional','graph'],default='conventional');p.add_argument('--variant',choices=['full','pruned'],default='full');p.add_argument('--schema',type=pathlib.Path,default=H/'relational-schema.sql');p.add_argument('--database',default='jac_tpcc_conventional');p.add_argument('--attempt',default='original');p.add_argument('--graph',type=pathlib.Path);p.add_argument('--timeout',type=int,default=300);p.add_argument('--lease-held',action='store_true');p.add_argument('--compat-cp',default='');a=p.parse_args()
classes=H/'classes';classes.mkdir(exist_ok=True);cp=':'.join([str(classes),str(I/'numeric-width/classes'),str(I/'jdbc-string/combined'),str(I/'sql-frontend/classes'),m.CP])
if a.action=='build':
 cmd=[str(B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(classes),*map(str,H.glob('*.java'))];r=subprocess.run(cmd,capture_output=True,text=True);(H/'build.json').write_text(json.dumps({'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'sources':{f.name:sha(f)for f in H.glob('*.java')}},indent=2));print(r.stderr);raise SystemExit(r.returncode)
assert a.input
assert json.loads((H/'build.json').read_text())['sources']=={f.name:sha(f)for f in H.glob('*.java')},'Java sources changed after recorded build; rebuild before capturing'
compat=[pathlib.Path(p).resolve()for p in a.compat_cp.split(':')if p];compat_manifest=[{str(f.relative_to(d)):sha(f)for f in sorted(d.rglob('*.class'))}for d in compat]
manifest={'session_configuration':{'no_unsigned_subtraction':True,'preserve_existing_strict_modes':True,'isolation':'SERIALIZABLE','read_only':False},'transaction_dialect':'JDBC setAutoCommit(false)/setAutoCommit(true); real rollback plus connection restore on invalid-item abort','compatibility_classes':compat_manifest,'source':{f.name:sha(f)for f in H.glob('*.java')},'classes':{f.name:sha(f)for f in classes.glob('*.class')},'input_sha256':sha(a.input),'schema_sha256':sha(a.schema),'program':a.program,'variant':a.variant,'graph_context_sha256':sha(H/'graph-context.json')if a.program=='graph'else None,'fixture_manifest_sha256':sha(H.parent/'native/tpcc-fixture/export.json')if a.program=='graph'else sha(H/'relational-fixture-jac-seed/manifest.json')};bundle=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();snapshot=H/'snapshots'/bundle
if not snapshot.exists():
 (snapshot/'source').mkdir(parents=True);shutil.copytree(classes,snapshot/'classes')
 for f in H.glob('*.java'):shutil.copy2(f,snapshot/'source'/f.name)
 
 if a.program=='graph':shutil.copy2(H/'graph-context.json',snapshot/'graph-context.json')
 
 for index,directory in enumerate(compat):shutil.copytree(directory,snapshot/'compatibility'/str(index))
 shutil.copy2(a.input,snapshot/'input.json');shutil.copy2(a.schema,snapshot/'schema.sql');(snapshot/'manifest.json').write_text(json.dumps(manifest,indent=2))
cp=cp.replace(str(classes)+':',str(snapshot/'classes')+':',1);cp=':'.join([str(snapshot/'compatibility'/str(i))for i in range(len(compat))]+[cp]);case=H/'cases'/(a.program+'-'+a.variant+'-'+a.input.stem+'-'+bundle[:12]+'-'+a.attempt);case.mkdir(parents=True,exist_ok=True);(case/'generated/sql').mkdir(parents=True,exist_ok=True);api='Tpcc_'+hashlib.sha256(str(case).encode()).hexdigest()[:12]
config={'baseDir':str(case/'generated'),'target':'dummy','app.name':'jac_tpcc','app.schema.init.sql':str(snapshot/'schema.sql'),'api.endpoint.name':api,'sp.baseDir':'${baseDir}','spdefs.path':'${sp.baseDir}/sql/'+api,'sp.path':'${sp.baseDir}/sql/'+api,'spcontext.path':'${sp.baseDir}/sql/context/'+api,'sqlgraph.path':'${sp.baseDir}/sql/graph/'+api,'sptracehash.path':'${baseDir}/trace'}
metadata={'api':api,'manifest':manifest,'snapshot':str(snapshot),'database':a.database,'classpath':cp,'program':a.program,'variant':a.variant};meta=case/'metadata.json'
if meta.exists():assert json.loads(meta.read_text())==metadata
else:meta.write_text(json.dumps(metadata,indent=2));(case/'aligned.conf').write_text('\n'.join(k+'='+v for k,v in config.items())+'\n')
if a.action=='record':assert not(case/'record.bin').exists(),'Preserve original capture with a new attempt'
out=case/(a.action+'-'+m.now());java=(m.ZERO if a.action=='replay'else B/'boot-jdk8'if a.action=='synth'else m.SERVER)/'bin/java';cmd=[str(java),'-Xmx8g','-Xss20m','-Dintegration.dir='+str(case),'-Dexecution.dir='+str(out),'-Dintegration.api='+api,'-Dintegration.scope=cold','-Daligned.source='+str(snapshot/'source/TpccSql.java'),'-Dexperiment.input='+str(snapshot/'input.json'),'-Dexperiment.program='+a.program,'-Dexperiment.pruned='+str(a.variant=='pruned').lower(),'-Dexperiment.graph.context='+str(snapshot/'graph-context.json'),'-Dexperiment.mysql.url=jdbc:mysql://127.0.0.1:55337/'+a.database+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true','-cp',cp,'TpccWeBridge',a.action]+([str(a.graph.resolve())]if a.action=='synth'else[])
m.LIMITS={'rss_bytes':12*1024**3,'output_bytes':8*1024**3}
with (nullcontext()if a.lease_held else lease('tpcc-'+a.action,out.parent/(out.name+'-lease.json'))):
 if a.action=='replay':
  assert shutil.disk_usage(H).free>15*1024**3
  with (I/'.engine-graph.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX);m.command(cmd,out,a.timeout)
 elif a.action=='optimized':
  w=load('watchdog',B/'benchmark-comparison/owned_watchdog.py')
  with (I/'.mysql-sp-profile.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX);result=w.run(cmd,out,timeout=a.timeout,request_limit=15,db=a.database)
  (out/'guard-result.json').write_text(json.dumps(result,indent=2));assert not result['timed_out'],'Generated transaction timed out'
 else:m.command(cmd,out,a.timeout)
print(out)
