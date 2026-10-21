#!/usr/bin/env python3
"""Freeze completed owner latency publications and optionally run offline attribution."""
import argparse,collections,datetime,hashlib,json,pathlib,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;N=H.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def key(c):return(c['family'],c['workload'],c.get('tweets_per_user'),c.get('write_percent'),c['arm'],c['delay_ms'])
p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');p.add_argument('--run',action='store_true');a=p.parse_args();deadline=time.monotonic()+3600
paths=[N/'native/normalized-rtt-latency.json',N/'tpcc/normalized-rtt-latency.json',N/'littlex/normalized-rtt-results.json']
while True:
 raw=[p.read_bytes()for p in paths];data=[json.loads(b)for b in raw];cells=[x if isinstance(x,list)else[c for c in x['cells']if c.get('method','latency')=='latency']for x in data];counts=list(map(len,cells))
 if counts==[162,126,360]:break
 assert a.wait and time.monotonic()<deadline,counts
 time.sleep(5)
assert all(r['status']=='accepted'for r in cells[0]);rows=[r for chunk in cells for r in chunk];assert len(rows)==648 and len({key(c)for c in rows})==648
assert collections.Counter(r['status']for r in rows)=={'accepted':495,'failed_with_stage_evidence':153}
output=H/'final-input.json';assert not output.exists(),'Preserve existing frozen input'
provenance={'created_utc':now(),'scope':'648 terminal PRIMARY latency cells; references excluded','owner_counts':counts,'sources':[{'path':str(p),'sha256':sha(b),'bytes':len(b)}for p,b in zip(paths,raw)],'freezer_source_sha256':sha(pathlib.Path(__file__).read_bytes()),'attribution_helper_sha256':sha((H/'analyze.py').read_bytes())}
payload={'schema':2,'metric':'rtt','latency':rows,'provenance':provenance};encoded=(json.dumps(payload,indent=2)+'\n').encode();output.write_bytes(encoded);provenance['frozen_input_sha256']=sha(encoded);(H/'final-input-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n');print(now(),'frozen648',flush=True)
if a.run:
 command=[sys.executable,str(H/'analyze.py'),'--results',str(output),'--out',str(H/'final')];(H/'final-command.json').write_text(json.dumps({'started_utc':now(),'argv':command},indent=2)+'\n');r=subprocess.run(command);assert r.returncode==0,r.returncode
