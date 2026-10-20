#!/usr/bin/env python3
"""Read-only CPU/RSS host sampling; enforce recorded affinity on each new arm before warmup ends."""
import argparse,json,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=2000);a=p.parse_args()
mysqlpid=int(subprocess.check_output(['docker','inspect','-f','{{.State.Pid}}','jac-webridge-paper-mysql5725'],text=True))
seen=set();end=time.monotonic()+a.seconds
with (R/'paper/host-samples.jsonl').open('a') as out:
 while time.monotonic()<end:
  roles={'mysql':mysqlpid}
  pidfile=R/'paper/online.pid'
  if pidfile.exists():
   try:roles['online']=int(pidfile.read_text())
   except (ValueError,FileNotFoundError):pass
  if roles.get('online') and roles['online'] not in seen:
   # Only called on service creation, during warmup; never migrate an established timed arm.
   subprocess.run(['python3',str(R/'apply_resources.py')],check=True,capture_output=True);seen.add(roles['online'])
  row={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'monotonic':time.monotonic(),'loadavg':Path('/proc/loadavg').read_text().strip(),'processes':{}}
  for role,pid in roles.items():
   try:
    stat=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split();status=Path(f'/proc/{pid}/status').read_text()
    row['processes'][role]={'pid':pid,'user_ticks':int(stat[11]),'system_ticks':int(stat[12]),'status':{x.split(':',1)[0]:x.split(':',1)[1].strip() for x in status.splitlines() if x.split(':',1)[0] in ['VmRSS','VmHWM','Threads','Cpus_allowed_list','voluntary_ctxt_switches','nonvoluntary_ctxt_switches']}}
   except (FileNotFoundError,ProcessLookupError,PermissionError):pass
  row['memory']={x.split(':',1)[0]:x.split(':',1)[1].strip() for x in Path('/proc/meminfo').read_text().splitlines() if x.split(':',1)[0] in ['MemAvailable','SwapFree','Dirty']}
  out.write(json.dumps(row)+'\n');out.flush();time.sleep(5)
