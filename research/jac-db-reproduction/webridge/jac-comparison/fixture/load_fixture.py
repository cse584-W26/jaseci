"""Clone source DDL/metadata read-only, load only the pinned MySQL anchor closure."""
import hashlib,json,time
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
H=Path(__file__).resolve().parent;W=H.parents[1];EXPORT=W/'alignment/graph-fixture';HOST='/tmp/jacpg-d6275e76eb';SOURCE='jac_snb_bench_pg_fbdb3a2c';TARGET='jac_webridge_matched_20261020'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
cat=json.loads((H/'source-catalog.json').read_text());original_manifest=json.loads((EXPORT/'manifest.json').read_text());assert sha(EXPORT/'anchors.tsv')==original_manifest['files']['anchors']['sha256']
receipt={'source_database':SOURCE,'target_database':TARGET,'source_read_only':True,'host':HOST,'user':'jac','load_start_unix':time.time(),'input_sha256':sha(EXPORT/'anchors.tsv'),'steps':[],'metadata_files':{}}
with psycopg.connect(host=HOST,user='jac',dbname=SOURCE,options='-c default_transaction_read_only=on',autocommit=True,row_factory=dict_row) as src,psycopg.connect(host=HOST,user='jac',dbname=TARGET,row_factory=dict_row) as dst:
 assert dst.execute("SELECT count(*) AS n FROM pg_tables WHERE schemaname='public'").fetchone()['n']==0,'Refuse to overwrite initialized fixture'
 column_rows=src.execute("SELECT c.relname AS table_name,a.attname AS name,format_type(a.atttypid,a.atttypmod) AS type,a.attnotnull AS not_null,pg_get_expr(d.adbin,d.adrelid) AS default_expr,a.attgenerated,a.attidentity FROM pg_class c JOIN pg_attribute a ON a.attrelid=c.oid LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum WHERE c.relnamespace='public'::regnamespace AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum").fetchall()
 sequences=src.execute("SELECT c.relname,s.seqtypid::regtype::text AS type,s.seqstart,s.seqincrement,s.seqmax,s.seqmin,s.seqcache,s.seqcycle FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid WHERE c.relnamespace='public'::regnamespace ORDER BY c.relname").fetchall();ddl=[]
 def run(statement):
  dst.execute(statement);ddl.append(statement)
 for x in sequences:
  run(f'CREATE SEQUENCE public."{x["relname"]}" AS {x["type"]} INCREMENT BY {x["seqincrement"]} MINVALUE {x["seqmin"]} MAXVALUE {x["seqmax"]} START WITH {x["seqstart"]} CACHE {x["seqcache"]} '+('CYCLE' if x['seqcycle'] else 'NO CYCLE'))
 tables=[x for x in cat['tables'] if x['relkind']=='r']
 for t in tables:
  columns=[]
  for x in column_rows:
   if x['table_name']!=t['name']:continue
   assert not x['attgenerated'] and not x['attidentity'],x
   columns.append('"'+x['name']+'" '+x['type']+(' DEFAULT '+x['default_expr'] if x['default_expr'] else '')+(' NOT NULL' if x['not_null'] else ''))
  run('CREATE '+('UNLOGGED ' if t['relpersistence']=='u' else '')+'TABLE public."'+t['name']+'" ('+', '.join(columns)+')')
 for x in cat['constraints']:
  if x['contype']=='n':continue
  run('ALTER TABLE public."'+x['tablename']+'" ADD CONSTRAINT "'+x['conname']+'" '+x['definition'])
 run('ALTER SEQUENCE public.anchors_seq_seq OWNED BY public.anchors.seq')
 for seq in sequences:
  state=src.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(seq['relname']))).fetchone();dst.execute('SELECT setval(%s::regclass,%s,%s)',(seq['relname'],state['last_value'],state['is_called']));receipt.setdefault('sequence_states',{})[seq['relname']]=state
 # Runtime state and authentication metadata are copied, while derived mirror rows are rebuilt locally.
 metadata=['graph_types','identity_users','identity_lookups','sso_lookups','jac_docs','kv_state','quarantine','jac_ep_violation']
 assert [x['key'] for x in src.execute('SELECT key FROM kv_state').fetchall()]==['schema_fingerprint'],'Audit new KV markers before copying'
 for table in metadata:
  path=H/(table+'.tsv');columns=[x['name'] for x in column_rows if x['table_name']==table]
  copy_sql=sql.SQL('COPY {} ({}) TO STDOUT WITH(FORMAT text)').format(sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,columns)))
  with src.cursor().copy(copy_sql) as cp,path.open('wb') as f:
   for chunk in cp:f.write(chunk)
  path.chmod(0o600)
  with dst.cursor().copy(sql.SQL('COPY {} ({}) FROM STDIN WITH(FORMAT text)').format(sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,columns)))) as cp,path.open('rb') as f:
   for chunk in iter(lambda:f.read(1024*1024),b''):cp.write(chunk)
  receipt['metadata_files'][table]={'sha256':sha(path),'bytes':path.stat().st_size,'rows':dst.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(sql.Identifier(table))).fetchone()['n']}
 # Export column11 is xmin, not format_version. Preserve it in the immutable input audit only.
 run('CREATE TEMP TABLE matched_stage(id uuid,kind text,arch_type text,arch_module text,fingerprint text,root_id uuid,src uuid,dst uuid,undirected bool,props jsonb,exported_xmin text,seq bigint,src_type text,dst_type text) ON COMMIT DROP')
 with dst.cursor().copy('COPY matched_stage FROM STDIN WITH(FORMAT text)') as cp,(EXPORT/'anchors.tsv').open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):cp.write(chunk)
 assert dst.execute('SELECT count(*) AS n FROM matched_stage').fetchone()['n']==460984
 business='id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,undirected,props,seq,src_type,dst_type'
 run('INSERT INTO public.anchors('+business+') SELECT '+business+' FROM matched_stage ORDER BY id')
 receipt['anchors_rows']=dst.execute('SELECT count(*) AS n FROM anchors').fetchone()['n'];receipt['edge_rows']=dst.execute("SELECT count(*) AS n FROM anchors WHERE kind='EdgeAnchor'").fetchone()['n'];assert receipt['anchors_rows']==460984 and receipt['edge_rows']==300901
 # COPY roundtrip proves all thirteen business fields agree, including ordering/seq/JSON representation.
 for name,query in [('expected-business','SELECT '+business+' FROM matched_stage ORDER BY id'),('actual-business','SELECT '+business+' FROM public.anchors ORDER BY id')]:
  digest=hashlib.sha256()
  with dst.cursor().copy('COPY ('+query+') TO STDOUT WITH(FORMAT text)') as cp:
   for chunk in cp:digest.update(chunk)
  receipt[name+'_sha256']=digest.hexdigest()
 assert receipt['expected-business_sha256']==receipt['actual-business_sha256']
 receipt['null_endpoint_violations']=dst.execute("SELECT count(*) AS n FROM anchors e LEFT JOIN anchors s ON s.id=e.src LEFT JOIN anchors d ON d.id=e.dst WHERE e.kind='EdgeAnchor' AND (s.id IS NULL OR d.id IS NULL)").fetchone()['n'];assert receipt['null_endpoint_violations']==0
 receipt['owner_root_violations']=dst.execute('SELECT count(*) AS n FROM anchors a LEFT JOIN anchors r ON r.id=a.root_id WHERE a.root_id IS NOT NULL AND r.id IS NULL').fetchone()['n'];assert receipt['owner_root_violations']==0
 constraint_indexes={x['conname'] for x in cat['constraints'] if x['contype'] in ('p','u')}
 for x in cat['indexes']:
  if x['indexname'] not in constraint_indexes:run(x['indexdef'])
 for x in cat['functions']:run(x['definition'])
 for x in cat['triggers']:run(x['definition'])
 for x in cat['database_overrides']:
  for setting in x['setconfig']:
   key,value=setting.split('=',1);dst.execute(sql.SQL('ALTER DATABASE {} SET {} TO {}').format(sql.Identifier(TARGET),sql.Identifier(key),sql.Literal(value)))
 receipt['derived_tables_pending_backfill']={x['name']:dst.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(sql.Identifier(x['name']))).fetchone()['n'] for x in tables if x['name'].startswith('g_n_') or x['name']=='adj_knows'}
 dst.commit()
 dst.autocommit=True
 dst.execute('ANALYZE')
 receipt['analyze_completed']=True
 (H/'schema.sql').write_text(';\n\n'.join(x.rstrip(';') for x in ddl if 'TEMP TABLE matched_stage' not in x and not x.startswith('INSERT INTO public.anchors'))+';\n')
 receipt['schema_sha256']=sha(H/'schema.sql');receipt['source_catalog_sha256']=sha(H/'source-catalog.json');receipt['load_finished_unix']=time.time();receipt['physical_xmin']='New PostgreSQL transaction IDs; original exported xmin preserved only in pinned anchors.tsv. Source business fields roundtrip exactly.';receipt['ready_for_runtime_backfill']=True
 (H/'load-receipt.json').write_text(json.dumps(receipt,indent=2,default=str)+'\n');print(json.dumps({k:receipt[k] for k in ['anchors_rows','edge_rows','null_endpoint_violations','owner_root_violations','ready_for_runtime_backfill']},indent=2))
