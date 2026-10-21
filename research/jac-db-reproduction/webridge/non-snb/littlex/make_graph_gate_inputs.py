#!/usr/bin/env python3
import pathlib,json,uuid
H=pathlib.Path(__file__).resolve().parent;roots=json.loads((H/'cached-identity-roots.json').read_text())['guest_root_id']
for tier in roots:
 profiles={};maxseq=0
 for line in(H/'fixtures'/tier/'anchors.tsv').open():
  r=line.rstrip('\n').split('\t');maxseq=max(maxseq,int(r[11]))
  if r[1]=='NodeAnchor'and r[2]=='Profile':profiles[r[0]]=r[5]
 x=json.loads((H/(tier+'-gate-inputs.json')).read_text())
 for i,r in enumerate(x):
  r['actor_root_id']=profiles[r['actor_id']];r['guest_root_id']=roots[tier];r['new_seq']=str(maxseq+2*i+2);r['new_edge_seq']=str(maxseq+2*i+1)
  if r['op']in ['follow','create_tweet']:r['new_edge_id']=str(uuid.uuid5(uuid.NAMESPACE_URL,'littlex/graphgate/'+tier+'/'+str(i)))
 (H/(tier+'-graph-gate-inputs.json')).write_text(json.dumps(x,indent=2)+'\n')
print('Four graph gate input catalogs prepared')
