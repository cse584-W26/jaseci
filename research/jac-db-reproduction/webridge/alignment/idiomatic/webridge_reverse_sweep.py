#!/usr/bin/env python3
"""Isolated full/pruned Java and actual WeBridge delay sweep."""
import pathlib,json,subprocess,importlib.util,time,signal,sys,statistics
H=pathlib.Path(__file__).resolve().parent;R=H.parents[1]/'latency-comparison';I=R.parent/'integration';spec=importlib.util.spec_from_file_location('ctl',I/'control.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def main():
 out=H/'webridge-delay-reverse-results';out.mkdir(exist_ok=False)
 logging=subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-e','SELECT @@global.general_log,@@global.log_output'],text=True).strip();assert logging.split('\t')[0]=='0';(out/'logging-before.tsv').write_text(logging)
 cp=':'.join([str(H/'webridge-classes'),str(I/'numeric-width/classes'),str(R/'classes'),str(R.parent/'alignment/small-diagnostic/classes'),str(I/'jdbc-string/combined'),m.CP]);align=R.parent/'alignment/small-diagnostic/runtime-data'
 def run(cmd,dest,timeout=240):m.command(cmd,dest,timeout)
 run([str(m.SERVER/'bin/java'),'-cp',cp,'Roundtrip','55337',str(out/'direct-roundtrip.json')],out/'calibration-direct')
 for delay in [0,2,10]:
  o=out/f'delay-{delay}ms';o.mkdir();cmd=[sys.executable,str(R/'proxy.py'),'--port','18537','--delay-ms',str(delay),'--target-port','55337','--receipt',str(o/'proxy-cleanup.json')];(o/'proxy-command.json').write_text(json.dumps(cmd))
  with (o/'proxy.log').open('w') as log:
   p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    for _ in range(100):
     if '"ready": true' in (o/'proxy.log').read_text():break
     if p.poll()is not None:raise RuntimeError('proxy start failed')
     time.sleep(.05)
    else:raise RuntimeError('proxy readiness timeout')
    run([str(m.SERVER/'bin/java'),'-cp',cp,'Roundtrip','18537',str(o/'roundtrip.json')],o/'calibration')
    for variant in ['idiomatic']:
     case=I/'cases'/'idiomatic-small-20261020';dest=o/variant;flags=['-Dpruned.'+x+'=true' for x in ['auth','acl','schema','hydration']]if variant=='pruned'else[]
     api=json.loads((case/'metadata.json').read_text())['api']
     cmd=[str(m.SERVER/'bin/java'),'-Xmx8g','-Didiomatic.sql='+str(H/'ic5.sql'),'-Dorg.slf4j.simpleLogger.defaultLogLevel=error',*flags,'-Dexperiment.mysql.endpoint=127.0.0.1:18537','-Dintegration.dir='+str(case),'-Dexecution.dir='+str(dest),'-Dintegration.api='+api,'-cp',cp,'IdiomaticTiming',str(align),str(case),str(dest/'requests'),variant,'jac_alignment_utf8','10','30','sp,baseline']
     run(cmd,dest)
    run([str(m.SERVER/'bin/java'),'-cp',cp,'Roundtrip','18537',str(o/'roundtrip-after.json')],o/'calibration-after')
   finally:
    if p.poll()is None:p.send_signal(signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    (o/'proxy-process.json').write_text(json.dumps({'pid':p.pid,'returncode':p.returncode,'stopped':p.poll()is not None}))
 summary={}
 for delay in [0,2,10]:
  o=out/f'delay-{delay}ms';entry={'roundtrip_median_ms':statistics.median(json.loads((o/'roundtrip.json').read_text())),'arms':{}}
  for variant in ['idiomatic']:
   rows=[json.loads(x)for x in (o/variant/'requests/rows.jsonl').read_text().splitlines()];assert len(rows)==80 and all(x['oracle_ok']for x in rows)
   for phase in ['baseline','sp']:
    rr=[x for x in rows if x['phase']==phase and not x['warmup']];assert len(rr)==30
    expected=4;assert all(x['questions']==expected for x in rr)
    entry['arms'][variant+'-'+phase]={'median_ms':statistics.median(x['ms']for x in rr),'thread_cpu_median_ms':statistics.median(x['thread_cpu_ms']for x in rr),'commands':expected,'samples':30}
  summary[str(delay)]=entry
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
