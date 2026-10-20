#!/usr/bin/env python3
"""Original WeBridge lifecycle for conventional six-query Java reference."""
import pathlib,importlib.util,json,subprocess,sys,uuid,fcntl,hashlib,shutil
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];I=B/'integration';sp=importlib.util.spec_from_file_location('ctl',I/'control.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
q,action=sys.argv[1:3];assert q in ['is1','is2','is3','ic1','ic2','ic13'];case=I/'cases'/json.loads((H/'selected-cases.json').read_text())[q];meta=m.prepare_case(case,'cold');source_path=case/'source/SnbSetSql.java' if (case/'source/SnbSetSql.java').exists() else H/'SnbSetSql.java';current_hash=hashlib.sha256(source_path.read_bytes()).hexdigest();assert meta.get('source_sha256',current_hash)==current_hash,'Frozen case source hash differs';meta['query']=q;meta['source']='SnbSetSql';meta['request_scope']='Conventional trusted-input SQL/set-frontier reference; transaction commands outside original WeBridge recorded business region';meta['source_sha256']=current_hash;(case/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n');(case/'aligned.conf').write_text((case/'aligned.conf').read_text().replace(str(m.A/'schema.sql'),str(B/'expansion/fixture/compiler-schema.sql')))
snapshot=case/'source';snapshot.mkdir(exist_ok=True)
for name in ['SnbSetSql.java','SetWeBridge.java','SetTiming.java']:
 target=snapshot/name;current=H/name
 if not target.exists():shutil.copy2(current,target)
cp=':'.join([str(snapshot/'classes'),str(I/'recorded-bind-types/classes'),str(I/'json-type-compat/classes'),str(I/'numeric-width/classes'),str(I/'jdbc-string/combined'),m.CP]);(snapshot/'classes').mkdir(exist_ok=True)
subprocess.run([str(m.B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(snapshot/'classes'),str(snapshot/'SnbSetSql.java'),str(snapshot/'SetWeBridge.java'),str(snapshot/'SetTiming.java')],check=True)
if action=='record':assert not(case/'record-0.bin').exists(),'Preserve existing recording; create a fresh case for rerecording'
data=H/'runtime-data'/q;assert(data/'inputs.json').exists(),'Canonical source result gate must pass before creating runtime-data'
out=case/(action+'-'+m.now());out.mkdir();(out/'source-hashes.json').write_text(json.dumps({str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.rglob('*') if p.is_file()},indent=2)+'\n');java=(m.ZERO if action=='replay'else m.B/'boot-jdk8'if action=='synth'else m.SERVER)/'bin/java';cmd=[str(java),'-Xmx8g','-Xss20m',*(['-Dsnb.finiteDepth=true'] if q=='ic13' else []),*(['-Dsnb.branchTopk=true'] if q=='ic2' else []),'-Dsnb.query='+q,'-Dsnb.url=jdbc:mysql://127.0.0.1:55337/jac_snb_six_20261020?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true','-Dintegration.dir='+str(case),'-Dexecution.dir='+str(out),'-Dalignment.dir='+str(data),'-Daligned.source='+str(snapshot/'SnbSetSql.java'),'-Dintegration.scope=cold','-Dintegration.api='+meta['api'],'-cp',cp,'SetWeBridge',action];cmd+=sys.argv[3:]if action=='synth'else['0'];m.LIMITS={'rss_bytes':12*1024**3,'output_bytes':8*1024**3}
if action=='replay':
 assert shutil.disk_usage(B).free>=15*1024**3,'Below15GiBdiskheadroom: notify coordinator andhold capture'
 with(I/'.engine-graph.lock').open('w')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);g=pathlib.Path('/tmp/webridgeMngr.tmp.sp.string');before=g.stat().st_mtime_ns if g.exists() else None
  try:m.command(cmd,out,300)
  finally:
   if g.exists() and g.stat().st_mtime_ns!=before and not(out/'graph.json').exists():
    info={'bytes':g.stat().st_size,'mtime_ns':g.stat().st_mtime_ns,'note':'Native global output updated but Java frontend returned no retained graph'}
    if g.stat().st_size<=4*1024**3 and shutil.disk_usage(B).free>=15*1024**3+g.stat().st_size:
     shutil.copy2(g,out/'native-graph-before-java-return.json');info['preserved']=True
    else:info['preserved']=False;info['hold_next_capture_for_coordinator']=True
    (out/'native-output-receipt.json').write_text(json.dumps(info,indent=2)+'\n')
elif action=='optimized':
 with(I/'.mysql-sp-profile.lock').open('w')as lock:fcntl.flock(lock,fcntl.LOCK_EX);m.command(cmd,out,300)
else:m.command(cmd,out,300)
print(out)
