"""Persistently collect direct server-phase case pairs, yielding the lease after each stage."""
import pathlib,json,subprocess,sys,time,datetime,hashlib
R=pathlib.Path(__file__).resolve().parent;O=R/'db-time-analysis/direct-zero-controller';O.mkdir(exist_ok=False)
state={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'completed':[]};commands=[]
def save():(O/'progress.json').write_text(json.dumps(state,indent=2)+'\n')
def run(label,args):
 state['current']=label;state['current_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();cmd=[sys.executable,*map(str,args)];commands.append({'label':label,'argv':cmd});(O/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');print(label,flush=True);subprocess.run(cmd,check=True);state['completed'].append(label);save()
try:
 state['current']='waiting for direct t20 feed pilot';save()
 while True:
  p=R/'littlex-db-only-zero-pilot/lease.json'
  if p.exists():
   d=json.loads(p.read_text())
   if 'released_utc'in d:assert 'error'not in d,d;break
  time.sleep(3)
 run('verify pilot',[R/'finalize_db_only.py','littlex-db-only-zero-pilot'])
 for tier in ['t20','t50','t100','t200']:
  for label in ['W1-feed','W2-like','W2-follow','W2-create_tweet']:
   if tier=='t20'and label=='W1-feed':continue
   name='littlex-db-only-zero-'+tier+'-'+label
   run('collect '+name,[R/'profile_server_only_littlex.py','--output',name,'--tiers',tier,'--only',label,'--profile-measured','30']);run('verify '+name,[R/'finalize_db_only.py',name])
 for mix in [0,5,15,30]:
  name='littlex-db-only-zero-mix'+str(mix);run('collect '+name,[R/'profile_server_only_littlex.py','--output',name,'--tiers','t200','--only','W3-'+str(mix),'--profile-measured','100']);run('verify '+name,[R/'finalize_db_only.py',name])
 run('public evidence inventory',[R.parent/'measurement_lease.py','--label','Native direct server-time public inventory','--receipt',R/'db-time-analysis/direct-zero/public-inventory-lease.json','--',sys.executable,R/'public_manifest.py','--strict'])
 state['status']='PASS';state['current']='complete';save()
except BaseException as e:state['status']='FAILED';state['error']=repr(e);save();raise
