import json
from pathlib import Path
import psycopg
H=Path(__file__).resolve().parent
with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname='jac_snb_bench_pg_fbdb3a2c',options='-c default_transaction_read_only=on',autocommit=True) as c:
 queries={
 'database':"SELECT datname,pg_encoding_to_char(encoding) encoding,datcollate,datctype FROM pg_database WHERE datname=current_database()",
 'tables':"SELECT c.oid::regclass::text name,c.relkind,c.relpersistence FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY c.relname",
 'columns':"SELECT table_name,column_name,data_type,udt_name,ordinal_position,column_default,is_nullable FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position",
 'indexes':"SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname",
 'constraints':"SELECT conrelid::regclass::text tablename,conname,contype,pg_get_constraintdef(oid,true) definition FROM pg_constraint WHERE connamespace='public'::regnamespace ORDER BY conrelid,conname",
 'triggers':"SELECT tgrelid::regclass::text tablename,tgname,pg_get_triggerdef(oid,true) definition FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN(SELECT oid FROM pg_class WHERE relnamespace='public'::regnamespace) ORDER BY tgrelid,tgname",
 'functions':"SELECT p.oid::regprocedure::text name,pg_get_functiondef(p.oid) definition FROM pg_proc p WHERE pronamespace='public'::regnamespace AND prokind IN('f','p') ORDER BY p.oid::regprocedure::text",
 'database_overrides':"SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=current_database())",
 'settings':"SELECT name,setting,unit,source FROM pg_settings WHERE name IN ('fsync','synchronous_commit','log_statement','log_min_duration_statement','shared_buffers','work_mem','effective_cache_size','max_connections') ORDER BY name"}
 c.row_factory=psycopg.rows.dict_row
 result={key:c.execute(sql).fetchall() for key,sql in queries.items()}
 (H/'source-catalog.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
 print('tables',[(x['name'],x['relkind']) for x in result['tables']]);print('functions',len(result['functions']),'triggers',len(result['triggers']))
