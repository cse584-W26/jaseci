#!/usr/bin/env python3
"""Original WeBridge integration lifecycle; every command and result is retained."""
import argparse,datetime,fcntl,hashlib,json,os,pathlib,shutil,subprocess,time,signal,re
R=pathlib.Path(__file__).resolve().parent;B=R.parent;W=B.parents[1]/'webridge';A=B/'alignment'
ZERO=W/'SourceCode/openjdk8-webridge/build/linux-x86_64-normal-zero-release/images/j2sdk-image'
SERVER=W/'SourceCode/openjdk8-webridge/build/linux-x86_64-normal-server-release/images/j2sdk-image'
BUILD=json.loads((R/'current-build.json').read_text()) if (R/'current-build.json').exists() else {'classes':str(R/'classes')}
CP=':'.join(map(str,[BUILD['classes'],B/'deps/mysql-driver-extended.jar',B/'deps/basic-components.jar',B/'deps/*']))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
def env():
 e=os.environ.copy();e['LD_LIBRARY_PATH']=str(B/'native-lib')+(':'+e['LD_LIBRARY_PATH'] if e.get('LD_LIBRARY_PATH') else '');return e
LIMITS={}
def group_members(pgid):
 members=[]
 for proc in pathlib.Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:
   stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
   if int(stat[2])==pgid and stat[0] not in ('Z','X'):
    members.append({'pid':int(proc.name),'state':stat[0],'rss_bytes':int(stat[21])*os.sysconf('SC_PAGE_SIZE')})
  except (OSError,ValueError,IndexError):pass
 return members
def final_cleanup(p,out):
 before=group_members(p.pid)
 if before:
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
 deadline=time.monotonic()+5
 after=group_members(p.pid)
 while after and time.monotonic()<deadline:
  time.sleep(.05);after=group_members(p.pid)
 try:p.wait(timeout=1)
 except subprocess.TimeoutExpired:pass
 receipt={'before':before,'remaining_active':after,'verified_empty':not after}
 (out/'final-group-cleanup.json').write_text(json.dumps(receipt,indent=2))
 if after:raise RuntimeError('Owned process group remains active: '+str(after))
def command(cmd,out,timeout):
 out.mkdir(parents=True,exist_ok=True);(out/'command.json').write_text(json.dumps(dict(argv=list(map(str,cmd)),cpu_affinity='9,19',utc=now(),timeout_s=timeout),indent=2))
 start=time.monotonic()
 with (out/'stdout.log').open('wb') as so,(out/'stderr.log').open('wb') as se:
  actual=list(map(str,['/usr/bin/time','-v','-o',out/'resource-usage.txt','taskset','-c','9,19',*cmd]))
  (out/'actual-command.json').write_text(json.dumps(actual,indent=2))
  p=subprocess.Popen(actual,cwd=out,env=env(),stdout=so,stderr=se,start_new_session=True)
  (out/'pid.json').write_text(json.dumps(dict(pid=p.pid,process_group=p.pid)))
  stop_reason=None; peak_rss=0; peak_output=0; next_disk=0; next_sample=0
  try:
   while p.poll() is None:
    elapsed=time.monotonic()-start
    if elapsed>=timeout:stop_reason='wall_timeout';break
    if LIMITS:
     rss=0
     for proc in pathlib.Path('/proc').iterdir():
      if not proc.name.isdigit():continue
      try:
       stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
       if int(stat[2])==p.pid:rss+=int(stat[21])*os.sysconf('SC_PAGE_SIZE')
      except (OSError,ValueError,IndexError):pass
     peak_rss=max(peak_rss,rss)
     if elapsed>=next_sample or rss>LIMITS.get('rss_bytes',float('inf')):
      sample={'elapsed_seconds':elapsed,'utc':now(),'process_group_rss_bytes':rss}
      with (out/'stdout.log').open('rb') as progress:
       progress.seek(0,2);progress.seek(max(0,progress.tell()-8192));tail=progress.read()
      matches=list(re.finditer(rb'SQL (\d+) used [0-9.]+ ms to serialize(?:;? json_buffer_bytes=(\d+))?',tail))
      if matches:
       sample['last_serialized_sql_index']=int(matches[-1][1])
       if matches[-1][2] is not None:sample['serialized_json_bytes']=int(matches[-1][2])
      with (out/'resource-samples.jsonl').open('a') as samples:samples.write(json.dumps(sample)+'\n')
      next_sample=elapsed+1
     if rss>LIMITS.get('rss_bytes',float('inf')):stop_reason='process_group_rss_limit';break
     if elapsed>=next_disk:
      global_graph=pathlib.Path('/tmp/webridgeMngr.tmp.sp.string')
      disk_bytes=sum(f.stat().st_size for f in out.parent.rglob('*') if f.is_file())
      if global_graph.exists():disk_bytes+=global_graph.stat().st_size
      peak_output=max(peak_output,disk_bytes)
      next_disk=elapsed+1
      if peak_output>LIMITS.get('output_bytes',float('inf')):stop_reason='case_output_limit';break
    time.sleep(.1)
   if stop_reason:raise subprocess.TimeoutExpired(cmd,timeout)
   rc=p.returncode
  except subprocess.TimeoutExpired:
   # /usr/bin/time may exit on TERM before its native JVM child does.
   # A wrapper exit is not proof that the owned process group stopped.
   def live_group():
    members=[]
    for proc in pathlib.Path('/proc').iterdir():
     if not proc.name.isdigit():continue
     try:
      stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
      if int(stat[2])==p.pid and stat[0]!='Z':members.append(int(proc.name))
     except (OSError,ValueError,IndexError):pass
    return members
   before_stop=live_group()
   hard_limit=stop_reason in ('process_group_rss_limit','case_output_limit')
   try:os.killpg(p.pid,signal.SIGKILL if hard_limit else signal.SIGTERM)
   except ProcessLookupError:pass
   deadline=time.monotonic()+(0 if hard_limit else 1)
   while live_group() and time.monotonic()<deadline:time.sleep(.05)
   remaining=live_group()
   if remaining:
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
   p.wait(timeout=5)
   cleanup_deadline=time.monotonic()+2
   while live_group() and time.monotonic()<cleanup_deadline:time.sleep(.05)
   after_stop=live_group()
   (out/'group-stop.json').write_text(json.dumps(dict(reason=stop_reason,hard_limit_immediate_kill=hard_limit,before_live_pids=before_stop,after_live_pids=after_stop),indent=2))
   if after_stop:raise RuntimeError('Owned process group remains alive after kill: '+str(after_stop))
   rc=124
  finally:
   final_cleanup(p,out)
 result=dict(returncode=rc,wall_s=time.monotonic()-start,utc=now(),stop_reason=stop_reason,limits=LIMITS,peak_process_group_rss_bytes=peak_rss,peak_case_output_bytes=peak_output);(out/'process-result.json').write_text(json.dumps(result,indent=2));print(out,flush=True)
 if rc:raise SystemExit(rc)
