"""Separate SQL/protocol instrumentation after quiet timing."""
import pathlib,subprocess,sys,json,time,os,signal
R=pathlib.Path(__file__).resolve().parent;J=R.parents[1]/'jac-comparison';out=R/'profiles';out.mkdir(exist_ok=False)
for delay in [0,2]:
 for variant in ['baseline','final']:
  d=out/f'delay-{delay}ms'/variant;d.mkdir(parents=True);control=d/'control.txt';control.write_text('idle');cmd=[sys.executable,str(J/'roundtrip-profile/trace_proxy.py'),'--port','18532','--delay-ms',str(delay),'--control',str(control),'--out',str(d/'trace')];log=(d/'proxy.stdout').open('w');err=(d/'proxy.stderr').open('w');proxy=subprocess.Popen(cmd,stdout=log,stderr=err,start_new_session=True);(d/'proxy-command.json').write_text(json.dumps(cmd))
  try:
   for _ in range(100):
    if proxy.poll()is not None:raise RuntimeError('Proxy exited')
    if(d/'proxy.stdout').stat().st_size:break
    time.sleep(.05)
   command=[sys.executable,str(R/'measure.py'),'--variant',variant,'--profile-control',str(control),'--out',str(d/'requests')];(d/'command.json').write_text(json.dumps(command));r=subprocess.run(command,capture_output=True,text=True);(d/'driver.stdout').write_text(r.stdout);(d/'driver.stderr').write_text(r.stderr);assert r.returncode==0,r.stderr
  finally:
   if proxy.poll()is None:os.killpg(proxy.pid,signal.SIGTERM)
   try:proxy.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(proxy.pid,signal.SIGKILL);proxy.wait()
   log.close();err.close();(d/'cleanup.json').write_text(json.dumps({'proxy_stopped':True,'returncode':proxy.returncode}));assert proxy.returncode==0
  print(json.dumps({'delay':delay,'variant':variant,'done':True}),flush=True)
