"""Pay lazy DDL before opening any measured window."""
import json,sys,time
from pathlib import Path
import httpx
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'benchmark/scripts'))
from bench_timed import SNB_QUERIES,build_surviving,issue_snb
from snb_validate import Jac
ctx=Jac('jaseci-pg');rows=build_surviving(ctx,20)
with httpx.Client(base_url='http://127.0.0.1:18109',timeout=900) as c:
 for q,m in SNB_QUERIES.items():
  idx,row=rows[m['file']][0];times=[]
  for attempt in range(8):
   ms,server,out,err=issue_snb('jaseci-pg',c,ctx,{},q,row);times.append(ms)
   print(f'{q} attempt={attempt} ms={ms:.1f} server={server} error={err}',flush=True)
   if attempt>=1 and not err and max(times[-2:])<=2*min(times):break
  if err:raise RuntimeError(f'{q}: {err}')
