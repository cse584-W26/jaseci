#!/usr/bin/env python3
"""Build/freeze the final littleX driver and run the finite genuine compilation matrix."""
import pathlib,subprocess,json,sys,time,hashlib
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
p=H/('genuine-batch-'+str(time.time_ns()));p.mkdir();rows=[]
def save(): (p/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
def call(argv,label):
 out=p/label;out.mkdir();r=subprocess.run(argv,capture_output=True);(out/'command.json').write_text(json.dumps(argv,indent=2));(out/'stdout.log').write_bytes(r.stdout);(out/'stderr.log').write_bytes(r.stderr);row={'stage':label,'returncode':r.returncode,'logs':str(out)};rows.append(row);save();print(label,r.returncode,flush=True);return r
with lease('littlex final timer build and immutable freeze',p/'build.lease.json'):
 r=call([sys.executable,str(H/'build.py')],'build');assert r.returncode==0
 r=call([sys.executable,str(H/'freeze_build.py')],'freeze');assert r.returncode==0
 frozen=r.stdout.decode().strip().splitlines()[-1];(p/'final-build-snapshot.json').write_text(json.dumps({'path':frozen},indent=2)+'\n');(H/'final-build-snapshot.json').write_text(json.dumps({'path':frozen,'batch':str(p)},indent=2)+'\n')
overlay=H/'compat/dml-positional/e51966e0c4a82870907a7ef053bfc4562ee33721fd7d4dc894f7c7ff48337128/classes'
for impl in ['LittleXSql','LittleXFull','LittleXPruned']:
 for op in ['follow','create_tweet','like','feed_page','feed']:
  if impl=='LittleXSql'and op=='like':
   recovered=sorted(H.glob('compiler-retry-*/summary.json'))
   if recovered:
    rr=json.loads(recovered[-1].read_text());meta=json.loads((pathlib.Path(rr['case'])/'metadata.json').read_text())
    if rr['status'].startswith('PASS')and meta['manifest']['source']['LittleXSql.java']==hashlib.sha256((H/'LittleXSql.java').read_bytes()).hexdigest():
     rows.append({'stage':impl+'-'+op,'status':'reused genuine accepted case; identical business implementation source','case':rr['case'],'compiler_retry':str(recovered[-1])});save();continue
  tier='t200'if op=='feed_page'else't20';r=call([sys.executable,str(H/'pipeline.py'),'--implementation',impl,'--operations',op,'--tier',tier,'--attempt','final-sdk-'+p.name,'--synth-overlay',str(overlay)],impl+'-'+op)
  manifests=[x for x in r.stdout.decode(errors='replace').splitlines()if x.startswith(str(H/'pipeline-'))]
  if manifests:rows[-1]['pipeline_summary']=str(pathlib.Path(manifests[-1])/'summary.json');save()
print(p)
