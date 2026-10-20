#!/usr/bin/env python3
"""Scripted compilation and conventional-JDBC correctness/timing runs."""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1];WORK=B.parents[1]
a=argparse.ArgumentParser();a.add_argument('mode',choices=['gate','time']);a.add_argument('--out',type=Path,required=True);a.add_argument('--url',default='jdbc:mysql://127.0.0.1:55337/jac_alignment_utf8?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true');a.add_argument('--warm',type=int,default=10);a.add_argument('--measure',type=int,default=30);args=a.parse_args();assert not args.out.exists()
classes=H/'classes';classes.mkdir(exist_ok=True);deps=[B/'deps/mysql-connector-java-5.1.46.jar',B/'deps/fastjson2-2.0.9.jar'];cp=':'.join(map(str,[classes,*deps]));subprocess.run(['taskset','-c','0-3,10-13',str(B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(classes),str(H/'IdiomaticIc5.java')],check=True)
java=WORK/'webridge/SourceCode/openjdk8-webridge/build/linux-x86_64-normal-server-release/images/j2sdk-image/bin/java';cmd=['taskset','-c','9,19',str(java),'-Didiomatic.sql='+str(H/'ic5.sql'),'-Didiomatic.jdbcUrl='+args.url,'-cp',cp,'IdiomaticIc5',args.mode,str(H.parent),str(args.out.resolve()),str(args.warm),str(args.measure)]
args.out.parent.mkdir(parents=True,exist_ok=True);log=args.out.parent/(args.out.name+'.driver.log');started=time.time()
with log.open('wb') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
if args.out.exists():(args.out/'provenance.json').write_text(json.dumps({'command':cmd,'started_unix':started,'ended_unix':time.time(),'returncode':p.returncode,'source_sha256':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [H/'IdiomaticIc5.java',H/'ic5.sql',*deps]},'timer':'System.nanoTime around BEGIN/SET/query/read rows/COMMIT; same current-thread CPU API as WarmTiming','auth':'Conventional trusted-input SQL baseline omits Jac identity/ACL/schema/hydration services'},indent=2)+'\n')
print(args.out,flush=True);raise SystemExit(p.returncode)
