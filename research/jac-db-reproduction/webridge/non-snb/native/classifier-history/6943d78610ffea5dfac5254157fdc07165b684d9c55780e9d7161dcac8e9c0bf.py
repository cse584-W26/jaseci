"""Source SQL categories plus explicitly observed PostgreSQL connection initialization."""
from littlex_sql import category as littlex_category
from tpcc_sql import category as tpcc_category

def category(sql,family='littlex'):
 s=' '.join(sql.lower().split())
 if s=='select 1':return'driver.healthcheck'
 if s.startswith('select distinct arch_type from anchors'):return'schema.ensure.edge_type_probe'
 if s.startswith('select 1 from anchors')and'undirected'in s:return'schema.ensure.undirected_probe'
 if s.startswith('select 1 from anchors')and'group by dst having count(*) > 1'in s:return'schema.ensure.destination_uniqueness_probe'
 if s.startswith('select distinct type_name from graph_types'):return'type_registry.lookup'
 if s.startswith(('create ','alter ','drop ')):return'schema.ensure'
 if s.startswith('show server_version'):return'driver.connection_init.server_version'
 if s.startswith('set lock_timeout'):return'schema.ensure.lock_timeout_setting'
 if s.startswith('show '):return'driver.connection_init.setting'
 if 'pg_catalog.'in s or'information_schema.'in s:return'schema.catalog'
 if s.startswith(('set datestyle','set client_encoding','set standard_conforming_strings','set intervalstyle')):return'driver.connection_init.setting'
 return littlex_category(sql)if family=='littlex'else tpcc_category(sql)
