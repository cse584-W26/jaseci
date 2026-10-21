#!/usr/bin/env python3
"""Publish complete littleX RTT evidence and bounded public response payloads."""
import importlib.util,json,pathlib,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('lease',H.parent/'measurement_lease.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
lease_path=H/'primary-rtt'/('package-lease-'+str(time.time_ns())+'.json')
with m.lease('littleX final source/RTT audit and public packaging',lease_path):
 data=json.loads((H/'normalized-rtt-results.json').read_text());assert data['latency_cells']==360 and data['reference_cells']==120
 sys.path.insert(0,str(H));from result_chunks import export
 payloads={r['full_results_logical_monolith']for r in data['cells']if r.get('full_results_logical_monolith')}
 chunks=[]
 for name in sorted(payloads):
  p=pathlib.Path(name)
  if p.stat().st_size>80*1024**2:chunks.append(str(export(p,p.with_name('full-results-public-chunks'))))
 (H/'primary-rtt/public-response-indexes.json').write_text(json.dumps(chunks,indent=2)+'\n')
 subprocess.run([sys.executable,str(H/'primary-rtt/finish.py'),'--summary',str(H/'primary-rtt/complete-final/matrix/summary.json')],check=True)
 for helper in [H/'primary-rtt/audit_final.py',H/'summarize.py',H/'public_manifest.py']:
  subprocess.run([sys.executable,str(helper)],check=True)
(H/'primary-rtt/package-complete.json').write_text(json.dumps({'status':'PASS','wall_ns':time.time_ns(),'normalized':str(H/'normalized-rtt-results.json'),'audit':str(H/'primary-rtt/final-audit.json'),'public_manifest':str(H/'PUBLIC_FILES.json'),'public_chunk_indexes':chunks},indent=2)+'\n')

# The released lease and completion receipt are finalized after the heavy manifest scan.
import hashlib
manifest_path=H/'PUBLIC_FILES.json';manifest=json.loads(manifest_path.read_text());files={r['path']:r for r in manifest['files']}
for p in [lease_path,H/'primary-rtt/package-complete.json',H/'primary-rtt/package.stdout.log',H/'primary-rtt/package.stderr.log']:
 files[str(p)]={'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
manifest['files']=list(files.values());manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
