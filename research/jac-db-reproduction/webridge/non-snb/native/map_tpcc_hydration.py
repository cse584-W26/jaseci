"""Associate actual generic-load parameter UUIDs with frozen graph node types."""
import pathlib,json,re,collections
R=pathlib.Path(__file__).resolve().parent;rows=json.loads((R/'tpcc-census/SQL-map.json').read_text());pattern=r'[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}';wanted=set()
for row in rows:
 for e in row['events']:
  if e['category']=='hydrate.generic_anchor':wanted.update(re.findall(pattern,e['parameter_log']or''))
types={}
with(R/'tpcc-fixture/anchors.tsv').open()as f:
 for line in f:
  identifier=line[:36]
  if identifier in wanted:
   fields=line.split('\t',3);types[identifier]={'kind':fields[1],'type':fields[2]}
  if len(types)==len(wanted):break
out=[]
for row in rows:
 loads=[]
 for e in row['events']:
  if e['category']!='hydrate.generic_anchor':continue
  ids=re.findall(pattern,e['parameter_log']or'');loads.append({'SQL_ordinal':e['ordinal'],'UUIDs':ids,'requested_UUID_count':len(ids),'node_types':dict(collections.Counter(types.get(x,{'type':'MissingAnchor'})['type']for x in ids))})
 out.append({'label':row['label'],'iteration':row['iteration'],'cold':row['cold'],'loads':loads})
(R/'tpcc-census/hydration-map.json').write_text(json.dumps({'method':'Actual server-log parameter UUIDs joined to frozen complete initial anchor export. Missing UUIDs remain explicit.','UUID_types':types,'requests':out},indent=2));print('Mapped',len(types),'initial anchors;',len(wanted)-len(types),'missing UUIDs')
