#!/usr/bin/env python3
import pathlib,json,subprocess,importlib.util,time,signal,sys
R=pathlib.Path(__file__).resolve().parent;B=R.parent;I=B/'integration';L=B/'latency-comparison';spec=importlib.util.spec_from_file_location('ctl',I/'control.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=R/'mysql-results';out.mkdir(exist_ok=False);cmd=[sys.executable,str(R/'mysql_proxy.py'),'--port','18547','--delay-ms','2','--trace',str(out/'protocol.jsonl'),'--receipt',str(out/'proxy-cleanup.json')];(out/'proxy-command.json').write_text(json.dumps(cmd));log=(out/'proxy.log').open('w');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
try:
 for _ in range(100):
  if '"ready": true'in(out/'proxy.log').read_text():break
  if p.poll()is not None:raise RuntimeError('proxy start failed')
  time.sleep(.05)
 else:raise RuntimeError('proxy timeout')
 cp=':'.join([str(L/'classes'),str(B/'alignment/small-diagnostic/classes'),str(I/'jdbc-string/combined'),m.CP]);align=B/'alignment/small-diagnostic/runtime-data'
 for variant in ['full','pruned']:
  case=I/'cases'/f'small-{variant}-webridge-20261020';dest=out/variant;flags=['-Dpruned.'+x+'=true'for x in ['auth','acl','schema','hydration']]if variant=='pruned'else[];api=json.loads((case/'metadata.json').read_text())['api']
  cmd=[str(m.SERVER/'bin/java'),'-Xmx8g','-Dorg.slf4j.simpleLogger.defaultLogLevel=error',*flags,'-Dexperiment.mysql.endpoint=127.0.0.1:18547','-Dintegration.dir='+str(case),'-Dexecution.dir='+str(dest),'-Dintegration.api='+api,'-cp',cp,'WarmTiming',str(align),str(case),str(dest/'requests'),variant,'jac_alignment_utf8','10','3','baseline,sp'];m.command(cmd,dest,180)
finally:
 if p.poll()is None:p.send_signal(signal.SIGTERM)
 try:p.wait(timeout=5)
 except subprocess.TimeoutExpired:p.kill();p.wait()
 log.close();(out/'proxy-process.json').write_text(json.dumps({'pid':p.pid,'returncode':p.returncode,'stopped':p.poll()is not None}))
print(out)
