#!/usr/bin/env python3
"""Three actual bounded first-SP requests per delay for the measured slow IC1 arms."""
import argparse,fcntl,importlib.util,json,pathlib,signal,statistics,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1]
spec=importlib.util.spec_from_file_location('tc',H/'timing_command.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
spec=importlib.util.spec_from_file_location('ow',B/'benchmark-comparison/owned_watchdog.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,default=H/'timing');p.add_argument('--port',type=int,default=18537);a=p.parse_args();root=a.root/'censored';root.mkdir(exist_ok=False);cases=json.loads((H/'case-status.json').read_text());summary=json.loads((a.root/'summary.json').read_text())
for delay in [0,2,10]:
 d=root/f'delay-{delay}ms';d.mkdir();cmd=[sys.executable,str(B/'latency-comparison/proxy.py'),'--port',str(a.port),'--delay-ms',str(delay),'--target-port','55337','--receipt',str(d/'proxy-cleanup.json')];(d/'proxy-command.json').write_text(json.dumps(cmd));log=(d/'proxy.log').open('w');proxy=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 try:
  for _ in range(100):
   if '"ready": true'in(d/'proxy.log').read_text():break
   if proxy.poll()is not None:raise RuntimeError('Proxy start failed')
   time.sleep(.05)
  else:raise RuntimeError('Proxy readiness timeout')
  for variant in ['full','pruned']:
   selected=next(r for r in cases if r['query']=='ic1'and r['variant']==variant);results=[];completed=[]
   for attempt in range(3):
    out=d/variant/f'attempt-{attempt}';cmd=t.command(selected['selected_case'],out,0,1,'sp',f'127.0.0.1:{a.port}',delay);cmd.insert(cmd.index('-cp'),'-Dexperiment.allow.first.sp.metadata=true')
    with(B/'integration/.mysql-sp-profile.lock').open('w')as lock:
     fcntl.flock(lock,fcntl.LOCK_EX);result=w.run(cmd,out,timeout=45,request_limit=15)
    (out/'censored-attempt.json').write_text(json.dumps({'query':'ic1','variant':variant,'delay_ms':delay,'attempt':attempt,'warmup_completed':False,'protocol':'Fresh JVM and connection; first SP request including callable metadata; no completed SP warmup; 15-second whole-request budget','result':result},indent=2));results.append({'path':str(out),'result':result})
    f=out/'requests/rows.jsonl'
    if f.exists():
     rr=[json.loads(x)for x in f.read_text().splitlines()];assert len(rr)==1 and rr[0]['oracle_ok'];completed.append(rr[0])
    print('ic1',variant,delay,attempt,'timeout'if result['timed_out']else'completed',flush=True)
   censored=[r for r in results if r['result']['timed_out']];row={'query':'ic1','variant':variant,'phase':'sp','delay_ms':delay,'n':len(completed),'attempts':3,'median_ms':statistics.median(r['ms']for r in completed)if not censored else None,'p95_ms':None,'status':'timeout >15s'if len(censored)==3 else'partially censored'if censored else'measured first SP request','protocol':'First SP request; warmup not completed; cold callable metadata retained','request_limit_s':15,'timeout_paths':[str(pathlib.Path(r['path'])/'owned-watchdog-summary.json')for r in censored],'attempt_paths':[r['path']for r in results],'completed_ms':[r['ms']for r in completed],'rows_path':None};summary=[r for r in summary if not(r['query']=='ic1'and r['variant']==variant and r['phase']=='sp'and r['delay_ms']==delay)]+[row];(a.root/'summary.json').write_text(json.dumps(summary,indent=2))
 finally:
  if proxy.poll()is None:proxy.send_signal(signal.SIGTERM)
  try:proxy.wait(timeout=5)
  except subprocess.TimeoutExpired:proxy.kill();proxy.wait()
  log.close();(d/'proxy-process.json').write_text(json.dumps({'pid':proxy.pid,'returncode':proxy.returncode,'stopped':proxy.poll()is not None}))
