#!/usr/bin/env python3
"""Use exact frozen warm-plan inputs for tier-specific genuine captures."""
import pathlib,json,hashlib
H=pathlib.Path(__file__).resolve().parent;rows=[]
for tier in ['t20','t50','t100','t200']:
 d=H/'inputs'if tier=='t20'else H/'inputs'/tier;d.mkdir(exist_ok=True)
 for op in ['feed','feed_page','like','follow','create_tweet']:
  name=tier+'-'+('W1-feed'if op in ['feed','feed_page']else'W2-'+op)+'-latency.json';plan=H/'plans'/name;x=json.loads(plan.read_text())[0]['input'];x['op']=op;p=d/(op+'.json');p.write_text(json.dumps(x,indent=2)+'\n');rows.append({'tier':tier,'operation':op,'source_plan':str(plan),'source_ordinal':0,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(H/'inputs/tier-representatives.json').write_text(json.dumps(rows,indent=2)+'\n');print('Tier representatives',len(rows))
