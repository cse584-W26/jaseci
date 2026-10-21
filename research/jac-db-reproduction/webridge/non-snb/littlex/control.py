#!/usr/bin/env python3
import contextlib
"""Content-addressed littleX source through the genuine WeBridge lifecycle."""
import argparse,fcntl,hashlib,importlib.util,json,pathlib,shutil,subprocess,sys
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];I=B/'integration'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('original',I/'control.py');lease=load('lease',H.parent/'measurement_lease.py').lease
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--lease-held',action='store_true');p.add_argument('action',choices=['build','baseline','record','replay','synth','optimized']);p.add_argument('--input',type=pathlib.Path);p.add_argument('--schema',type=pathlib.Path,default=H/'fixtures/t20/mysql-schema.sql');p.add_argument('--database',default='jac_lx_t20_20261020');p.add_argument('--attempt',default='original');p.add_argument('--graph',type=pathlib.Path);p.add_argument('--implementation',default='LittleXSql',choices=['LittleXSql','LittleXFull','LittleXPruned']);p.add_argument('--region',default='');p.add_argument('--timeout',type=int,default=300);a=p.parse_args()
classes=H/'classes';classes.mkdir(exist_ok=True);cp=':'.join([str(classes),str(I/'recorded-bind-types/classes'),str(I/'json-type-compat/classes'),str(I/'numeric-width/classes'),str(I/'jdbc-string/combined'),str(I/'sql-frontend/classes'),m.CP])
if a.action=='build':
 cmd=[str(B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(classes),*map(str,H.glob('*.java'))];r=subprocess.run(cmd,capture_output=True,text=True);(H/'build.json').write_text(json.dumps({'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'sources':{f.name:sha(f)for f in H.glob('*.java')}},indent=2));print(r.stderr);raise SystemExit(r.returncode)
assert a.input;build=json.loads((H/'build.json').read_text());assert build['returncode']==0
for name,expected in build.get('sources_sha256',build.get('sources')).items():assert sha(H/name)==expected,('Compile current sources before freezing case',name)
manifest={'source':{f.name:sha(f)for f in H.glob('*.java')},'classes':{f.name:sha(f)for f in classes.glob('*.class')},'input_sha256':sha(a.input),'schema_sha256':sha(a.schema),'implementation':a.implementation,'region':a.region,'templates_sha256':sha(H/'native-templates.json')};bundle=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();snapshot=H/'snapshots'/bundle
if not snapshot.exists():
 (snapshot/'source').mkdir(parents=True);shutil.copytree(classes,snapshot/'classes')
 for f in H.glob('*.java'):shutil.copy2(f,snapshot/'source'/f.name)
 shutil.copy2(H/'native-templates.json',snapshot/'native-templates.json');shutil.copy2(a.input,snapshot/'input.json');shutil.copy2(a.schema,snapshot/'schema.sql');(snapshot/'manifest.json').write_text(json.dumps(manifest,indent=2))
cp=cp.replace(str(classes)+':',str(snapshot/'classes')+':',1);case=H/'cases'/(a.input.stem+'-'+bundle[:12]+'-'+a.attempt);case.mkdir(parents=True,exist_ok=True);(case/'generated/sql').mkdir(parents=True,exist_ok=True);api='LittleX_'+hashlib.sha256(str(case).encode()).hexdigest()[:12]
config={'baseDir':str(case/'generated'),'target':'dummy','app.name':'jac_littlex','app.schema.init.sql':str(snapshot/'schema.sql'),'api.endpoint.name':api,'sp.baseDir':'${baseDir}','spdefs.path':'${sp.baseDir}/sql/'+api,'sp.path':'${sp.baseDir}/sql/'+api,'spcontext.path':'${sp.baseDir}/sql/context/'+api,'sqlgraph.path':'${sp.baseDir}/sql/graph/'+api,'sptracehash.path':'${baseDir}/trace'}
metadata={'api':api,'manifest':manifest,'snapshot':str(snapshot),'database':a.database,'classpath':cp,'implementation':a.implementation,'region':a.region};meta=case/'metadata.json'
if meta.exists():assert json.loads(meta.read_text())==metadata
else:meta.write_text(json.dumps(metadata,indent=2));(case/'aligned.conf').write_text('\n'.join(k+'='+v for k,v in config.items())+'\n')
if a.action=='record':assert not(case/'record.bin').exists(),'Preserve original capture with a new attempt'
out=case/(a.action+'-'+m.now());java=(m.ZERO if a.action=='replay'else B/'boot-jdk8'if a.action=='synth'else m.SERVER)/'bin/java';cmd=[str(java),'-Xmx8g','-Xss20m','-Dintegration.dir='+str(case),'-Dexecution.dir='+str(out),'-Dintegration.api='+api,'-Dintegration.scope=cold','-Daligned.source='+str(snapshot/'source/LittleXSql.java'),'-Dlittlex.implementation='+a.implementation,'-Dlittlex.region='+a.region,'-Dlittlex.templates='+str(snapshot/'native-templates.json'),'-Dexperiment.input='+str(snapshot/'input.json'),'-Dexperiment.mysql.url=jdbc:mysql://127.0.0.1:55337/'+a.database+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true&connectionCollation=utf8mb4_bin','-cp',cp,'LittleXWeBridge',a.action]+([str(a.graph.resolve())]if a.action=='synth'else[])
m.LIMITS={'rss_bytes':12*1024**3,'output_bytes':8*1024**3}
with(contextlib.nullcontext()if a.lease_held else lease('littlex-'+a.action,out.parent/(out.name+'-lease.json'))):
 if a.action in ['baseline','record','replay','optimized']:
  assert a.database in ['jac_lx_'+t+'_20261020'for t in ['t20','t50','t100','t200']]
  tier=a.database.split('_')[2];subprocess.run([sys.executable,str(H/'reset_relations.py'),tier,'--lease-held'],check=True)
 if a.action=='replay':
  assert shutil.disk_usage(H).free>15*1024**3
  with (I/'.engine-graph.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX);m.command(cmd,out,a.timeout)
 elif a.action=='optimized':
  w=load('watchdog',B/'benchmark-comparison/owned_watchdog.py')
  with (I/'.mysql-sp-profile.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX);result=w.run(cmd,out,timeout=a.timeout,request_limit=15,db=a.database)
  (out/'guard-result.json').write_text(json.dumps(result,indent=2));assert not result['timed_out'],'Generated transaction timed out'
 else:m.command(cmd,out,a.timeout)
print(out)
