#!/usr/bin/env python3
"""Serialized original-driver direct/SP sweep with shared calibrated response-delay proxy."""
import pathlib,subprocess,sys,json,time,signal,importlib.util,statistics,argparse,fcntl
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];R=B/'latency-comparison';I=B/'integration';sp=importlib.util.spec_from_file_location('ctl',I/'control.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
sp_lock=(I/'.mysql-sp-profile.lock').open('w');fcntl.flock(sp_lock,fcntl.LOCK_EX)
ds=importlib.util.spec_from_file_location('guard_driver',H/'watchdog_command.py');gd=importlib.util.module_from_spec(ds);ds.loader.exec_module(gd)
ws=importlib.util.spec_from_file_location('owned_watchdog',B/'benchmark-comparison/owned_watchdog.py');wd=importlib.util.module_from_spec(ws);ws.loader.exec_module(wd)
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--queries',nargs='+',default=['is1','is2','is3','ic1','ic2','ic13']);p.add_argument('--phases',default='baseline,sp');p.add_argument('--warm',type=int,default=10);p.add_argument('--measure',type=int,default=30);a=p.parse_args();out=a.out.resolve();out.mkdir(exist_ok=True);summary=json.loads((out/'summary-detailed.json').read_text()) if (out/'summary-detailed.json').exists() else {}
logging=subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-e','SELECT @@global.general_log'],text=True).strip();assert logging=='0';(out/'logging-before.json').write_text(json.dumps({'general_log':logging}))
calcp=str(R/'classes')+':'+m.CP
for delay in [0,2,10]:
 d=out/f'delay-{delay}ms';d.mkdir(exist_ok=True);cmd=[sys.executable,str(R/'proxy.py'),'--port','18537','--delay-ms',str(delay),'--target-port','55337','--receipt',str(d/'proxy-cleanup.json')];(d/'proxy-command.json').write_text(json.dumps(cmd))
 with(d/'proxy.log').open('w')as log:
  proxy=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   for _ in range(100):
    if '"ready": true'in(d/'proxy.log').read_text():break
    if proxy.poll()is not None:raise RuntimeError('proxy failed')
    time.sleep(.05)
   else:raise RuntimeError('proxy timeout')
   m.command([str(m.SERVER/'bin/java'),'-cp',calcp,'Roundtrip','18537',str(d/'roundtrip-before.json')],d/'calibration-before',60)
   for q in a.queries:
    if all(f'{q}/{delay}/{phase}' in summary for phase in a.phases.split(',') if not(q=='ic1' and phase=='sp')):continue
    c=I/'cases'/json.loads((H/'selected-cases.json').read_text())[q];classes=c/'source/classes';assert(classes/'SetTiming.class').exists();cp=':'.join([str(classes),str(I/'recorded-bind-types/classes'),str(I/'json-type-compat/classes'),str(I/'numeric-width/classes'),str(I/'jdbc-string/combined'),m.CP]);dest=d/q;phases=','.join(x for x in a.phases.split(',') if not(q=='ic1' and x=='sp'));cmd=gd.command(q,dest,18537,a.warm,a.measure,phases);wd.run(cmd,dest,timeout=300,request_limit=15)
    rows=[json.loads(x)for x in(dest/'requests/rows.jsonl').read_text().splitlines()];assert len(rows)==len(phases.split(','))*(a.warm+a.measure)and all(x['oracle_ok']for x in rows)
    for phase in phases.split(','):
     rr=[x for x in rows if x['phase']==phase and not x['warmup']];assert len(rr)==a.measure
     summary[f'{q}/{delay}/{phase}']={'median_ms':statistics.median(x['ms']for x in rr),'samples':len(rr),'actual_command_counts':sorted({x['questions']for x in rr}),'actual_call_counts':sorted({x['status_delta']['Com_call_procedure']for x in rr})}
    (out/'summary-detailed.json').write_text(json.dumps(summary,indent=2)+'\n');(out/'summary.json').write_text(json.dumps([dict(query=k.split('/')[0],variant='set',phase=k.split('/')[2],delay_ms=int(k.split('/')[1]),median_ms=v['median_ms'],n=v['samples'],rows_path=str(out/('delay-'+k.split('/')[1]+'ms')/k.split('/')[0]/'requests/rows.jsonl'),actual_command_counts=v['actual_command_counts'],actual_call_counts=v['actual_call_counts']) for k,v in summary.items()]+[json.loads(z.read_text()) for z in sorted(out.glob('delay-*/censored-summary.json'))],indent=2)+'\n')
   if 'ic1' in a.queries and 'sp' in a.phases.split(','):
    censored=[]
    for attempt in range(3):
     probe=d/'ic1'/('censored-sp-'+str(attempt));res=json.loads((probe/'owned-watchdog-summary.json').read_text()) if (probe/'owned-watchdog-summary.json').exists() else wd.run(gd.command('ic1',probe,18537,0,1,'sp'),probe,timeout=60,request_limit=15);assert res['timed_out'],'Unexpected noncensored IC1: assess actual rows before reporting';cid=wd.connection(probe)
     for _ in range(600):
      snap=wd.query("SELECT JSON_OBJECT('id',ID,'command',COMMAND,'state',STATE,'time',TIME) FROM information_schema.PROCESSLIST WHERE ID="+str(cid));remaining='0' if not snap.stdout.strip() else '1'
      with (probe/'cleanup-poll.jsonl').open('a') as poll:poll.write(json.dumps({'wall_ns':time.time_ns(),'returncode':snap.returncode,'stdout':snap.stdout,'stderr':snap.stderr})+'\n')
      if remaining=='0':break
      time.sleep(.1)
     assert remaining=='0','Owned IC1 connection remains';(probe/'server-absence-verification.json').write_text(json.dumps({'connection_id':cid,'verified_absent':True}));censored.append(str(probe))
    existing=json.loads((out/'summary.json').read_text());existing.append({'query':'ic1','variant':'set','phase':'sp','delay_ms':delay,'median_ms':None,'n':0,'status':'timeout >15s','warmup_completed':False,'measurement_scope':'SP request >15s; warmup not completed; fresh JVM with cold callable metadata','attempts':3,'timeout_paths':censored});(d/'censored-summary.json').write_text(json.dumps(existing[-1],indent=2));(out/'summary.json').write_text(json.dumps(existing,indent=2)+'\n')
   m.command([str(m.SERVER/'bin/java'),'-cp',calcp,'Roundtrip','18537',str(d/'roundtrip-after.json')],d/'calibration-after',60)
  finally:
   if proxy.poll()is None:proxy.send_signal(signal.SIGTERM)
   try:proxy.wait(timeout=5)
   except subprocess.TimeoutExpired:proxy.kill();proxy.wait()
   (d/'proxy-process.json').write_text(json.dumps({'pid':proxy.pid,'returncode':proxy.returncode,'stopped':proxy.poll()is not None}))
print(json.dumps(summary,indent=2))