def prepare_case(case,scope):
 case.mkdir(parents=True,exist_ok=True);(case/'generated/sql').mkdir(parents=True,exist_ok=True)
 api='AlignedIc5_'+scope+'_'+hashlib.sha256(str(case).encode()).hexdigest()[:12]
 if not (case/'metadata.json').exists():
  metadata=dict(api=api,scope=scope,alignment_gate=str(A/'alignment-gate.json'),aligned_source=str(A/'AlignedIc5.java'),aligned_sha256=sha(A/'AlignedIc5.java'),upstream_commit=subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip(),schema_sha256=sha(A/'schema.sql'),classpath=CP,java_wrapper_sha256=sha(R/'java/AlignedWeBridge.java'),request_scope='Validated AlignedIc5 request after upstream-authenticated CLI context; retains source session, ACL, hydration, transaction and process/client memo semantics')
  (case/'metadata.json').write_text(json.dumps(metadata,indent=2))
 else:metadata=json.loads((case/'metadata.json').read_text());assert metadata['scope']==scope
 config={'baseDir':str(case/'generated'),'target':'dummy','app.name':'alignedjacic5','app.schema.init.sql':str(A/'schema.sql'),'api.endpoint.name':metadata['api'],'sp.baseDir':'${baseDir}','spdefs.path':'${sp.baseDir}/sql/'+metadata['api'],'sp.path':'${sp.baseDir}/sql/'+metadata['api'],'spcontext.path':'${sp.baseDir}/sql/context/'+metadata['api'],'sqlgraph.path':'${sp.baseDir}/sql/graph/'+metadata['api'],'sptracehash.path':'${baseDir}/trace'}
 (case/'aligned.conf').write_text('\n'.join(k+'='+v for k,v in config.items())+'\n');return metadata

