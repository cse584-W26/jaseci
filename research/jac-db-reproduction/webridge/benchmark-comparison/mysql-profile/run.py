"""Instrumented immutable-case direct/SP profile with live thread-scoped P_S retention."""
import argparse,pathlib,sys,json,subprocess,time,threading,signal,os,importlib.util,gzip,fcntl
R=pathlib.Path(__file__).resolve().parent;W=R.parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=argparse.ArgumentParser();p.add_argument('--query',required=True);p.add_argument('--kind',choices=['full','pruned','conventional'],required=True);p.add_argument('--case',type=pathlib.Path);p.add_argument('--phases',default='baseline,sp');p.add_argument('--business-only-instruments',action='store_true');p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);lock=(W/'integration/.mysql-sp-profile.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
def sql(q):return subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-r','-e',q],text=True).strip()
settings=sql("SELECT @@global.general_log;SHOW VARIABLES LIKE 'performance_schema_events_statements_history_long_size';SHOW VARIABLES LIKE 'performance_schema_max_sql_text_length';SELECT NAME,ENABLED FROM performance_schema.setup_consumers WHERE NAME LIKE '%statement%';SELECT NAME,ENABLED,TIMED FROM performance_schema.setup_instruments WHERE NAME LIKE 'statement/sp/%'");(out/'instrumentation-before.tsv').write_text(settings);assert settings.splitlines()[0]=='0'
cmd=[sys.executable,str(R/'trace_proxy.py'),'--port','18547','--delay-ms','2','--quit-grace-ms','1000','--trace',str(out/'protocol.jsonl'),'--receipt',str(out/'proxy-cleanup.json')];(out/'proxy-command.json').write_text(json.dumps(cmd));log=(out/'proxy.log').open('w');proxy=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);stop=threading.Event();events={};polls=[];connection=None;errors=[]
def collect():
 global connection
 try:
  while not stop.is_set():
   trace=out/'protocol.jsonl'
   if trace.exists():
    for line in trace.read_text().splitlines():
     try:e=json.loads(line)
     except json.JSONDecodeError:continue
     if e['event']=='server_greeting':connection=e['server_connection_id'];break
   if connection is not None:break
   stop.wait(.05)
  if connection is None:return
  tid=sql('SELECT THREAD_ID FROM performance_schema.threads WHERE PROCESSLIST_ID='+str(connection));assert tid;tid=int(tid);(out/'connection.json').write_text(json.dumps({'connection_id':connection,'pfs_thread_id':tid}));last=0;final_round=False;summaries=[];trace_offset=0;trace_pending='';commands=[];done=set()
  while True:
   with(out/'protocol.jsonl').open()as tracefile:tracefile.seek(trace_offset);trace_new=tracefile.read();trace_offset=tracefile.tell()
   lines=(trace_pending+trace_new).splitlines(keepends=True);trace_pending=''
   for line in lines:
    if not line.endswith('\n'):trace_pending=line;continue
    if '"event": "command"'not in line and'"event": "response_complete"'not in line:continue
    e=json.loads(line)
    if e['event']=='command':commands.append(e)
    elif e['stage']=='delivered':done.add(e['command_id'])
   if commands and commands[-1]['id']not in done and time.monotonic()-commands[-1]['at']>15:
    owned=sql('SELECT ID,DB,COMMAND,INFO FROM information_schema.PROCESSLIST WHERE ID='+str(connection));fields=owned.split('\t');assert fields[0]==str(connection)and fields[1]=='jac_snb_six_20261020',owned;sql('KILL CONNECTION '+str(connection));(out/'server-kill.json').write_text(json.dumps({'owned_processlist_before_kill':owned,'connection_id':connection,'pending_command':commands[-1],'limit_s':15,'action':'KILL CONNECTION'}));errors.append('Owned request exceeded15s command watchdog');break
   t=time.monotonic_ns();q="SELECT JSON_OBJECT('thread',THREAD_ID,'event',EVENT_ID,'end_event',END_EVENT_ID,'nest',NESTING_EVENT_ID,'nest_type',NESTING_EVENT_TYPE,'name',EVENT_NAME,'sql',SQL_TEXT,'timer_start',TIMER_START,'timer_end',TIMER_END,'timer_ps',TIMER_WAIT,'rows_examined',ROWS_EXAMINED,'rows_sent',ROWS_SENT,'no_index',NO_INDEX_USED,'no_good_index',NO_GOOD_INDEX_USED,'object',OBJECT_NAME,'error',MYSQL_ERRNO) FROM performance_schema.events_statements_history_long WHERE THREAD_ID="+str(tid)+' AND EVENT_ID>'+str(last)+' ORDER BY EVENT_ID';raw=sql(q);new=0
   for line in raw.splitlines():
    e=json.loads(line)
    if e['thread']!=tid:
     errors.append('Concurrent P_S ring overwrite returned foreign THREAD_ID '+str(e['thread'])+' for owned '+str(tid));continue
    key=(e['thread'],e['event']);new+=key not in events;events[key]=e
   counter_raw=sql("SELECT JSON_OBJECT('thread',THREAD_ID,'name',EVENT_NAME,'count',COUNT_STAR,'timer_ps',SUM_TIMER_WAIT) FROM performance_schema.events_statements_summary_by_thread_by_event_name WHERE THREAD_ID="+str(tid)+" AND EVENT_NAME LIKE 'statement/%'");summaries.append({'at_mono_ns':time.monotonic_ns(),'rows':[json.loads(line)for line in counter_raw.splitlines()]});(out/'P_S-thread-summary-snapshots.json').write_text(json.dumps(summaries))
   # Retain all unseen ids rather than using maximum EVENT_ID: a parent CALL completes after its children.
   polls.append({'start_mono_ns':t,'end_mono_ns':time.monotonic_ns(),'returned_rows':len(raw.splitlines()),'new_events':new})
   if stop.is_set():
    if final_round:break
    final_round=True;continue
   stop.wait(.1)
 except BaseException as e:errors.append(repr(e))
