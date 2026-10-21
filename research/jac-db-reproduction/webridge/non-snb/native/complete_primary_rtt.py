"""Persist the authorized original native plans with per-case-pair compact DB RTT leases."""
import pathlib,json,subprocess,sys,time,datetime,hashlib
R=pathlib.Path(__file__).resolve().parent;O=R/'primary-rtt-controller';O.mkdir(exist_ok=False)
state={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'completed':['Primary first pair: littlex-rtt-pilot original/final t20 feed0ms; do not rerun duplicate keys.']};commands=[]
def save():(O/'progress.json').write_text(json.dumps(state,indent=2)+'\n')
def run(label,args):
 state['current']=label;state['current_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();cmd=[sys.executable,*map(str,args)];commands.append({'label':label,'argv':cmd});(O/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');print(label,flush=True);subprocess.run(cmd,check=True);state['completed'].append(label);save()
def lx(tier,label,delay,reference=False):
 name=('littlex-rtt-reference-'if reference else'littlex-rtt-latency-')+tier+'-'+label+'-'+str(delay)
 run('collect '+name,[R/'timing_rtt_littlex.py','--output',name,'--tiers',tier,'--only',label,'--delays',str(delay),'--method','reference'if reference else'latency']);run('verify '+name,[R/'finalize_rtt_littlex.py',name])
def tp(label,delay,reference=False):
 name=('tpcc-rtt-reference-'if reference else'tpcc-rtt-latency-')+label+'-'+str(delay)
 run('collect '+name,[R/'timing_rtt_tpcc.py','--output',name,'--only',label,'--delays',str(delay),*(['--reference']if reference else[])]);run('verify '+name,[R/'finalize_rtt_tpcc.py',name])
try:
 state['current']='waiting for independent compact pilot alignment';save()
 while True:
  p=R/'compact-pilot-alignment.json';receipt=R/'compact-pilot-alignment-lease.json'
  if p.exists()and receipt.exists():
   d=json.loads(receipt.read_text())
   if 'released_utc'in d:assert 'error'not in d and d.get('returncode',0)==0;assert json.loads(p.read_text())['PASS'];break
  time.sleep(3)
 for tier in ['t20','t50','t100','t200']:
  for label in ['W1-feed','W2-like','W2-follow','W2-create_tweet']:
   for delay in [0,2,10]:
    if tier=='t20'and label=='W1-feed'and delay==0:continue
    lx(tier,label,delay)
 for mix in [0,5,15,30]:
  for delay in [0,2,10]:lx('t200','W3-'+str(mix),delay)
 for label in ['payment_name_GC','new_order_rollback','payment_id_GC','new_order_5','new_order_15','payment_name_BC','payment_id_BC']:
  for delay in [0,2,10]:tp(label,delay)
 for tier in ['t20','t50','t100','t200']:
  for label in ['W1-feed','W2-like','W2-follow','W2-create_tweet']:lx(tier,label,0,True)
 for mix in [0,5,15,30]:lx('t200','W3-'+str(mix),0,True)
 tp('original900',0,True)
 run('strict public inventory',[R.parent/'measurement_lease.py','--label','Final native primary RTT public inventory','--receipt',R/'primary-rtt-public-inventory-lease.json','--',sys.executable,R/'public_manifest.py','--strict'])
 state['status']='PASS';state['current']='complete';save()
except BaseException as e:state['status']='FAILED';state['error']=repr(e);save();raise
