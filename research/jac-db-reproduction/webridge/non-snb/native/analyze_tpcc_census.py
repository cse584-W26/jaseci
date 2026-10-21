"""Classify actual ordered native commands; retain exact SQL and parameter text."""
import pathlib,json,gzip,re,hashlib,collections
R=pathlib.Path(__file__).resolve().parent;D=R/'tpcc-census';rows=json.loads((D/'rows.json').read_text());out=[]
def category(sql):
 s=' '.join(sql.split());u=s.upper()
 if u.startswith('DEALLOCATE'):return 'driver.prepared_cache_cleanup'
 if u.startswith('SHOW SERVER_VERSION'):return 'driver.server_version'
 if u.startswith(('CREATE ','ALTER ','UPDATE ANCHORS E SET SRC_TYPE','UPDATE ANCHORS E SET DST_TYPE','SET LOCK_TIMEOUT')):return 'schema.ensure'
 if u.startswith(('BEGIN','COMMIT','ROLLBACK','SET LOCAL')):return 'transaction.'+u.split()[0].lower()
 if 'identity_'in s:return 'identity.lookup'
 if u.startswith('INSERT INTO ANCHORS'):return 'write.anchor_batch_upsert'
 if u.startswith('INSERT INTO GRAPH_TYPES'):return 'write.type_registry'
 if 'n1.g_customer_c_last'in s:return 'graph.Customer.by_lastname_promoted'
 if 'SELECT n1.id, e1.id'in s:return 'graph.Warehouse.hop'
 if 'SELECT a.id, a.kind'in s:return 'hydrate.generic_anchor'
 if 'graph_types'in s:return 'type_registry.lookup'
 if 'schema'in s or'kv_state'in s or'to_regclass'in s:return 'schema.guard'
 return 'unclassified'
for row in rows:
 p=D/row['label']/(str(row['iteration'])+'.sql.log.gz');text=gzip.open(p,'rt').read();blocks=re.split(r'(?=^\d{4}-\d\d-\d\d .*?\[\d+\] )',text,flags=re.M);events=[];pids={x[0]for same in rows if same['label']==row['label']for x in same['backend_pids']}
 for block_index,block in enumerate(blocks):
  m=re.search(r'\[(\d+)\] LOG:  duration: ([0-9.]+) ms  (execute [^:]+|statement): (.*)',block,re.S)
  if not m:continue
  pid=int(m[1]);assert pid in pids,(pid,pids);sql=re.split(r'^\d{4}-\d\d-\d\d .*?DETAIL:|^\d{4}-\d\d-\d\d .*?CONTEXT:',m[4],maxsplit=1,flags=re.M)[0].strip();events.append({'ordinal':len(events),'pid':pid,'duration_ms':float(m[2]),'protocol_phase':m[3],'SQL':sql,'parameter_log':blocks[block_index+1].strip()if block_index+1<len(blocks)and'detail:  parameters:'in blocks[block_index+1].lower()else None,'sha256':hashlib.sha256(sql.encode()).hexdigest(),'category':category(sql)})
 result={'label':row['label'],'iteration':row['iteration'],'cold':row['cold'],'actual_commands':len(events),'categories':dict(collections.Counter(x['category']for x in events)),'events':events};out.append(result)
(D/'SQL-map.json').write_text(json.dumps(out,indent=2));print(json.dumps([{'label':x['label'],'iteration':x['iteration'],'count':x['actual_commands'],'categories':x['categories']}for x in out],indent=2))