instrument_rows=[line.split('\t')for line in sql("SELECT NAME,ENABLED,TIMED FROM performance_schema.setup_instruments WHERE NAME LIKE 'statement/sp/%' ORDER BY NAME").splitlines()];(out/'SP-instruments-before.json').write_text(json.dumps(instrument_rows,indent=2))
try:
 if not a.business_only_instruments:sql("UPDATE performance_schema.setup_instruments SET ENABLED='YES',TIMED='YES' WHERE NAME LIKE 'statement/sp/%'")
 if a.business_only_instruments:sql("UPDATE performance_schema.setup_instruments SET ENABLED=IF(NAME IN('statement/sp/stmt','statement/sp/copen'),'YES','NO'),TIMED=IF(NAME IN('statement/sp/stmt','statement/sp/copen'),'YES','NO') WHERE NAME LIKE 'statement/sp/%'")
 (out/'SP-instruments-active.tsv').write_text(sql("SELECT NAME,ENABLED,TIMED FROM performance_schema.setup_instruments WHERE NAME LIKE 'statement/sp/%' ORDER BY NAME"))
 for _ in range(100):
  if '"ready": true'in(out/'proxy.log').read_text():break
  if proxy.poll()is not None:raise RuntimeError('Proxy startup failed')
  time.sleep(.05)
 else:raise RuntimeError('Proxy startup timeout')
 if a.kind=='conventional':helper=module('setcommand',W/'expansion/set-sql/profile_command.py');command=helper.command(a.query,out/'run/requests',port=18547,warm=10,measure=3,phases=a.phases)
 else:
  assert a.case;helper=module('snbcommand',W/'snb-extension/java/timing_command.py');command=helper.command(a.case,out/'run',warm=10,measured=3,phases=a.phases,endpoint='127.0.0.1:18547',delay=2)
 (out/'request-command.json').write_text(json.dumps(command,indent=2));(out/'case.json').write_text(json.dumps({'query':a.query,'kind':a.kind,'case':str(a.case)if a.case else None,'delay_ms':2,'warm_perphase':10,'measured_perphase':3,'phases':a.phases,'P_S_mode':'business_stmt_and_cursor_only'if a.business_only_instruments else'business_and_control_statement_instruments','control_event_counts_observed':not a.business_only_instruments}));monitor=threading.Thread(target=collect);monitor.start();ctl=module('original_control',W/'integration/control.py');ctl.command(command,out/'run',300)
finally:
 stop.set()
 if'monitor'in globals():monitor.join(timeout=20)
 (out/'pfs.jsonl').write_text(''.join(json.dumps(e)+'\n'for _,e in sorted(events.items())));(out/'pfs-polls.json').write_text(json.dumps({'polls':polls,'errors':errors,'deduplicated_events':len(events),'unique_key':'THREAD_ID,EVENT_ID','instrumentation_changes':True,'restore_receipt':'SP-instruments-restored.json'},indent=2))
 if proxy.poll()is None:os.killpg(proxy.pid,signal.SIGTERM)
 try:proxy.wait(timeout=10)
 except subprocess.TimeoutExpired:os.killpg(proxy.pid,signal.SIGKILL);proxy.wait()
 for name,enabled,timed in instrument_rows:sql("UPDATE performance_schema.setup_instruments SET ENABLED='"+enabled+"',TIMED='"+timed+"' WHERE NAME='"+name+"'")
 restored=[line.split('\t')for line in sql("SELECT NAME,ENABLED,TIMED FROM performance_schema.setup_instruments WHERE NAME LIKE 'statement/sp/%' ORDER BY NAME").splitlines()];assert restored==instrument_rows;(out/'SP-instruments-restored.json').write_text(json.dumps({'exact_prior_settings_restored':True,'rows':restored},indent=2))
 log.close();(out/'proxy-process.json').write_text(json.dumps({'pid':proxy.pid,'stopped':True,'returncode':proxy.returncode}));assert proxy.returncode==0
 if(out/'protocol.jsonl').exists():
  with(out/'protocol.jsonl').open('rb')as src,gzip.open(out/'protocol.jsonl.gz','wb')as dst:
   for b in iter(lambda:src.read(1024*1024),b''):dst.write(b)
assert not errors,errors
print(out)
