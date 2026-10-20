#!/usr/bin/env python3
"""Repeat all eighteen censored requests with strict sequential server isolation."""
import datetime,fcntl,importlib.util,json,pathlib,signal,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
t=load('tc',H/'timing_command.py');w=load('ow',B/'benchmark-comparison/owned_watchdog.py')
root=H/'timing/censored-retries';root.mkdir(exist_ok=False)
cases=json.loads((H/'case-status.json').read_text());summary_path=H/'timing/summary.json';summary=json.loads(summary_path.read_text());exclusions=[]
window={'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'running'}
try:
 old_ids=set(json.loads((B/'benchmark-comparison/censored-server-absence-verified.json').read_text())['connection_ids'])
 for base in [H/'timing/censored',B/'expansion']:
  for receipt in base.rglob('connection-id.json'):
   try:
    value=json.loads(receipt.read_text());old_ids.add(int(value['connection_id'] if isinstance(value,dict) else value))
   except (ValueError,KeyError,TypeError):pass
 assert old_ids
 pre=subprocess.run(['docker','exec','jac-webridge-mysql57','mysql','-N','-B','-uroot','-e','SELECT ID,DB,COMMAND,TIME,STATE,INFO FROM information_schema.PROCESSLIST WHERE ID IN ('+','.join(map(str,sorted(old_ids)))+')'],capture_output=True,text=True,check=True)
 (root/'old-owned-connections-preclear.json').write_text(json.dumps({'wall_ns':time.time_ns(),'connection_ids':sorted(old_ids),'processlist':pre.stdout,'all_absent':not pre.stdout.strip()},indent=2));assert not pre.stdout.strip()
 for delay,variant,attempt in [(d,v,a) for d in [0,2,10] for v in ['full','pruned'] for a in range(3)]:
  out=root/f'delay-{delay}ms'/variant/f'attempt-{attempt}';out.parent.mkdir(parents=True,exist_ok=True)
  log=(out.parent/'proxy.log').open('w');proxy=subprocess.Popen([sys.executable,str(B/'latency-comparison/proxy.py'),'--port','18537','--delay-ms',str(delay),'--target-port','55337','--receipt',str(out.parent/'proxy-cleanup.json')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   for _ in range(100):
    if '"ready": true' in (out.parent/'proxy.log').read_text():break
    assert proxy.poll() is None;time.sleep(.05)
   else:raise RuntimeError('Proxy not ready')
   case=next(c for c in cases if c['query']=='ic1' and c['variant']==variant)
   cmd=t.command(case['selected_case'],out,0,1,'sp','127.0.0.1:18537',delay);cmd.insert(cmd.index('-cp'),'-Dexperiment.allow.first.sp.metadata=true')
   with (B/'integration/.mysql-sp-profile.lock').open('w') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);result=w.run(cmd,out,timeout=45,request_limit=15)
    cid=json.loads((out/'connection-id.json').read_text());cid=cid['connection_id'] if isinstance(cid,dict) else cid
    observed=[];deadline=time.monotonic()+60
    while True:
     p=subprocess.run(['docker','exec','jac-webridge-mysql57','mysql','-N','-B','-uroot','-e',f'SELECT ID,DB,COMMAND,TIME,STATE,INFO FROM information_schema.PROCESSLIST WHERE ID={int(cid)}'],capture_output=True,text=True,check=True)
     observed.append({'wall_ns':time.time_ns(),'processlist':p.stdout})
     if not p.stdout.strip():break
     assert time.monotonic()<deadline,'Server connection remained after60s';time.sleep(.25)
    (out/'strict-server-absence.json').write_text(json.dumps({'connection_id':cid,'absent_before_next_request':True,'observations':observed},indent=2))
   assert result['timed_out'],'Unexpected completed request needs separate analysis'
   old=H/f'timing/censored/delay-{delay}ms'/variant/f'attempt-{attempt}'
   exclusions.append({'excluded_path':str(old),'replacement_path':str(out),'reason':'Sequential server-isolation proof incomplete in original sweep; retained as excluded diagnostic'})
   row=next(r for r in summary if r['query']=='ic1' and r['phase']=='sp' and r['variant']==variant and r['delay_ms']==delay)
   row['timeout_paths']=[str(out/'owned-watchdog-summary.json') if p==str(old/'owned-watchdog-summary.json') else p for p in row['timeout_paths']]
   row['attempt_paths']=[str(out) if p==str(old) else p for p in row['attempt_paths']]
   summary_path.write_text(json.dumps(summary,indent=2));(root/'excluded-attempts.json').write_text(json.dumps(exclusions,indent=2));print(delay,variant,attempt,'verified absent',flush=True)
  finally:
   if proxy.poll() is None:proxy.send_signal(signal.SIGTERM)
   proxy.wait(timeout=5);log.close()
 window['status']='complete'
finally:
 window['end_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(root/'quiet-window.json').write_text(json.dumps(window,indent=2))
