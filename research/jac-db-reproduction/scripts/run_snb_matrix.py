"""Serialized reproduction stages; formal latency uses SQL logging disabled."""
import json, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PY=str(ROOT/'runtime/venv314/bin/python')
STAGES=[
 ('logging-off-baseline',['scripts/db_settings.py','off']),
 ('baseline-latency',['scripts/gate.py','--tag','baseline-latency','--warm','0','--rounds','2']),
 ('baseline-other-parity',['scripts/gate.py','--tag','baseline-other-parity','--queries','is1,is2,is3,ic1,ic2,ic13','--warm','0','--rounds','1']),
 ('baseline-profile-logging',['scripts/db_settings.py','duration']),
 ('baseline-profile',['scripts/profile_ic5.py','--tag','baseline-profile','--repeats','3','--warmups','0']),
 ('baseline-profile-off',['scripts/db_settings.py','off']),
 ('final-start',['scripts/manage.py','start','jac','--variant','final']),
 ('final-warm',['scripts/gate.py','--tag','final-warm','--queries','is1,is2,is3,ic1,ic2,ic5,ic13','--warm','0','--rounds','1']),
 ('final-census-on',['scripts/db_settings.py','census']),
 ('final-census',['scripts/gate.py','--tag','final-census','--warm','1','--rounds','1','--census']),
 ('final-census-off',['scripts/db_settings.py','off']),
 ('final-latency',['scripts/gate.py','--tag','final-latency','--queries','is1,is2,is3,ic1,ic2,ic5,ic13','--warm','0','--rounds','3']),
 ('final-profile-on',['scripts/db_settings.py','duration']),
 ('final-profile',['scripts/profile_ic5.py','--tag','final-profile','--repeats','5','--warmups','2']),
 ('final-profile-off',['scripts/db_settings.py','off']),
]
def main():
 progress=[]
 for name,args in STAGES:
  print(f'START {name}',flush=True);start=time.time()
  with (ROOT/f'logs/stage-{name}.log').open('w') as handle:
   result=subprocess.run([PY,*args],cwd=ROOT,stdout=handle,stderr=subprocess.STDOUT)
  progress.append({'stage':name,'started_unix':start,'seconds':time.time()-start,'exit':result.returncode})
  (ROOT/'results/snb-stage-progress.json').write_text(json.dumps(progress,indent=2))
  print(f'DONE {name} exit={result.returncode} seconds={time.time()-start:.1f}',flush=True)
  if result.returncode:raise SystemExit(result.returncode)
if __name__=='__main__':main()
