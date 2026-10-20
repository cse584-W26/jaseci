#!/usr/bin/env python3
"""Single-owner snapshot, disable, and restore SP instruction instrumentation for quiet timing."""
import argparse,datetime,json,pathlib,subprocess
H=pathlib.Path(__file__).resolve().parent;O=H/'quiet-instrumentation';O.mkdir(exist_ok=True)
def sql(q):
 p=subprocess.run(['docker','exec','jac-webridge-mysql57','mysql','-N','-B','-uroot','-e',q],capture_output=True,text=True);assert p.returncode==0,p.stderr;return [line.split('\t')for line in p.stdout.splitlines()]
def snapshot():return {'instruments':sql('SELECT NAME,ENABLED,TIMED FROM performance_schema.setup_instruments ORDER BY NAME'),'consumers':sql('SELECT NAME,ENABLED FROM performance_schema.setup_consumers ORDER BY NAME'),'general_log':sql('SELECT @@global.general_log,@@global.log_output')}
p=argparse.ArgumentParser();p.add_argument('action',choices=['begin','restore','status']);a=p.parse_args()
if a.action=='begin':
 assert not(O/'active.json').exists(),'Quiet instrumentation already owned';before=snapshot();assert before['general_log'][0][0]=='0','General SQL logging enabled';(O/'before.json').write_text(json.dumps(before,indent=2));sql("UPDATE performance_schema.setup_instruments SET ENABLED='NO',TIMED='NO' WHERE NAME LIKE 'statement/sp/%'");after=snapshot();assert all(row[1:]==['NO','NO']for row in after['instruments']if row[0].startswith('statement/sp/'));(O/'after-disable.json').write_text(json.dumps(after,indent=2));(O/'active.json').write_text(json.dumps({'owner':'snb_java_webridge','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'All quiet Java arms use unchanged SQL instrumentation and disabled statement/sp/% event instrumentation'},indent=2));print('SP instruction instrumentation disabled; exact state saved')
elif a.action=='restore':
 before=json.loads((O/'before.json').read_text());statements=[]
 for name,enabled,timed in before['instruments']:
  if name.startswith('statement/sp/'):statements.append("UPDATE performance_schema.setup_instruments SET ENABLED='"+enabled+"',TIMED='"+timed+"' WHERE NAME='"+name+"';")
 sql('\n'.join(statements));after=snapshot();assert after==before,'Global instrumentation not exactly restored';(O/'restored.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exact_full_snapshot_equal':True,'state':after},indent=2));(O/'active.json').unlink();print('Exact global instrumentation and logging state restored')
else:print(json.dumps({'owned_active':(O/'active.json').exists(),'sp_instruments':sql("SELECT NAME,ENABLED,TIMED FROM performance_schema.setup_instruments WHERE NAME LIKE 'statement/sp/%' ORDER BY NAME")},indent=2))
