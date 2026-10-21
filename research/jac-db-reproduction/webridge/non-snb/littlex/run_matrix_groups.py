#!/usr/bin/env python3
"""Run the required matrix in lease-bounded tier/implementation/method/RTT groups."""
import argparse,pathlib,json,subprocess,sys,time,shutil
H=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--build-snapshot',required=True);p.add_argument('--bundle-map',required=True);p.add_argument('--out',required=True,type=pathlib.Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);groups=[];aggregate=[]
for method in ['latency','reference']:
 for delay in ([0,2,10]if method=='latency'else[0]):
  for tier in ['t20','t50','t100','t200']:
   for impl in ['LittleXSql','LittleXFull','LittleXPruned']:
    free=shutil.disk_usage(H).free;assert free>10*1024**3,('Disk guard before group; reclaim verified duplicate payloads then resume',free)
    out=a.out/(method+'-'+str(delay)+'ms-'+tier+'-'+impl);argv=[sys.executable,str(H/'timing_sweep.py'),'--build-snapshot',a.build_snapshot,'--bundle-map',a.bundle_map,'--out',str(out),'--methods',method,'--delays',str(delay),'--tiers',tier,'--implementations',impl];log=a.out/(out.name+'.stdout.log');err=a.out/(out.name+'.stderr.log');(a.out/(out.name+'.command.json')).write_text(json.dumps(argv,indent=2)+'\n');start=time.time_ns()
    with log.open('wb')as stdout,err.open('wb')as stderr:r=subprocess.run(argv,stdout=stdout,stderr=stderr)
    group=dict(method=method,delay_ms=delay,tier=tier,implementation=impl,returncode=r.returncode,start_ns=start,end_ns=time.time_ns(),summary=str(out/'summary.json'),stdout=str(log),stderr=str(err));groups.append(group);(a.out/'groups.json').write_text(json.dumps(groups,indent=2)+'\n');assert r.returncode==0,group
    aggregate.extend(json.loads((out/'summary.json').read_text()));(a.out/'summary.json').write_text(json.dumps(aggregate,indent=2)+'\n');print(out.name,len(aggregate),flush=True)
assert len(groups)==48 and len(aggregate)==480,(len(groups),len(aggregate));print(a.out,flush=True)
