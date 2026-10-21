#!/usr/bin/env python3
"""Freeze source anchor templates and original public graph target maps, excluding tokens."""
import json,pathlib,uuid
H=pathlib.Path(__file__).resolve().parent;N=H.parent/'native';templates={};maximum=0
for line in (N/'tpcc-fixture/anchors.tsv').open():
 a=line.rstrip('\n').split('\t');maximum=max(maximum,int(a[11]))
 if a[2]not in templates:templates[a[2]]={'kind':a[1],'arch_type':a[2],'arch_module':a[3],'fingerprint':a[4],'props':json.loads(a[9].replace('\\\\','\\'))}
targets=N/'baseline/app/targets';maps={name:json.loads((targets/(name+'.json')).read_text())for name in ['warehouse','customers','items','stocks']}
root=templates['Warehouse']['props']['root'];lookup=dict(line.rstrip('\n').split('\t')for line in(N/'tpcc-fixture/identity_lookups.tsv').open());context={'root_id':root,'user_id':lookup['tpcc_w1'],'initial_max_seq':maximum,'templates':templates,'maps':maps};(H/'graph-context.json').write_text(json.dumps(context,indent=2));print(root,maximum,len(templates))
