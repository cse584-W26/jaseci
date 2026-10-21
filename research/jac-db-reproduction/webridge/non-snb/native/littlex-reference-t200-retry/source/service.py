"""Launch only isolated matched-fixture Jac copies; preserve source and launch receipts."""
import argparse,pathlib,subprocess,os,json,time,urllib.request,signal,hashlib,shutil
R=pathlib.Path(__file__).resolve().parent;REPRO=R.parents[3]
p=argparse.ArgumentParser();p.add_argument('action',choices=['start','stop','prepare']);p.add_argument('--variant',choices=['baseline','final'],required=True);p.add_argument('--database',default='jac_wb_lx_t20_20261020');p.add_argument('--socket',default='/tmp/jacpg-d6275e76eb');p.add_argument('--port',type=int,default=18134);p.add_argument('--db-host');p.add_argument('--db-port',type=int,default=5432);a=p.parse_args();home=R/a.variant;home.mkdir(exist_ok=True);pidfile=home/'service.pid';app=home/'app';original=REPRO/'littlex/historical-app-source';source=REPRO/'runtime/ad469-source/jac' if a.variant=='baseline' else REPRO.parent/'jac-db/jac'
if a.action=='stop':
 if pidfile.exists():
  pid=int(pidfile.read_text());proc=pathlib.Path('/proc')/str(pid)
  if proc.exists() and (proc/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':
   assert (proc/'cwd').resolve()==app.resolve();os.killpg(pid,signal.SIGTERM)
   for _ in range(300):
    if not proc.exists() or (proc/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z':break
    time.sleep(.1)
   else:raise RuntimeError('Owned Jac service did not stop')
  stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime());archive=R/'launch-history'/(a.variant+'-'+stamp);archive.mkdir(parents=True,exist_ok=False)
  for name in ['launch.json','source.json','server.log']:
   if(home/name).exists():shutil.copy2(home/name,archive/name)
  pidfile.unlink()
 (home/'stopped.json').write_text(json.dumps({'pidfile_removed':True,'variant':a.variant}));raise SystemExit()
assert not pidfile.exists();app.mkdir(exist_ok=True)
for name in [f.name for f in original.glob('*.jac')]:
 (app/name).write_bytes((original/name).read_bytes())
(app/'jac.toml').write_text('[project]\nname="littlex-webridge"\nversion="1.0.0"\nentry-point="main.jac"\n[dev]\njaclang_source="'+str(source)+'"\n')
receipt={'variant':a.variant,'database':a.database,'source':str(source),'source_commit':subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),'source_files_sha256':{name:hashlib.sha256((app/name).read_bytes()).hexdigest() for name in ['main.jac','app.jac','import_data.jac']},'app':str(app),'python':str(REPRO/'runtime/venv314/bin/python')};(home/'source.json').write_text(json.dumps(receipt,indent=2))
if a.action=='prepare':raise SystemExit()
env=os.environ.copy();env.update(PYTHONUNBUFFERED='1',JAC_CACHE_HOME=str(REPRO/'dbcache'),JAC_DB_URL=('postgresql://jac@'+a.db_host+':'+str(a.db_port)+'/'+a.database if a.db_host else 'postgresql://jac@/'+a.database+'?host='+a.socket),JAC_PG_VERSION='18',JAC_PG_DIST='/home/baichuan/.cache/jac/pg/dist/linux-amd64-18.6.0',JAC_API_LEAN_RESPONSE='1',JAC_ACCESS_LOG='0',JAC_REPORT_ECHO='0',JAC_TIMING_HEADERS='1',JAC_PG_POOL='1',JAC_PG_ENSURE_CACHE='1',JAC_PG_DRIVER='psycopg',JAC_STICKY_DENY='1',JAC_RO_WALKERS='')
env.update(PYTHONPATH=str(source),JAC_NO_DEV_SOURCE='1',JAC_NO_PRECOMPILE='1',XDG_CACHE_HOME=str(REPRO/'runtime'/('cache314-ad469'if a.variant=='baseline'else'cache314')),JAC_LLVM_SHIM=str(REPRO/'runtime/lib/libjacllvm.so'))
env.update(PERF='1')
if a.variant=='baseline':env.update(JAC_STREAM_LATERAL='1',JAC_SQL_ACL='1',JAC_FUSED_FEED='1',JAC_STICKY_DENY='1')
else:
 for key in ['JAC_STREAM_LATERAL','JAC_SQL_ACL','JAC_FUSED_FEED','JAC_STICKY_DENY']:env.pop(key,None)
for k in ['JAC_LAZY_TXN','JAC_EDGE_ONLY_DIRTY']:env.pop(k,None)
cmd=['taskset','-c','9,19',str(REPRO/'runtime/venv314/bin/python'),str(REPRO/'webridge/jac-comparison/connection_shim.py'),'start','main.jac','-p',str(a.port),'--no-client']
with (home/'server.log').open('w')as f:proc=subprocess.Popen(cmd,cwd=app,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
pidfile.write_text(str(proc.pid));(home/'launch.json').write_text(json.dumps(receipt|{'pid':proc.pid,'command':cmd,'port':a.port,'environment':{k:v for k,v in env.items() if k.startswith('JAC_')}},indent=2))
for _ in range(240):
 if proc.poll() is not None:raise RuntimeError('Jac exited '+str(proc.returncode))
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+str(a.port)+'/healthz',timeout=2)as r:
   if r.status==200:print(json.dumps({'ready':True,'pid':proc.pid,'variant':a.variant}));break
 except Exception:pass
 time.sleep(1)
else:raise RuntimeError('Startup timeout')
