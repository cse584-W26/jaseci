#!/usr/bin/env python3
"""Finalize small packaging logs/source entries after their writers have exited."""
import hashlib,json,pathlib,time
H=pathlib.Path(__file__).resolve().parent.parent;p=H/'PUBLIC_FILES.json';d=json.loads(p.read_text());files={r['path']:r for r in d['files']}
for name in ['summarize.py','primary-rtt/package_final.py','primary-rtt/package.stdout.log','primary-rtt/package.stderr.log','primary-rtt/refresh_small_receipts.py']:
 f=H/name;files[str(f)]={'path':str(f),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
d['files']=list(files.values());p.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({'status':'PASS','files':len(files),'maximum_file_bytes':max(r['bytes']for r in files.values()),'small_receipts_finalized':True}))
