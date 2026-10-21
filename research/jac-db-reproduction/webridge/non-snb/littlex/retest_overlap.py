#!/usr/bin/env python3
"""Replace two quiet groups preceding the first timestamped native cleanup verification."""
import pathlib,json,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;root=H/'timing/complete-1792552799038277631';out=H/'overlap-retests'/str(time.time_ns());out.mkdir(parents=True);replacement=[]
for impl in ['LittleXFull','LittleXPruned']:
 name='latency-0ms-t50-'+impl;old=root/name;scope={'accepted_for_primary_comparison':False,'reason':'Group precedes the first timestamped native PID/session absence check after a service-stop timeout; actual interference remains unmeasured','cleanup_boundary_utc':'2026-10-21T03:36:10.406864+00:00','cleanup_receipt':str(H.parent/'native/littlex-reference-t200/cleanup-recovery.json')};(old/'scope.json').write_text(json.dumps(scope,indent=2)+'\n');argv=json.loads((root/(name+'.command.json')).read_text());new=out/name;argv[argv.index('--out')+1]=str(new);(out/(name+'.command.json')).write_text(json.dumps(argv,indent=2)+'\n')
 with(out/(name+'.stdout.log')).open('wb')as stdout,(out/(name+'.stderr.log')).open('wb')as stderr:r=subprocess.run(argv,stdout=stdout,stderr=stderr)
 assert r.returncode==0,(name,r.returncode);rows=json.loads((new/'summary.json').read_text())
 for row in rows:row['replaces_potential_overlap_summary']=str(old/'summary.json');row['cleanup_verification']=scope['cleanup_receipt']
 (new/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');replacement.append(str(new/'summary.json'));(H/'replacement-summaries.json').write_text(json.dumps(replacement,indent=2)+'\n');print(name,'PASS',flush=True)
print(out,flush=True)
