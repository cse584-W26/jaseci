#!/usr/bin/env python3
"""Bound an owned JDBC request and terminate its verified database connection."""
import argparse,concurrent.futures,importlib.util,json,pathlib,subprocess,time,traceback
R=pathlib.Path(__file__).resolve().parent;W=R.parent
spec=importlib.util.spec_from_file_location('experiment_control',W/'integration/control.py');ctl=importlib.util.module_from_spec(spec);spec.loader.exec_module(ctl)

def query(sql):
 return subprocess.run(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-r','-e',sql],capture_output=True,text=True,timeout=10)
def read(p):return json.loads(p.read_text())
def connection(out):
 p=out/'connection-id.json'
 if not p.exists():return None
 d=read(p)
 if isinstance(d,int):return d
 for k in ['connection_id','connectionId','mysql_connection_id','id']:
  if k in d:return int(d[k])
 raise ValueError('Unrecognized owned connection marker keys: '+','.join(d))
def terminate(out,db,reason,marker):
 cid=connection(out);assert cid is not None,'No owned connection receipt'
 check=query("SELECT JSON_OBJECT('id',ID,'db',DB,'command',COMMAND,'time',TIME,'state',STATE,'info',INFO) FROM information_schema.PROCESSLIST WHERE ID="+str(cid))
 assert check.returncode==0,check.stderr
 lines=check.stdout.splitlines();actual=json.loads(lines[-1])if lines else None
 receipt={'wall_ns':time.time_ns(),'reason':reason,'connection_id':cid,'request_marker':marker,'verified_process':actual,'action':None}
 if actual:
  assert actual['id']==cid and actual['db']==db,actual
  killed=query('KILL CONNECTION '+str(cid));receipt.update(action='KILL CONNECTION '+str(cid),returncode=killed.returncode,stderr=killed.stderr)
  assert killed.returncode==0,killed.stderr
 (out/('owned-watchdog-'+str(time.time_ns())+'.json')).write_text(json.dumps(receipt,indent=2)+'\n');return receipt

def run(cmd,out,timeout=300,request_limit=15,db='jac_snb_six_20261020'):
 out=pathlib.Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
 (out/'watchdog-config.json').write_text(json.dumps({'request_limit_s':request_limit,'whole_process_limit_s':timeout,'database':db,'poll_s':.1,'clock':'marker start_wall_ms or first-observed active marker monotonic; Java nanoTime is retained as provenance'},indent=2))
 timed_out=None;error=None;seen={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=1)as pool:
  future=pool.submit(ctl.command,cmd,out,timeout)
  while not future.done():
   p=out/'request-active.json'
   if p.exists():
    try:marker=read(p)
    except(json.JSONDecodeError,FileNotFoundError):time.sleep(.05);continue
    identity=json.dumps(marker,sort_keys=True);first=seen.setdefault(identity,time.monotonic())
    start_ms=marker.get('start_wall_ms');elapsed=(time.time()*1000-start_ms)/1000 if start_ms is not None else time.monotonic()-first
    if elapsed>request_limit:
     timed_out=terminate(out,db,'active request exceeded measured wall-time limit',dict(marker,watchdog_elapsed_s=elapsed));break
   time.sleep(.1)
  try:future.result()
  except (Exception,SystemExit):error=traceback.format_exc()
 # The local process is now stopped; clean up its own server session if still present.
 if (out/'connection-id.json').exists():
  try:cleanup=terminate(out,db,'owned JDBC process ended; final server-session cleanup',{})
  except Exception:cleanup={'error':traceback.format_exc()}
 else:cleanup={'connection_marker_present':False}
 result={'timed_out':timed_out is not None,'limit_s':request_limit,'timeout_receipt':timed_out,'command_error':error,'final_database_cleanup':cleanup}
 (out/'owned-watchdog-summary.json').write_text(json.dumps(result,indent=2)+'\n')
 if timed_out:return result
 if error:raise RuntimeError(error)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--command-json',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--timeout',type=int,default=300);p.add_argument('--request-limit',type=float,default=15);p.add_argument('--database',default='jac_snb_six_20261020');a=p.parse_args();x=run(read(a.command_json),a.out,a.timeout,a.request_limit,a.database);print(json.dumps({'timed_out':x['timed_out'],'limit_s':x['limit_s']}));raise SystemExit(124 if x['timed_out'] else 0)
