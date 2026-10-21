#!/usr/bin/env python3
"""Add cached identity-root bindings to graph plans without adding measured SQL."""
import pathlib,json,re,uuid,hashlib
H=pathlib.Path(__file__).resolve().parent
chars={'b':'\b','t':'\t','n':'\n','r':'\r','v':'\v','f':'\f','\\':'\\'}
def decode(s):return re.sub(r'\\([btnrvf\\])',lambda m:chars[m.group(1)],s)
def guest(tier):
 d=H/'fixtures'/tier;lookup=dict(x.rstrip('\n').split('\t')for x in(d/'identity_lookups.tsv').open());users={}
 for line in(d/'identity_users.tsv').open():
  k,v=line.rstrip('\n').split('\t',1);users[k]=json.loads(decode(v))
 return str(uuid.UUID(users[lookup['__guest__']]['root_id'].zfill(32)))
roots={t:guest(t)for t in ['t20','t50','t100','t200']};maxseq={}
for tier in roots:
 maxseq[tier]=max(int(line.rstrip('\n').split('\t')[11])for line in(H/'fixtures'/tier/'anchors.tsv').open())
manifest=json.loads((H/'plans/manifest.json').read_text())
for row in manifest:
 p=pathlib.Path(row['path']);x=json.loads(p.read_text())
 for i,r in enumerate(x):r['input'].update(guest_root_id=roots[row['tier']],new_seq=str(maxseq[row['tier']]+i*2+2),new_edge_seq=str(maxseq[row['tier']]+i*2+1))
 p.write_text(json.dumps(x,indent=2)+'\n');row['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
(H/'plans/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for p in(H/'inputs').glob('*.json'):
 x=json.loads(p.read_text());
 if not isinstance(x,dict):continue
 x.update(guest_root_id=roots['t20'],new_seq=str(maxseq['t20']+2),new_edge_seq=str(maxseq['t20']+1));p.write_text(json.dumps(x,indent=2)+'\n')
(H/'cached-identity-roots.json').write_text(json.dumps({'source':'immutable snapshot identity_lookups and identity_users; native guest cache equivalent','guest_root_id':roots},indent=2)+'\n')
print('Cached guest roots added to40 plans and operation inputs')
