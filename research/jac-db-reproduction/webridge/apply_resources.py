#!/usr/bin/env python3
"""Partition physical cores, keeping each pair of SMT siblings together."""
import json,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent;W=R.parents[1]/'webridge'
sets={'online':'0-3,10-13','database':'4-7,14-17','driver':'8,18','offline':'9,19'}
receipts=[]
subprocess.run(['docker','update','--cpuset-cpus',sets['database'],'jac-webridge-paper-mysql5725'],check=True,capture_output=True)
for d in Path('/proc').iterdir():
 if not d.name.isdigit():continue
 try:args=(d/'cmdline').read_bytes().split(b'\0');s=b' '.join(args).decode(errors='replace')
 except (FileNotFoundError,PermissionError,ProcessLookupError):continue
 if not args or not args[0].decode(errors='replace').endswith('/bin/java'):continue
 role=None
 if str(R/'paper-driver/build/libs/webench-1.0-SNAPSHOT.jar') in s:role='driver'
 elif str(W/'Application/my-blog/target/my-blog-4.0.0-SNAPSHOT.jar') in s:
  try:cwd=(d/'cwd').resolve();role='offline' if cwd==R/'paper/offline' else 'online' if cwd==R/'paper/online' else None
  except (FileNotFoundError,PermissionError):pass
 elif 'PaperCompilerServer' in s and str(R) in s:role='offline'
 if role:
  p=subprocess.run(['taskset','-apc',sets[role],d.name],text=True,capture_output=True,check=True)
  receipts.append({'pid':int(d.name),'role':role,'cpus':sets[role],'command':s,'taskset':p.stdout})
payload=json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'sets':sets,'receipts':receipts},indent=2)+'\n'
(R/'paper/physical-core-partition.json').write_text(payload)
(R/('paper/physical-core-partition-'+time.strftime('%Y%m%dT%H%M%S',time.gmtime())+'.json')).write_text(payload)
print(json.dumps(sets))
