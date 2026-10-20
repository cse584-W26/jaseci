#!/usr/bin/env python3
import pathlib,json,subprocess,importlib.util,time,signal,sys,statistics
H=pathlib.Path(__file__).resolve().parent;R=H.parents[1]/'latency-comparison';I=R.parent/'integration'
spec=importlib.util.spec_from_file_location('ctl',I/'control.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=H/'delay-results';out.mkdir(exist_ok=False);summary={}
cp=str(R/'classes')+':'+m.CP
for delay in [0,2,10]:
 o=out/f'delay-{delay}ms';o.mkdir();cmd=[sys.executable,str(R/'proxy.py'),'--port','18537','--delay-ms',str(delay),'--target-port','55337','--receipt',str(o/'proxy-cleanup.json')];(o/'proxy-command.json').write_text(json.dumps(cmd))
 with (o/'proxy.log').open('w') as log:
  p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   for _ in range(100):
    if '"ready": true' in (o/'proxy.log').read_text():break
    if p.poll() is not None:raise RuntimeError('proxy failed')
    time.sleep(.05)
   else:raise RuntimeError('readiness timeout')
   m.command([str(m.SERVER/'bin/java'),'-cp',cp,'Roundtrip','18537',str(o/'roundtrip.json')],o/'calibration',60)
   url='jdbc:mysql://127.0.0.1:18537/jac_alignment_utf8?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true'
   subprocess.run([sys.executable,str(H/'run.py'),'time','--out',str(o/'timing'),'--url',url],check=True)
   m.command([str(m.SERVER/'bin/java'),'-cp',cp,'Roundtrip','18537',str(o/'roundtrip-after.json')],o/'calibration-after',60)
  finally:
   if p.poll() is None:p.send_signal(signal.SIGTERM)
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:p.kill();p.wait()
   (o/'proxy-process.json').write_text(json.dumps({'pid':p.pid,'returncode':p.returncode,'stopped':p.poll() is not None}))
 rows=[json.loads(x) for x in (o/'timing/rows.jsonl').read_text().splitlines()];print(rows[0],flush=True)
 rr=[x for x in rows if not x['warmup']];assert len(rr)==30 and all(x['oracle_ok'] and x['questions']==4 for x in rows)
 summary[str(delay)]={'median_ms':statistics.median(x['ms'] for x in rr),'thread_cpu_median_ms':statistics.median(x['thread_cpu_ms'] for x in rr),'samples':len(rr),'commands':4,'roundtrip_median_ms':statistics.median(json.loads((o/'roundtrip.json').read_text()))}
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary,flush=True)
