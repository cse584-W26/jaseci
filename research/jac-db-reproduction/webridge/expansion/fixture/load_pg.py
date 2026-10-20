"""Rebuild the frozen fixture from saved DDL/metadata/anchor files, without source DB access."""
import argparse,hashlib,json
from pathlib import Path
import psycopg
from psycopg import sql
O=Path(__file__).resolve().parent;H=O.parents[1]/'jac-comparison/fixture';export=O/'data';r=json.loads((H/'load-receipt.json').read_text());a=argparse.ArgumentParser();a.add_argument('--target',required=True);args=a.parse_args()
assert args.target.startswith('jac_webridge_matched_') and args.target!='jac_snb_bench_pg_fbdb3a2c'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
assert digest(export/'anchors.tsv')==json.loads((O/'export-receipt.json').read_text())['anchors']['sha256'];assert digest(H/'schema.sql')==r['schema_sha256']
for table,x in r['metadata_files'].items():assert digest(H/(table+'.tsv'))==x['sha256']
with psycopg.connect(host=r['host'],user=r['user'],dbname='postgres',autocommit=True) as ctl:
 assert not ctl.execute('SELECT 1 FROM pg_database WHERE datname=%s',(args.target,)).fetchone(),'Refuse overwrite'
 ctl.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C'").format(sql.Identifier(args.target)))
with psycopg.connect(host=r['host'],user=r['user'],dbname=args.target) as c:
 c.execute((H/'schema.sql').read_text(),prepare=False)
 for table in r['metadata_files']:
  with c.cursor().copy(sql.SQL('COPY {} FROM STDIN').format(sql.Identifier(table))) as cp,(H/(table+'.tsv')).open('rb') as f:
   for b in iter(lambda:f.read(1024*1024),b''):cp.write(b)
 c.execute('ALTER TABLE anchors DISABLE TRIGGER USER')
 c.execute('CREATE TEMP TABLE matched_stage(id uuid,kind text,arch_type text,arch_module text,fingerprint text,root_id uuid,src uuid,dst uuid,undirected bool,props jsonb,exported_xmin text,seq bigint,src_type text,dst_type text) ON COMMIT DROP')
 with c.cursor().copy('COPY matched_stage FROM STDIN') as cp,(export/'anchors.tsv').open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):cp.write(b)
 fields='id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,undirected,props,seq,src_type,dst_type'
 c.execute('INSERT INTO anchors('+fields+') SELECT '+fields+' FROM matched_stage ORDER BY id');c.execute('ALTER TABLE anchors ENABLE TRIGGER USER')
 for name,x in r['sequence_states'].items():c.execute('SELECT setval(%s::regclass,%s,%s)',(name,x['last_value'],x['is_called']))
 assert c.execute('SELECT count(*),count(*) FILTER(WHERE kind=\'EdgeAnchor\') FROM anchors').fetchone()==(1475843,sum(x[2] for x in json.loads((O/'export-receipt.json').read_text())['types'] if x[0]=='EdgeAnchor'))
 receipt={'target':args.target,'anchors':1475843,'source_file_sha256':digest(export/'anchors.tsv'),'metadata_source':str(H),'source_unchanged':True};business='id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,undirected,props,seq,src_type,dst_type'
 for name,table in [('expected','matched_stage'),('actual','anchors')]:
  dh=hashlib.sha256()
  with c.cursor().copy('COPY (SELECT '+business+' FROM '+table+' ORDER BY id) TO STDOUT') as cp:
   for b in cp:dh.update(b)
  receipt[name+'_business_sha256']=dh.hexdigest()
 assert receipt['expected_business_sha256']==receipt['actual_business_sha256']
 receipt['missing_endpoints']=c.execute("SELECT count(*) FROM anchors e LEFT JOIN anchors s ON s.id=e.src LEFT JOIN anchors d ON d.id=e.dst WHERE e.kind='EdgeAnchor' AND(s.id IS NULL OR d.id IS NULL)").fetchone()[0];assert receipt['missing_endpoints']==0
 receipt['missing_roots']=c.execute('SELECT count(*) FROM anchors a LEFT JOIN anchors r ON r.id=a.root_id WHERE a.root_id IS NOT NULL AND r.id IS NULL').fetchone()[0];assert receipt['missing_roots']==0
 c.commit();c.autocommit=True;c.execute('ANALYZE');receipt['analyze']=True;(O/'pg-load-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('Ready for baseline, then canonical final-runtime mirror backfill:',args.target)
