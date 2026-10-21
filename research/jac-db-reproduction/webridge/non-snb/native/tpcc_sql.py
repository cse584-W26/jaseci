"""Portable PostgreSQL duration parser and source-census TPC-C categories."""
import re

def sql_records(text,pids):
 out=[]
 for entry in re.split(r'(?=^\d{4}-\d\d-\d\d )',text,flags=re.M):
  m=re.search(r'\[(\d+)\] LOG:  duration: ([\d.]+) ms\s+(execute ([^:]+)|statement):\s*(.*)',entry,re.S)
  if m and int(m[1])in pids:out.append({'pid':int(m[1]),'execute_ms':float(m[2]),'statement':m[4],'sql':m[5].strip()})
 return out

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
