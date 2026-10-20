import pathlib,subprocess,json,sys,os,signal,time,hashlib
R=pathlib.Path(__file__).resolve().parent;out=R/'results';out.mkdir(exist_ok=False);(out/'sources.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in [R/'trace_proxy.py',R/'profile_driver.py',pathlib.Path(__file__)]},indent=2))
for delay in [0,2]:
 d=out/('delay-'+str(delay)+'ms');d.mkdir();control=d/'control.txt';control.write_text('warmup');cmd=['taskset','-c','9,19',sys.executable,str(R/'trace_proxy.py'),'--delay-ms',str(delay),'--control',str(control),'--out',str(d/'trace')];(d/'proxy-command.json').write_text(json.dumps(cmd));log=(d/'proxy.stdout').open('w');err=(d/'proxy.stderr').open('w');p=subprocess.Popen(cmd,stdout=log,stderr=err,start_new_session=True)
 try:
  for _ in range(100):
   if p.poll()is not None:raise RuntimeError('Traceproxy failed')
   if(d/'proxy.stdout').stat().st_size:break
   time.sleep(.05)
  for variant in ['baseline','final']:
   c=['taskset','-c','9,19',sys.executable,str(R/'profile_driver.py'),'--mode','census','--variant',variant,'--db-host','127.0.0.1','--db-port','18532','--warm','10','--measure','3','--out',str(d/variant),'--trace-control',str(control)];(d/(variant+'-command.json')).write_text(json.dumps(c));print(json.dumps({'delay_ms':delay,'variant':variant,'state':'start'}),flush=True);r=subprocess.run(c,capture_output=True,text=True);(d/(variant+'.stdout')).write_text(r.stdout);(d/(variant+'.stderr')).write_text(r.stderr);assert r.returncode==0,r.stderr;print(json.dumps({'delay_ms':delay,'variant':variant,'state':'done'}),flush=True)
 finally:
  if p.poll()is None:os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();raise
  log.close();err.close();(d/'proxy-exit.json').write_text(json.dumps({'pid':p.pid,'returncode':p.returncode,'stopped':True}));assert p.returncode==0
for p in out.rglob('*'):
 if p.is_file()and(p.suffix in ['.bin','.gz']or p.name=='events.jsonl'):p.chmod(0o600)
(out/'completed.json').write_text(json.dumps({'all_pass':True,'conditions':[0,2],'warmup':10,'profile_requests_per_variant_condition':3,'proxies_stopped':True}));print(out)
