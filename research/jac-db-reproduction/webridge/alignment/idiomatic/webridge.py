#!/usr/bin/env python3
import pathlib,importlib.util,subprocess,json,sys,fcntl
H=pathlib.Path(__file__).resolve().parent;I=H.parents[1]/'integration';spec=importlib.util.spec_from_file_location('ctl',I/'control.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
case=I/'cases/idiomatic-small-20261020';meta=m.prepare_case(case,'cold');config=(case/'aligned.conf').read_text().replace(str(m.A/'schema.sql'),str(m.A/'small-diagnostic/runtime-data/schema.sql'));(case/'aligned.conf').write_text(config)
cp=':'.join([str(H/'webridge-classes'),str(I/'numeric-width/classes'),str(I/'jdbc-string/combined'),m.CP]);(H/'webridge-classes').mkdir(exist_ok=True)
subprocess.run([str(m.B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(H/'webridge-classes'),str(H/'IdiomaticRegion.java'),str(H/'IdiomaticWeBridge.java')],check=True)
a=sys.argv[1];out=case/(a+'-'+m.now());java=(m.ZERO if a=='replay' else m.B/'boot-jdk8' if a=='synth' else m.SERVER)/'bin/java';cmd=[str(java),'-Xmx8g','-Xss20m','-Didiomatic.sql='+str(H/'ic5.sql'),'-Dintegration.dir='+str(case),'-Dexecution.dir='+str(out),'-Dalignment.dir='+str(m.A/'small-diagnostic/runtime-data'),'-Daligned.source='+str(H/'IdiomaticRegion.java'),'-Dintegration.scope=cold','-Dintegration.api='+meta['api'],'-cp',cp,'IdiomaticWeBridge',a]
cmd+=sys.argv[2:] if a=='synth' else [sys.argv[2] if len(sys.argv)>2 else '0','1'];m.LIMITS={'rss_bytes':12*1024**3,'output_bytes':8*1024**3}
if a=='replay':
 with (I/'.engine-graph.lock').open('w') as lock:fcntl.flock(lock,fcntl.LOCK_EX);m.command(cmd,out,300)
else:m.command(cmd,out,300)
print(out)
