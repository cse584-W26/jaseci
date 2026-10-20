#!/usr/bin/env python3
"""Quiet same-application full/pruned direct/SP sweep over measured response delay."""
import argparse,importlib.util,json,pathlib,signal,statistics,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1]
watch_spec=importlib.util.spec_from_file_location('owned_watchdog',B/'benchmark-comparison/owned_watchdog.py');watchdog=importlib.util.module_from_spec(watch_spec);watch_spec.loader.exec_module(watchdog)
spec=importlib.util.spec_from_file_location('timing_command',H/'timing_command.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
def p95(values):
 x=sorted(values);rank=(len(x)-1)*.95;lo=int(rank);return x[lo]+(x[min(lo+1,len(x)-1)]-x[lo])*(rank-lo)
def summarize(root):
 result=[]
 for path in sorted(root.glob('delay-*ms/*/*/requests/rows.jsonl')):
  rows=[json.loads(line)for line in path.read_text().splitlines()]
  for phase in sorted(set(r['phase']for r in rows)):
   selected=[r for r in rows if r['phase']==phase and not r['warmup']];assert len(selected)==30,(path,phase,len(selected));assert all(r['oracle_ok']for r in selected)
   first=selected[0];values=[r['ms']for r in selected];result.append({'query':first['query'],'variant':first['variant'],'phase':phase,'delay_ms':first['delay_ms'],'n':len(selected),'median_ms':statistics.median(values),'p95_ms':p95(values),'thread_cpu_median_ms':statistics.median(r['thread_cpu_ms']for r in selected),'questions':sorted(set(r['questions']for r in selected)),'call_procedure':sorted(set(r['call_procedure']for r in selected)),'rows_path':str(path),'status':'measured'})
 (root/'summary.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,default=H/'timing');p.add_argument('--delays',nargs='+',type=float,default=[0,2,10]);p.add_argument('--queries',nargs='+',default=['is1','is2','is3','ic1','ic2','ic13']);p.add_argument('--variants',nargs='+',default=['full','pruned']);p.add_argument('--port',type=int,default=18537);p.add_argument('--reverse',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 cases=json.loads((H/'case-status.json').read_text());logging=subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-N','-uroot','-e','SELECT @@global.general_log,@@global.log_output'],text=True).strip();assert logging.split('\t')[0]=='0','General SQL logging enabled';(a.out/'logging-before.tsv').write_text(logging)
 try:
  for delay in a.delays:
   o=a.out/f'delay-{delay:g}ms';o.mkdir();cmd=[sys.executable,str(B/'latency-comparison/proxy.py'),'--port',str(a.port),'--delay-ms',str(delay),'--target-port','55337','--receipt',str(o/'proxy-cleanup.json')];(o/'proxy-command.json').write_text(json.dumps(cmd));log=(o/'proxy.log').open('w');proxy=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    for _ in range(100):
     if '"ready": true'in(o/'proxy.log').read_text():break
     if proxy.poll()is not None:raise RuntimeError('Proxy start failed')
     time.sleep(.05)
    else:raise RuntimeError('Proxy readiness timeout')
    # Same original SERVER/JDBC path; median SELECT 1 latency is retained separately.
    calibration_cp=str(B/'latency-comparison/classes')+':'+t.m.CP;t.m.command([str(t.m.SERVER/'bin/java'),'-cp',calibration_cp,'Roundtrip',str(a.port),str(o/'roundtrip.json')],o/'calibration',60)
    for query in a.queries:
     for variant in a.variants:
      selected=next(r for r in cases if r['query']==query and r['variant']==variant);assert selected['selected_case'],selected
      phases='sp,baseline'if a.reverse else'baseline,sp'
      if selected['status']!='success':phases='baseline'
      dest=o/query/variant;cmd=t.command(selected['selected_case'],dest,10,30,phases,f'127.0.0.1:{a.port}',delay);guard=watchdog.run(cmd,dest,timeout=300,request_limit=15);assert not guard['timed_out'],'Unexpected fast-arm timeout';summarize(a.out);print(query,variant,delay,'complete',flush=True)
   finally:
    if proxy.poll()is None:proxy.send_signal(signal.SIGTERM)
    try:proxy.wait(timeout=5)
    except subprocess.TimeoutExpired:proxy.kill();proxy.wait()
    log.close();(o/'proxy-process.json').write_text(json.dumps({'pid':proxy.pid,'returncode':proxy.returncode,'stopped':proxy.poll()is not None}))
 finally:
  after=subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-N','-uroot','-e','SELECT @@global.general_log,@@global.log_output'],text=True).strip();(a.out/'logging-after.tsv').write_text(after);(a.out/'cleanup.json').write_text(json.dumps({'logging_unchanged':after==logging,'proxy_stop_receipts':list(map(str,a.out.glob('delay-*ms/proxy-cleanup.json')))},indent=2));summarize(a.out)
