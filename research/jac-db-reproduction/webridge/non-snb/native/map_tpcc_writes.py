"""Decode actual parallel-array batch bindings into ordered entity-type writes."""
import pathlib,json,re,collections
R=pathlib.Path(__file__).resolve().parent;rows=json.loads((R/'tpcc-census/SQL-map.json').read_text());out=[]
def array(text,parameter):
 match=re.search(r'\$'+str(parameter)+r" = '([^']*)'",text);assert match,parameter
 value=match[1];assert value.startswith('{')and value.endswith('}');return value[1:-1].split(',')if value!='{}'else[]
for row in rows:
 batches=[]
 for e in row['events']:
  if e['category']!='write.anchor_batch_upsert':continue
  ids=array(e['parameter_log'],2);kinds=array(e['parameter_log'],3);types=array(e['parameter_log'],4);assert len(ids)==len(kinds)==len(types);batches.append({'SQL_ordinal':e['ordinal'],'rows':len(ids),'entity_types':dict(collections.Counter(types)),'ordered_UUIDs':ids,'ordered_kinds':kinds,'ordered_types':types})
 out.append({'label':row['label'],'iteration':row['iteration'],'transaction_rolled_back':row['label']=='new_order_rollback','batches':batches})
(R/'tpcc-census/write-map.json').write_text(json.dumps({'method':'Actual $2 UUID,$3 kind,$4 archetype parallel-array bindings of native INSERT...ON CONFLICT. Rolled-back writes are retained explicitly.','requests':out},indent=2));print('Mapped',sum(len(x['batches'])for x in out),'actual write batches')
