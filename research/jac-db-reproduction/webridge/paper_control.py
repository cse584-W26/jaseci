#!/usr/bin/env python3
"""Scripted lifecycle for the original My-Blog/WeBridge experiment."""
import argparse,json,os,signal,subprocess,time,urllib.request,hashlib,shutil
from pathlib import Path
R=Path(__file__).resolve().parent; W=R.parents[1]/'webridge'; P=R/'paper'; P.mkdir(exist_ok=True)
ZERO=W/'SourceCode/openjdk8-webridge/build/linux-x86_64-normal-zero-release/images/j2sdk-image'
SERVER=W/'SourceCode/openjdk8-webridge/build/linux-x86_64-normal-server-release/images/j2sdk-image'
APP=W/'Application/my-blog'; JAR=APP/'target/my-blog-4.0.0-SNAPSHOT.jar'
GEN=P/'generated'; GEN.mkdir(exist_ok=True)
def event(kind,**d):
 with (P/'control-events.jsonl').open('a') as f:f.write(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'kind':kind,**d})+'\n')
def env():
 e=os.environ.copy();e['LD_LIBRARY_PATH']=str(R/'native-lib');e['PATH']=str(R/'bin')+':'+str(R/'apache-maven-3.8.8/bin')+':'+e['PATH'];return e
def stop(name):
 p=P/(name+'.pid')
 if not p.exists():return
 pid=int(p.read_text())
 try:
  cmd=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
  if str(R) not in cmd and str(W) not in cmd:raise RuntimeError('Foreign process: '+cmd)
  os.killpg(pid,signal.SIGTERM)
  for _ in range(200):
   try:
    state=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]
    if state=='Z':break
   except FileNotFoundError:break
   time.sleep(.1)
  else:raise RuntimeError('Owned process did not stop: '+str(pid))
 except (FileNotFoundError,ProcessLookupError):pass
 p.unlink();event('stop',service=name,pid=pid)
