#!/usr/bin/env python3
"""Add an explicitly derived profile-row view; preserve original request JSONL."""
import pathlib,json,subprocess,sys,hashlib
D=pathlib.Path(__file__).resolve().parent;endpoint,out=sys.argv[1:];O=pathlib.Path(out);O.mkdir(parents=True,exist_ok=True)
a=json.loads((D/'java-command.json').read_text());a=[x.replace('{endpoint}',endpoint).replace('{profile_output}',out)for x in a];r=subprocess.run(a);assert r.returncode==0,r.returncode
source=O/'requests.jsonl';rows=[]
for line in source.read_text().splitlines():
 row=json.loads(line);row['iteration']=row['idx'];row['phase']='sp';rows.append(row)
target=O/'rows.jsonl';target.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n'for x in rows));(O/'rows-normalization.json').write_text(json.dumps({'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'derived':str(target),'derived_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'transformation':'Add iteration=idx and phase=sp; retain every original field including warmup; prefix0..5 remains warmup diagnostic, not latency samples'},indent=2))
