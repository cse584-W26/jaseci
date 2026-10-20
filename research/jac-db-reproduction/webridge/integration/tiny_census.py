#!/usr/bin/env python3
"""Exclusive diagnostic original-SP warmup/census; restore server logging state."""
import pathlib,json,subprocess,sys,datetime
R=pathlib.Path(__file__).resolve().parent;out=R/'census'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True)
def sql(s):
 q=subprocess.run(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-r','-e',s],capture_output=True,text=True,check=True);return q.stdout.strip()
initial=sql('SELECT @@global.general_log,@@global.log_output,CURRENT_TIMESTAMP(6)').split('\t');assert len(initial)==3;assert initial[0] in ('0','1');assert all(x in ('TABLE','FILE','NONE') for x in initial[1].split(','));(out/'logging-before.json').write_text(json.dumps(initial))
try:
 sql("SET GLOBAL log_output='TABLE'; SET GLOBAL general_log=ON;")
 cmd=[sys.executable,str(R/'control.py'),'optimized','--case',str(R/'cases/tiny-region-width-cold-20261020'),'--program','region','--frontend-overlay',str(R/'numeric-width/classes'),'--repeats','6','--allow-live','--timeout','180'];(out/'command.json').write_text(json.dumps(cmd,indent=2));q=subprocess.run(cmd,capture_output=True,text=True);(out/'stdout.log').write_text(q.stdout);(out/'stderr.log').write_text(q.stderr);assert q.returncode==0,q.returncode
 attempt=pathlib.Path(q.stdout.strip().splitlines()[-1]);thread=json.loads((attempt/'connection-id.json').read_text());assert isinstance(thread,int)
 sql('SET GLOBAL general_log=OFF;')
 text=sql("SELECT JSON_OBJECT('event_time',event_time,'thread_id',thread_id,'command_type',command_type,'argument',argument) FROM mysql.general_log WHERE thread_id="+str(thread)+" AND event_time>='"+initial[2]+"' ORDER BY event_time");(out/'thread-log.jsonl').write_text(text+'\n');rows=[json.loads(x) for x in text.splitlines()];reports=[json.loads(f.read_text()) for f in sorted(attempt.glob('report-*.json'))];(out/'summary.json').write_text(json.dumps({'attempt':str(attempt),'thread':thread,'events':len(rows),'requests':reports,'note':'General-log enabled diagnostic; request timing excludes install but includes runtime overhead. Separate logging-off samples required for latency.'},indent=2));print(out)
finally:
 sql("SET GLOBAL general_log="+initial[0]+"; SET GLOBAL log_output='"+initial[1]+"';")
 (out/'logging-after.json').write_text(json.dumps(sql('SELECT @@global.general_log,@@global.log_output').split('\t')))