def main():
 global CP
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','ast-audit','inspect','input-audit','gate','baseline','record','replay','synth','optimized']);p.add_argument('--case',type=pathlib.Path);p.add_argument('--program',choices=['exact','typed','region','pruned-typed','pruned-region'],default='exact');p.add_argument('--scope',choices=['cold','warm'],default='cold');p.add_argument('--idx',type=int,default=0);p.add_argument('--repeats',type=int,default=1);p.add_argument('--graph',type=pathlib.Path);p.add_argument('--timeout',type=int,default=120);p.add_argument('--heap',default='2g');p.add_argument('--zero-java',type=pathlib.Path);p.add_argument('--frontend-overlay',type=pathlib.Path);p.add_argument('--rss-limit-gib',type=float);p.add_argument('--output-limit-gib',type=float);p.add_argument('--allow-live',action='store_true',help='Coordinator has granted the isolated DB/CPU window');p.add_argument('--graph-window-confirmed',action='store_true',help='Coordinator confirms exclusive original engine global graph file');a=p.parse_args()
 if a.frontend_overlay:
  overlay=a.frontend_overlay.resolve();assert R in overlay.parents and overlay.is_dir(),overlay
  CP=str(overlay)+':'+CP
 if a.rss_limit_gib:LIMITS['rss_bytes']=int(a.rss_limit_gib*1024**3)
 if a.output_limit_gib:LIMITS['output_bytes']=int(a.output_limit_gib*1024**3)
 if a.action=='ast-audit':
  out=R/'sql-boundaries'/('original-audit-'+now());command([B/'boot-jdk8/bin/java','-cp',CP,'AstAudit',R/'sql-boundaries/cases.json',A/'schema.sql',out/'report.json'],out,a.timeout);return
 if a.action=='build':
  out=R/'builds'/now();classes=out/'classes';classes.mkdir(parents=True);sources=[A/'AlignedIc5.java',*sorted((R/'java').glob('*.java'))]
  command([B/'boot-jdk8/bin/javac','-cp',CP,'-d',classes,*sources],out,a.timeout)
  (out/'source').mkdir()
  for source in sources:shutil.copy2(source,out/'source'/source.name)
  (out/'sources.json').write_text(json.dumps({str(f):sha(f) for f in sources},indent=2));(R/'current-build.json').write_text(json.dumps(dict(classes=str(classes),build=str(out)),indent=2));return
 case=(a.case or R/'cases'/now()).resolve();assert R in case.parents
 meta=prepare_case(case,a.scope);
 if 'program' in meta:assert meta['program']==a.program
 else:meta['program']=a.program;(case/'metadata.json').write_text(json.dumps(meta,indent=2))
 out=case/(a.action+'-'+now())
 if a.frontend_overlay:
  out.mkdir(parents=True,exist_ok=True)
  (out/'frontend-overlay.json').write_text(json.dumps(dict(classes=str(overlay),classpath=CP,coverage_repair=True,original_engine_algorithms_unchanged=True),indent=2))
 if a.action in ('baseline','record','replay','optimized','gate') and not a.allow_live:p.error('Explicit coordinator DB-window grant required: --allow-live')
 if a.action=='replay' and not a.graph_window_confirmed:p.error('Original graph-file window must be coordinated: --graph-window-confirmed')
 if a.action=='record' and (case/('record-'+a.scope+'-'+str(a.idx)+'.bin')).exists():p.error('Preserve existing capture; choose a new case')
 if a.action=='synth' and not a.graph:p.error('--graph must name the retained original-engine graph')
 java=(ZERO if a.action=='replay' else B/'boot-jdk8' if a.action=='synth' else SERVER)/'bin/java'
 if a.zero_java:
  assert a.action=='replay','--zero-java applies only to original native replay'
  java=a.zero_java.resolve();assert java.is_file() and B in java.parents,java
  out.mkdir(parents=True,exist_ok=True)
  binary_files=[java,*java.parent.parent.rglob('libjvm.so')]
  (out/'capacity-variant.json').write_text(json.dumps(dict(java=str(java),binary_sha256={str(f):sha(f) for f in binary_files},original_zero=str(ZERO/'bin/java'),explicit_variant=True),indent=2))
 program={'exact':('AlignedIc5','AlignedWeBridge',A/'AlignedIc5.java'),'typed':('ReplayCompatibleAlignedIc5','CompatibleWeBridge',R/'java/ReplayCompatibleAlignedIc5.java'),'region':('RegionCompatibleAlignedIc5','RegionWeBridge',R/'java/RegionCompatibleAlignedIc5.java'),'pruned-typed':('ReplayCompatiblePrunedIc5','PrunedRegionWeBridge',R/'java/ReplayCompatiblePrunedIc5.java'),'pruned-region':('RegionCompatiblePrunedIc5','PrunedRegionWeBridge',R/'java/RegionCompatiblePrunedIc5.java')}[a.program]
 cmd=[java,'-Xmx'+a.heap,'-Xss20m','-Dintegration.dir='+str(case),'-Dexecution.dir='+str(out),'-Dalignment.dir='+str(A),'-Daligned.source='+str(program[2]),'-Dintegration.scope='+a.scope,'-Dintegration.api='+meta['api'],'-Dalignment.finalRepeatFirst=true','-cp',CP,program[1],a.action]
 if a.program.startswith('pruned-'):
  cmd[1:1]=['-Dpruned.auth=true','-Dpruned.acl=true','-Dpruned.schema=true','-Dpruned.hydration=true']
 cmd+= [str(a.graph.resolve())] if a.action=='synth' else [str(a.idx),str(a.repeats)]
 if a.action=='gate':cmd=cmd[:cmd.index('-cp')]+['-cp',CP,program[0],'0','19','1']
 if a.action=='replay':
  with (R/'.engine-graph.lock').open('w') as lock:fcntl.flock(lock,fcntl.LOCK_EX);command(cmd,out,a.timeout)
 else:command(cmd,out,a.timeout)
if __name__=='__main__':main()
