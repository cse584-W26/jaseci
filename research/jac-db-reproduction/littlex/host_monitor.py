import json,time,subprocess
from pathlib import Path
from datetime import datetime,timezone
out=Path(__file__).resolve().parents[1]/'logs/littlex-host'/('samples-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.jsonl')
with out.open('w') as f:
 for i in range(900):
  row={'utc':datetime.now(timezone.utc).isoformat(),'proc_stat':Path('/proc/stat').read_text(),'loadavg':Path('/proc/loadavg').read_text(),'top_cpu':subprocess.check_output(['ps','-eo','pid,ppid,pcpu,pmem,comm','--sort=-pcpu'],text=True).splitlines()[:16]}
  f.write(json.dumps(row)+'\n');f.flush();time.sleep(1)
