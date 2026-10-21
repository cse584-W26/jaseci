#!/usr/bin/env python3
"""One final lease-owned compression/credential review/public allowlist refresh."""
import argparse,datetime,json,pathlib,subprocess,sys
D=pathlib.Path(__file__).resolve().parent;H=D.parent;N=H.parent;sys.path.insert(0,str(N));from measurement_lease import lease
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out=a.out.resolve();assert H not in a.out.parents,'Keep active receipt outside the allowlisted tree';a.out.mkdir(parents=True,exist_ok=False)
rows=json.loads((H/'normalized-rtt-latency.json').read_text());refs=json.loads((H/'rtt-reference-900-index.json').read_text());assert len(rows)==126 and len(refs['rows'])==6
with lease('TPC-C final public compact RTT evidence refresh',a.out/'lease.json'):
 for index,name in enumerate(['compress_public_states.py','public_files.py','review_public.py','public_files.py']):
  argv=[sys.executable,str(H/name)];r=subprocess.run(argv,capture_output=True,text=True);(a.out/(str(index)+'-'+name+'.stdout.log')).write_text(r.stdout);(a.out/(str(index)+'-'+name+'.stderr.log')).write_text(r.stderr);assert r.returncode==0,(name,r.stderr)
 review=json.loads((H/'public-credential-review.json').read_text());assert not review['findings_without_values'],'Public credential-pattern review requires attention'
 print('Public evidence refreshed',flush=True)
