#!/usr/bin/env python3
"""Optional all20 generated-procedure activation gate, serialized with diagnostic CALL profiles."""
import pathlib,sys,importlib.util,json,fcntl,time
H=pathlib.Path(__file__).resolve().parent;I=H.parents[1]/'integration';sp=importlib.util.spec_from_file_location('ctl',I/'control.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);sp=importlib.util.spec_from_file_location('driver',H/'profile_command.py');d=importlib.util.module_from_spec(sp);sp.loader.exec_module(d);out=H/('sp-gates-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));out.mkdir();result={}
with(I/'.mysql-sp-profile.lock').open('w')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 for q in sys.argv[1:]:
  dest=out/q;cmd=d.command(q,dest/'requests',55337,0,20,'sp');cmd.insert(1,'-Dsnb.gate=true')
  try:m.command(cmd,dest,60)
  except SystemExit:pass
  p=dest/'requests/rows.jsonl';rows=[json.loads(x)for x in p.read_text().splitlines()]if p.exists()else[];result[q]={'completed':len(rows),'all20exact':len(rows)==20 and all(x['oracle_ok']for x in rows),'all20sp_enabled':len(rows)==20 and all(x['sp_enabled_at_end']for x in rows),'questions':sorted({x['questions']for x in rows})};(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(out)
