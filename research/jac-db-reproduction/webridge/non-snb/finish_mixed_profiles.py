#!/usr/bin/env python3
"""Finish analysis after the separately verified connection-init counter windows."""
import hashlib,json,pathlib,subprocess,sys,time
from measurement_lease import lease
H=pathlib.Path(__file__).resolve().parent
receipt=H/'profiles'/('finish-mixed-'+str(time.time_ns()))
receipt.mkdir()
source=H/'analyze_mysql_profile.py'
frozen=receipt/'analyzer-source.py';frozen.write_bytes(source.read_bytes())
records=[]
for name in ['1792555546513752376','1792555553389885692']:
 batch=H/'profiles'/('littlex-batch-'+name)
 row=json.loads((batch/'summary.json').read_text())[0]
 out=pathlib.Path(row['out'])
 assert json.loads((out/'business-verification.json').read_text())['status']=='PASS'
 commands=[entry['argv'] for entry in row['commands'][2:]]
 commands[0][1]=str(frozen)
 commands.append([sys.executable,str(H/'littlex/verify_outputs.py'),'--tier','t200','--plan',str(pathlib.Path(row['inputs'])/'plan.json'),'--results',str(out/'run/full-results.jsonl.gz'),'--out',str(out/'independent-results.json')])
 results=[]
 with lease('Finalize measured mixed SQL profile '+name,receipt/(name+'-lease.json')):
  for i,cmd in enumerate(commands):
   r=subprocess.run(cmd,capture_output=True,text=True)
   (receipt/(name+'-'+str(i)+'.stdout')).write_text(r.stdout)
   (receipt/(name+'-'+str(i)+'.stderr')).write_text(r.stderr)
   results.append({'argv':cmd,'returncode':r.returncode})
   if r.returncode:break
 records.append({'profile':str(out),'commands':results,'status':'PASS' if all(x['returncode']==0 for x in results)else'FAIL','original_batch_status_retained':row['status']})
 (receipt/'summary.json').write_text(json.dumps(records,indent=2)+'\n')
 print(name,records[-1]['status'],flush=True)
print(receipt)
assert all(x['status']=='PASS'for x in records)