def launch(name,cmd,cwd):
 stop(name);cwd.mkdir(exist_ok=True,parents=True)
 cpu='0-3,10-13' if name=='online' else '9,19'
 cmd=['taskset','-c',cpu,*cmd]
 log=P/(name+'-'+time.strftime('%Y%m%dT%H%M%S',time.gmtime())+'.log')
 with log.open('wb') as f:proc=subprocess.Popen(cmd,cwd=cwd,env=env(),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 (P/(name+'.pid')).write_text(str(proc.pid));event('start',service=name,pid=proc.pid,command=cmd,cwd=str(cwd),log=str(log))
 return proc,log
def ready(proc,url,log,seconds=180):
 for _ in range(seconds):
  if proc.poll() is not None:raise RuntimeError('Exited; see '+str(log))
  try:
   with urllib.request.urlopen(url,timeout=2) as res:
    if res.status==200:return
  except Exception:pass
  time.sleep(1)
 raise RuntimeError('Not ready; see '+str(log))
def configure(mode):
 offline=mode=='offline';d=P/('offline' if offline else 'online');d.mkdir(exist_ok=True)
 values={
 'server.address':'127.0.0.1','server.port':'19099' if offline else '19080',
 'spring.datasource.url':'jdbc:mysql://127.0.0.1:55325/my_blog_db?useUnicode=true&characterEncoding=utf8&autoReconnect=true&useSSL=false&serverTimezone=UTC&useLocalSessionState=true&readOnlyPropagatesToServer=false',
 'spring.datasource.username':'webridge','spring.datasource.password':'webridge-local',
 'spdef.dir':str(GEN/'sql'),'recorder.threshold':'20',
 'webridge.enable.concolic.execution':str(offline).lower(),
 'trace.sql.enable':str(mode=='train').lower(),
 'webridge.use.sp':str(mode=='optimized').lower(),
 'webridge.use.sp.warmup':'5','webridge.profile.hit_rate':'false',
 'webridge.offline.compiler.enable':str(mode=='train').lower(),
 'webridge.offline.compiler.host':'127.0.0.1',
 'db.jdbcUrl':'jdbc:mysql://127.0.0.1:55325/my_blog_db',
 'db.user':'webridge','db.password':'webridge-local'}
 (d/'application.properties').write_text('\n'.join(k+'='+v for k,v in values.items())+'\n')
 event('configure',mode=mode,overrides=values,jar_sha256=hashlib.sha256(JAR.read_bytes()).hexdigest())
 return d
def start(mode):
 d=configure(mode);offline=mode=='offline';java=ZERO if offline else SERVER
 cmd=[str(java/'bin/java'),'-Xmx16g','-Xss20m','-Djava.security.policy='+str(W/'SourceCode/webridge-common/webridge.policy'),'-jar',str(JAR)]
 proc,log=launch('offline' if offline else 'online',cmd,d)
 # /webridge/hi requires no database queries and does not trigger compilation.
 ready(proc,'http://127.0.0.1:'+('19099' if offline else '19080')+'/webridge/hi',log)
 if offline:
  with urllib.request.urlopen('http://127.0.0.1:19099/admin/blogs/list?page=1&limit=10',timeout=60) as response: response.read()
  event('offline_pool_warmup',uri='/admin/blogs/list?page=1&limit=10',reason='initialize pool before concolic API replay to keep connection setup outside hot paths')
 print('Ready',mode,proc.pid,log,flush=True)
def compiler():
 cp=':'.join([str(R/'classes'),str(W/'SourceCode/webridge-common/lib/build/libs/lib.jar'),str(R/'deps/*')])
 cmd=[str(R/'boot-jdk8/bin/java'),'-Xmx8g','-cp',cp,'PaperCompilerServer',str(P)+'/',str(GEN),str(APP/'My-Blog-schema.sql')]
 proc,log=launch('compiler',cmd,P)
 for _ in range(60):
  if proc.poll() is not None:raise RuntimeError('Compiler exited; '+str(log))
  if 'PAPER_COMPILER_READY' in log.read_text():print('Ready compiler',proc.pid,log,flush=True);return
  time.sleep(1)
 raise RuntimeError('Compiler timeout '+str(log))
def bench(populate=False,smoke=False):
 driver=R/'paper-driver'
 jar=driver/'build/libs/webench-1.0-SNAPSHOT.jar'
 warm=5 if smoke else 300;duration=10 if smoke else 600
 out=P/('smoke' if smoke else 'measurements')/time.strftime('%Y%m%dT%H%M%S',time.gmtime());out.mkdir(parents=True)
 cmd=['taskset','-c','8,18',str(R/'boot-jdk8/bin/java'),'-jar',str(jar),'--app','myblog','--workload','blogging','--schema',str(APP/'My-Blog-schema-and-data.sql'),'--threads','1','--warmup',str(warm),'--time',str(duration),'--period','60','--host','127.0.0.1','--port','55325','--username','webridge','--password','webridge-local','--database','my_blog_db','--web-host','http://127.0.0.1:19080','--distribution-base-dir','data/blogging','--perf-base-dir',str(out)]
 if populate:cmd+=['--onlyPopulateDb']
 event('benchmark',command=cmd,output=str(out),populate_only=populate,smoke=smoke)
 (out/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
 with (out/'driver.log').open('wb') as f:
  p=subprocess.run(cmd,cwd=driver,env=env(),stdout=f,stderr=subprocess.STDOUT)
 print(out,flush=True)
 if p.returncode:raise RuntimeError('Driver failed: '+str(out))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('action',choices=['start','stop','compiler','populate','smoke','measure']);a.add_argument('--mode',choices=['normal','train','optimized','offline'],default='normal');args=a.parse_args()
 if args.action=='start':start(args.mode)
 elif args.action=='stop':
  for n in ['online','offline','compiler']:stop(n)
 elif args.action=='compiler':compiler()
 else:bench(populate=args.action=='populate',smoke=args.action=='smoke')
