import argparse,pathlib,json,subprocess,sys,datetime
R=pathlib.Path(__file__).resolve().parent;p=argparse.ArgumentParser();p.add_argument('--variant',choices=['full','pruned'],required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
def sql(s):return subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-r','-e',s],text=True).strip()
initial=sql('SELECT @@global.general_log,@@global.log_output,CURRENT_TIMESTAMP(6)').split('\t');(o/'logging-before.json').write_text(json.dumps(initial));assert len(initial)==3
try:
 sql("SET GLOBAL log_output='TABLE'; SET GLOBAL general_log=ON")
 cmd=[sys.executable,str(R/'warm_timing.py'),'--variant',a.variant,'--db','jac_alignment_utf8','--out',str(o/'run'),'--warm','1','--measure','2','--instrumented'];(o/'command.json').write_text(json.dumps(cmd));r=subprocess.run(cmd,capture_output=True,text=True);(o/'stdout.log').write_text(r.stdout);(o/'stderr.log').write_text(r.stderr);assert r.returncode==0
 c=json.loads((o/'run/requests/connection.json').read_text());sql('SET GLOBAL general_log=OFF')
 for name,query in [('general-log',"SELECT JSON_OBJECT('time',event_time,'command',command_type,'sql',argument) FROM mysql.general_log WHERE thread_id="+str(c['connection_id'])+" AND event_time>='"+initial[2]+"' ORDER BY event_time"),('pfs',"SELECT JSON_OBJECT('thread',THREAD_ID,'event',EVENT_ID,'nest',NESTING_EVENT_ID,'name',EVENT_NAME,'sql',SQL_TEXT,'timer_ps',TIMER_WAIT,'rows_examined',ROWS_EXAMINED,'rows_sent',ROWS_SENT,'no_index',NO_INDEX_USED) FROM performance_schema.events_statements_history_long WHERE THREAD_ID="+str(c['pfs_thread_id'])+' ORDER BY EVENT_ID')]:
  (o/(name+'.jsonl')).write_text(sql(query)+'\n')
 print(o)
finally:
 sql("SET GLOBAL general_log="+initial[0]+"; SET GLOBAL log_output='"+initial[1]+"'");(o/'logging-after.json').write_text(json.dumps(sql('SELECT @@global.general_log,@@global.log_output').split('\t')))
