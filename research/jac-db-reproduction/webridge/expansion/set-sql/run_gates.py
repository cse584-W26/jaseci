#!/usr/bin/env python3
import pathlib,subprocess,json,hashlib,time,sys,os,shlex
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];I=B/'integration';catalog=B/'snb-extension/inputs-all20.json';classes=H/'classes';classes.mkdir(exist_ok=True);cp=':'.join(map(str,[classes,B/'deps/mysql-connector-java-5.1.46.jar',B/'deps/fastjson2-2.0.9.jar']))
subprocess.run([str(B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(classes),str(H/'SnbSetSql.java')],check=True)
java=B.parents[1]/'webridge/SourceCode/openjdk8-webridge/build/linux-x86_64-normal-server-release/images/j2sdk-image/bin/java';root=H/('gates-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));root.mkdir();(root/'SnbSetSql.java').write_bytes((H/'SnbSetSql.java').read_bytes());(root/'source-sha256.json').write_text(json.dumps({'source':hashlib.sha256((H/'SnbSetSql.java').read_bytes()).hexdigest(),'catalog':hashlib.sha256(catalog.read_bytes()).hexdigest()}));summary={}
for q in sys.argv[1:]or['is1','is2','is3','ic1','ic2','ic13']:
 cmd=['taskset','-c','9,19',str(java),'-Xmx4g',*(['-Dsnb.finiteDepth=true'] if q=='ic13' else []),*(['-Dsnb.branchTopk=true'] if q=='ic2' else []),*shlex.split(os.environ.get('SNB_JAVA_FLAGS','')),'-cp',cp,'SnbSetSql',q,str(catalog),str(root/q)];(root/(q+'-command.json')).write_text(json.dumps(cmd))
 with (root/(q+'.log')).open('w')as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 rr=[]
 if(root/q/'rows.jsonl').exists():
  for line in(root/q/'rows.jsonl').read_text().splitlines():
   x=json.loads(line);actual=hashlib.sha256(json.dumps(x['result'],sort_keys=True).encode()).hexdigest();rr.append({'idx':x['idx'],'pass':actual==x['expected_canonical_sha256'],'actual':actual,'expected':x['expected_canonical_sha256'],'calls':x['source_calls']})
 summary[q]={'returncode':p.returncode,'rows':rr,'all20pass':len(rr)==20 and all(x['pass']for x in rr)};(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(q,summary[q]['all20pass'],flush=True)
print(root)
