#!/usr/bin/env python3
"""Persistent lease-bounded primary RTT matrix controller."""
import argparse,hashlib,json,pathlib,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
selected=json.loads((H/'selected-cases.json').read_text());snapshot=json.loads((H/'final-build-snapshot.json').read_text());build=snapshot.get('snapshot',snapshot.get('path'));assert build,snapshot
sources={}
for name in ['compact_proxy.py','extract.py','sweep.py','run_groups.py','finish.py','run_complete.py']:
 src=H/'primary-rtt'/name;dest=a.out/'source'/name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(src.read_bytes());sources[name]=hashlib.sha256(dest.read_bytes()).hexdigest()
(a.out/'source-manifest.json').write_text(json.dumps(sources,indent=2)+'\n')
status={'status':'running','started_ns':time.time_ns(),'stages':[]};path=a.out/'status.json'
def save():path.write_text(json.dumps(status,indent=2)+'\n')
save()
try:
 for stage,argv in [('matrix',[sys.executable,str(H/'primary-rtt/run_groups.py'),'--build-snapshot',build,'--bundle-map',selected['bundle_map'],'--out',str(a.out/'matrix')]),('normalize',[sys.executable,str(H/'primary-rtt/finish.py'),'--summary',str(a.out/'matrix/summary.json')])]:
  row={'stage':stage,'started_ns':time.time_ns(),'command':argv};status['stages'].append(row);save()
  with(a.out/(stage+'.stdout.log')).open('wb')as stdout,(a.out/(stage+'.stderr.log')).open('wb')as stderr:r=subprocess.run(argv,stdout=stdout,stderr=stderr)
  row.update(returncode=r.returncode,finished_ns=time.time_ns());save();assert r.returncode==0,row
 status.update(status='complete',finished_ns=time.time_ns());save()
except BaseException as e:
 status.update(status='failed',error=repr(e),finished_ns=time.time_ns());save();raise
