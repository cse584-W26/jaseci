"""Serialized matched-fixture Jac latency sweep using the shared response proxy."""
import argparse,pathlib,json,subprocess,sys,time,signal,os,hashlib,statistics
import psycopg
R=pathlib.Path(__file__).resolve().parent;J=R.parents[1]/'jac-comparison';W=J.parent;p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--port',type=int,default=18532);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);proxy_script=W/'latency-comparison/proxy.py';(out/'sources.json').write_text(json.dumps({str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [pathlib.Path(__file__),proxy_script,R/'measure.py',J/'service.py']},indent=2));(out/'sweep-source.py').write_bytes(pathlib.Path(__file__).read_bytes())
def calibrate(name,host=None):
 kw={'user':'jac','dbname':'jac_webridge_matched_six_20261020','autocommit':True}
 if host:kw.update(host='127.0.0.1',port=a.port,sslmode='disable')
 else:kw.update(host='/tmp/jacpg-d6275e76eb')
 rows=[]
 with psycopg.connect(**kw)as c:
  for i in range(40):
   t=time.perf_counter();v=c.execute('SELECT 1').fetchone();ms=(time.perf_counter()-t)*1000;assert v==(1,);rows.append({'iteration':i,'warmup':i<10,'ms':ms})
 d={'transport':'proxyTCP'if host else'directUnix','n':30,'warmup':10,'median_ms':statistics.median(x['ms']for x in rows if not x['warmup']),'rows':rows};(out/(name+'.json')).write_text(json.dumps(d,indent=2));return d
calibrate('direct-unix-control')
for delay in [0,2,10]:
 d=out/('delay-'+str(delay)+'ms');d.mkdir();cmd=['taskset','-c','9,19',sys.executable,str(proxy_script),'--port',str(a.port),'--delay-ms',str(delay),'--unix','/tmp/jacpg-d6275e76eb/.s.PGSQL.5432','--receipt',str(d/'proxy-stop.json')];(d/'proxy-command.json').write_text(json.dumps(cmd,indent=2));log=(d/'proxy.stdout').open('w');err=(d/'proxy.stderr').open('w');proxy=subprocess.Popen(cmd,stdout=log,stderr=err,start_new_session=True);(d/'proxy-pid.json').write_text(json.dumps({'pid':proxy.pid,'pgid':proxy.pid}));
 try:
  for _ in range(100):
   if proxy.poll()is not None:raise RuntimeError('Proxy exited')
   if(d/'proxy.stdout').stat().st_size:break
   time.sleep(.05)
  else:raise RuntimeError('Proxy readiness timeout')
  before=calibrate('rtt-'+str(delay)+'ms-before',True)
  for variant in ['baseline','final']:
   modes=['timing']
   for mode in modes:
    target=d/mode/variant;command=['taskset','-c','9,19',sys.executable,str(R/'measure.py'),'--variant',variant,'--out',str(target)];(d/(mode+'-'+variant+'-command.json')).write_text(json.dumps(command,indent=2));print(json.dumps({'delay_ms':delay,'variant':variant,'mode':mode,'state':'start'}),flush=True);r=subprocess.run(command,capture_output=True,text=True);(d/(mode+'-'+variant+'.stdout')).write_text(r.stdout);(d/(mode+'-'+variant+'.stderr')).write_text(r.stderr);assert r.returncode==0,(variant,delay,mode,r.stderr);print(json.dumps({'delay_ms':delay,'variant':variant,'mode':mode,'state':'done'}),flush=True)
  calibrate('rtt-'+str(delay)+'ms-after',True)
 finally:
  if proxy.poll()is None:
   os.killpg(proxy.pid,signal.SIGTERM)
   try:proxy.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(proxy.pid,signal.SIGKILL);proxy.wait();raise RuntimeError('Proxy required forced cleanup')
  log.close();err.close();(d/'proxy-exit.json').write_text(json.dumps({'returncode':proxy.returncode,'pid':proxy.pid,'stopped':True}));assert proxy.returncode==0
calibrate('direct-unix-after');(out/'completed.json').write_text(json.dumps({'all_conditions_complete':True,'all_proxies_stopped':True,'conditions_ms':[0,2,10]}));print(out)
