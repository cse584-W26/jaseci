#!/usr/bin/env python3
"""Version the measured native owner-root identity branch before full Java captures."""
import pathlib,subprocess,json,sys,time,hashlib,os,signal
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
out=H/('owner-branch-alignment-'+str(time.time_ns()));out.mkdir();previous=json.loads((H/'final-build-snapshot.json').read_text());old=pathlib.Path(previous['path'])/'source/LittleXGraph.java';new=H/'LittleXGraph.java';proof=H.parent/'native/littlex-like-alignment.json';receipt={'previous_final_build':previous,'native_proof':str(proof),'native_proof_sha256':hashlib.sha256(proof.read_bytes()).hexdigest(),'old_graph_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'new_graph_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'change':'Full LIKE/follow owner-root hydration executes only when ownerRoot differs from actorRoot; native permission returns WRITE on identity before mem.get(ownerRoot).','supervisor_pid':3218460,'status':'queued'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
with lease('littlex proven owner-identity source branch build/freeze',out/'lease.json'):
 for label,script in [('build','build.py'),('freeze','freeze_build.py')]:
  r=subprocess.run([sys.executable,str(H/script)],capture_output=True);(out/(label+'.stdout')).write_bytes(r.stdout);(out/(label+'.stderr')).write_bytes(r.stderr);assert r.returncode==0,(label,r.stderr)
 snapshot=r.stdout.decode().strip().splitlines()[-1];(H/'final-build-snapshot.json').write_text(json.dumps({'path':snapshot,'batch':previous['batch'],'alignment_receipt':str(out/'receipt.json')},indent=2)+'\n');receipt.update(status='PASS source-aligned build frozen',final_snapshot=snapshot);(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
os.kill(3218460,signal.SIGCONT);receipt['supervisor_resumed']=True;(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(out)
