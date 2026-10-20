"""Independent read-only checks of pinned slice, catalog reproduction and closure."""
import hashlib,json
from pathlib import Path
import psycopg
H=Path(__file__).resolve().parent;cat=json.loads((H/'source-catalog.json').read_text());load=json.loads((H/'load-receipt.json').read_text());out={'checks':{},'scope':'Read-only target verification; original DB not connected or mutated'}
with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname='jac_webridge_matched_20261020',options='-c default_transaction_read_only=on',autocommit=True) as c:
 out['anchors']=c.execute('SELECT count(*),count(*) FILTER(WHERE kind=\'EdgeAnchor\'),min(seq),max(seq) FROM anchors').fetchone();out['checks']['exact_anchor_edge_counts']=out['anchors'][:2]==(460984,300901)
 indexes={x[0]:x[1] for x in c.execute("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public'").fetchall()};out['checks']['source_indexes_preserved']=all(indexes.get(x['indexname'])==x['indexdef'] for x in cat['indexes'])
 triggers={x[0]:x[1] for x in c.execute("SELECT tgname,pg_get_triggerdef(oid,true) FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN(SELECT oid FROM pg_class WHERE relnamespace='public'::regnamespace)").fetchall()};out['checks']['source_triggers_preserved']=all(triggers.get(x['tgname'])==x['definition'] for x in cat['triggers'])
 funcs={x[0]:x[1] for x in c.execute("SELECT p.oid::regprocedure::text,pg_get_functiondef(p.oid) FROM pg_proc p WHERE pronamespace='public'::regnamespace AND prokind IN('f','p')").fetchall()};out['checks']['source_functions_preserved']=all(funcs.get(x['name'])==x['definition'] for x in cat['functions'])
 columns=c.execute("SELECT table_name,column_name,data_type,udt_name,ordinal_position,column_default,is_nullable FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position").fetchall();expected=[tuple(x[k] for k in ['table_name','column_name','data_type','udt_name','ordinal_position','column_default','is_nullable']) for x in cat['columns']];out['checks']['source_column_definitions_preserved']=set(expected).issubset(set(columns))
 out['checks']['expected_and_actual_business_sha_equal']=load['expected-business_sha256']==load['actual-business_sha256']
 out['checks']['endpoint_and_root_closure']=load['null_endpoint_violations']==load['owner_root_violations']==0
 out['metadata_counts']={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in load['metadata_files']};out['checks']['metadata_counts_preserved']=all(out['metadata_counts'][t]==x['rows'] for t,x in load['metadata_files'].items())
 out['derived_table_counts']={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in load['derived_tables_pending_backfill']}
 out['index_count']=len(indexes);out['trigger_count']=len(triggers);out['function_count']=len(funcs)
out['passed']=all(out['checks'].values());(H/'independent-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));raise SystemExit(int(not out['passed']))
