"""Finish bounded native littleX groups; each live or heavy stage acquires the common lease."""
import datetime,hashlib,json,pathlib,subprocess,sys,time
R=pathlib.Path(__file__).resolve().parent;O=R/'littlex-completion-controller';O.mkdir(exist_ok=False)
state={'script_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'completed':[]};commands=[]
def save(): (O/'progress.json').write_text(json.dumps(state,indent=2)+'\n')
def run(label,args):
    state['current']=label;state['current_started_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();command=[sys.executable,*map(str,args)];commands.append({'label':label,'argv':command});(O/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');print('STAGE',label,flush=True);subprocess.run(command,check=True);state['completed'].append(label);save()
def finish(name,protocol=False,chunk=False):
    selected=json.loads((R/('littlex-profile-selections.json'if protocol else'latency-selections.json')).read_text());selected=selected if protocol else selected['references'if 'reference'in name else'littleX']
    marker=name if protocol else name+'/summary.json'
    if marker in selected:return
    run('verify/export '+name,[R/'finalize_littlex.py','--input',name,*(['--protocol']if protocol else[]),*(['--chunk-feeds']if chunk else[])])
try:
    state['current']='waiting for already-queued mix5';save();deadline=time.monotonic()+3*3600
    while True:
        p=R/'littlex-timing-mix5/lease.json'
        if p.exists():
            rec=json.loads(p.read_text())
            if 'released_utc'in rec:assert 'error'not in rec,rec;break
        assert time.monotonic()<deadline,'Queued mix5 did not finish within three hours';time.sleep(5)
    for name in ['littlex-timing-mix0','littlex-timing-mix5']:finish(name)
    for mix in [15,30]:
        name='littlex-timing-mix'+str(mix);run('quiet '+name,[R/'timing_littlex.py','--output',name,'--tiers','t200','--delays','0,2,10','--only','W3-'+str(mix)]);finish(name)
    name='littlex-profiles-mixes';run('diagnostic full100-slot W3 protocols',[R/'timing_littlex.py','--output',name,'--tiers','t200','--delays','2','--only','W3-0,W3-5,W3-15,W3-30','--instrument','--profile-measured','100']);finish(name,protocol=True)
    for tier in ['t20','t50','t100','t200']:
        name='littlex-reference-'+tier;run('quiet reference '+name,[R/'timing_littlex.py','--method','reference','--output',name,'--tiers',tier,'--delays','0','--only','W1-feed,W2-like,W2-follow,W2-create_tweet']);finish(name,chunk=True)
    for mix in [0,5,15,30]:
        name='littlex-reference-mix'+str(mix);run('quiet reference '+name,[R/'timing_littlex.py','--method','reference','--output',name,'--tiers','t200','--delays','0','--only','W3-'+str(mix)]);finish(name)
    run('public trace metadata export',[R/'export_native_traces.py','--receipt',R/'public-trace-export-lease.json'])
    run('final public inventory',[R/'public_manifest.py','--strict']);state['status']='PASS';state['current']='complete';save();print('ALL NATIVE LITTLE X STAGES PASS',flush=True)
except BaseException as error:
    state['status']='FAILED';state['error']=repr(error);save();raise
