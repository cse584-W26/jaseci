#!/usr/bin/env python3
"""Run retained generic graph programs through the original WeBridge lifecycle."""
import argparse,fcntl,hashlib,importlib.util,json,pathlib,subprocess,shutil
H=pathlib.Path(__file__).resolve().parent;E=H.parent;B=E.parent;I=B/'integration'
spec=importlib.util.spec_from_file_location('original_control',I/'control.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('action',choices=['build','baseline','record','replay','synth','optimized']);p.add_argument('--query',choices=['is1','is2','is3','ic1','ic2','ic13'],required=True);p.add_argument('--variant',choices=['full','pruned'],default='full');p.add_argument('--inputs',type=pathlib.Path,required=True);p.add_argument('--alignment-dir',type=pathlib.Path,default=B/'alignment');p.add_argument('--schema',type=pathlib.Path,default=B/'alignment/schema.sql');p.add_argument('--attempt',default='frozen');p.add_argument('--stack',default='20m');p.add_argument('--database',default='jac_snb_six_20261020');p.add_argument('--endpoint',default='127.0.0.1:55337');p.add_argument('--idx',type=int,default=0);p.add_argument('--repeats',type=int,default=1);p.add_argument('--graph',type=pathlib.Path);p.add_argument('--timeout',type=int,default=300);a=p.parse_args()
classes=H/'classes';classes.mkdir(exist_ok=True)
cp=':'.join([str(classes),str(I/'numeric-width/classes'),str(I/'jdbc-string/combined'),str(I/'sql-frontend/classes'),m.CP])
if (H/'frontend-current.json').exists():cp=json.loads((H/'frontend-current.json').read_text())['classes']+':'+cp
if a.action=='build':
 cmd=[str(B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(classes),*map(str,sorted(H.glob('*.java')))];r=subprocess.run(cmd,capture_output=True,text=True);(H/'build.json').write_text(json.dumps({'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'sources':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in H.glob('*.java')}},indent=2));raise SystemExit(r.returncode)
manifest={'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in sorted(H.glob('*.java'))},'class_sha256':{str(f.relative_to(classes)):hashlib.sha256(f.read_bytes()).hexdigest()for f in sorted(classes.rglob('*.class'))},'frontend_extension':json.loads((H/'frontend-current.json').read_text())if(H/'frontend-current.json').exists()else None,'inputs_sha256':hashlib.sha256(a.inputs.read_bytes()).hexdigest(),'schema_sha256':hashlib.sha256(a.schema.read_bytes()).hexdigest()}
bundle=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();snapshot=H/'snapshots'/bundle
if not snapshot.exists():
 (snapshot/'source').mkdir(parents=True);shutil.copytree(classes,snapshot/'classes')
 for source in H.glob('*.java'):shutil.copy2(source,snapshot/'source'/source.name)
 shutil.copy2(a.inputs,snapshot/'inputs.json');shutil.copy2(a.schema,snapshot/'compiler-schema.sql');(snapshot/'manifest.json').write_text(json.dumps(manifest,indent=2))
cp=cp.replace(str(classes)+':',str(snapshot/'classes')+':',1)
case=E/'webridge-cases'/f'{a.query}-{a.variant}-{bundle[:12]}-{a.attempt}';case.mkdir(parents=True,exist_ok=True);(case/'generated/sql').mkdir(parents=True,exist_ok=True);api='Snb_'+a.query+'_'+a.variant+'_'+hashlib.sha256(str(case).encode()).hexdigest()[:10]
config={'baseDir':str(case/'generated'),'target':'dummy','app.name':'jac_snb_extension','app.schema.init.sql':str(snapshot/'compiler-schema.sql'),'api.endpoint.name':api,'sp.baseDir':'${baseDir}','spdefs.path':'${sp.baseDir}/sql/'+api,'sp.path':'${sp.baseDir}/sql/'+api,'spcontext.path':'${sp.baseDir}/sql/context/'+api,'sqlgraph.path':'${sp.baseDir}/sql/graph/'+api,'sptracehash.path':'${baseDir}/trace'}
config_text='\n'.join(k+'='+v for k,v in config.items())+'\n'
metadata={'api':api,'variant':a.variant,'query':a.query,'bundle_sha256':bundle,'snapshot':str(snapshot),'manifest':manifest,'classpath':cp,'database':a.database,'endpoint':a.endpoint}
if (case/'metadata.json').exists():
 assert json.loads((case/'metadata.json').read_text())==metadata,'Frozen case metadata changed'
 assert (case/'aligned.conf').read_text()==config_text,'Frozen compiler config changed'
else:
 (case/'aligned.conf').write_text(config_text);(case/'metadata.json').write_text(json.dumps(metadata,indent=2))
if a.action=='record':assert not(case/('record-warm-'+str(a.idx)+'.bin')).exists(),'Choose --attempt to preserve existing capture'
out=case/(a.action+'-'+m.now());java=(m.ZERO if a.action=='replay' else B/'boot-jdk8' if a.action=='synth' else m.SERVER)/'bin/java'
cmd=[str(java),'-Xmx8g','-Xss'+a.stack,'-Dintegration.dir='+str(case),'-Dexecution.dir='+str(out),'-Dalignment.dir='+str(a.alignment_dir.resolve()),'-Daligned.source='+str(snapshot/'source/SnbAccess.java'),'-Dintegration.scope=warm','-Dintegration.api='+api,'-Dexperiment.inputs='+str(snapshot/'inputs.json'),'-Dexperiment.mysql.url=jdbc:mysql://'+a.endpoint+'/'+a.database+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true']
if a.variant=='pruned':cmd+=['-Dpruned.'+k+'=true' for k in ['auth','acl','schema','hydration']]
cmd+=['-cp',cp,'SnbWeBridge',a.action]+([str(a.graph.resolve())] if a.action=='synth' else [str(a.idx),str(a.repeats)])
m.LIMITS={'rss_bytes':12*1024**3,'output_bytes':8*1024**3}
if a.action=='optimized':
 overlay=json.loads((H/'gate-overlay-current.json').read_text());cmd[cmd.index('-cp')+1]=overlay['classes']+':'+cmd[cmd.index('-cp')+1];out.mkdir(parents=True,exist_ok=True);(out/'gate-overlay.json').write_text(json.dumps(overlay,indent=2))
 spec_w=importlib.util.spec_from_file_location('owned_watchdog',B/'benchmark-comparison/owned_watchdog.py');watchdog=importlib.util.module_from_spec(spec_w);spec_w.loader.exec_module(watchdog)
 with(I/'.mysql-sp-profile.lock').open('w')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);result=watchdog.run(cmd,out,timeout=a.timeout,request_limit=15)
 (out/'guard-result.json').write_text(json.dumps(result,indent=2))
 print(out)
 raise SystemExit(124 if result['timed_out']else 0)
if a.action=='replay':
 free=shutil.disk_usage(E).free
 (out if out.exists() else out.parent).mkdir(parents=True,exist_ok=True)
 if free<15*1024**3:raise RuntimeError('Native capture paused: free space below 15 GiB: '+str(free))
 with (I/'.engine-graph.lock').open('w') as lock:fcntl.flock(lock,fcntl.LOCK_EX);m.command(cmd,out,a.timeout)
else:m.command(cmd,out,a.timeout)
print(out)
