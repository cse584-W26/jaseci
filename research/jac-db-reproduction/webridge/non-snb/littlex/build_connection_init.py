import pathlib,sys,json,subprocess,shutil
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
pending=json.loads((H/'connection-init-fix-pending.json').read_text());out=pathlib.Path(pending['path'])
with lease('littleX measured four-byte connection initialization build',out/'build.lease.json'):
 for label in ['build','freeze_build']:
  r=subprocess.run([sys.executable,str(H/(label+'.py'))],capture_output=True);(out/(label+'.stdout.log')).write_bytes(r.stdout);(out/(label+'.stderr.log')).write_bytes(r.stderr);assert r.returncode==0,r.stderr
  if label=='freeze_build':snapshot=r.stdout.decode().strip().splitlines()[-1]
 (H/'final-build-snapshot.json').write_text(json.dumps({'path':snapshot,'connection_init_fix':str(out)},indent=2)+'\n');pending.update(build_snapshot=snapshot,unicode_roundtrip=str(H/'unicode-roundtrip/1792555295689936325/summary.json'),initialization_scope='Explicit SET NAMES before API/request timer, with actual SQL list and Questions recorded per connection');(out/'receipt.json').write_text(json.dumps(pending,indent=2)+'\n');print(snapshot,flush=True)
