#!/usr/bin/env python3
"""Clone immutable historical littleX snapshots and export complete graph fixtures."""
import pathlib,json,time,hashlib,psycopg,sys
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
recipe=json.loads((H/'recipe.json').read_text());host='/tmp/jacpg-d6275e76eb';stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
with lease('littlex snapshot clone/export',H/('export-lease-'+stamp+'.json')):
 for tier,source in recipe['tiers'].items():
  dest=H/'fixtures'/tier;dest.mkdir(parents=True,exist_ok=True);receipt=dest/'export.json'
  if receipt.exists():continue
  db='jac_wb_lx_'+tier+'_20261020';admin=psycopg.connect(host=host,user='jac',dbname='postgres',autocommit=True)
  assert not admin.execute('SELECT 1 FROM pg_database WHERE datname=%s',(db,)).fetchone(),'Refuse preexisting clone'
  admin.execute(psycopg.sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(psycopg.sql.Identifier(db),psycopg.sql.Identifier(source['historical_snapshot'])));admin.close()
  c=psycopg.connect(host=host,user='jac',dbname=db);c.execute('SET TRANSACTION READ ONLY');meta={'source':source,'clone_database':db,'started_utc':stamp,'tables':{}}
  queries={'anchors':'SELECT id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,undirected,props::text,xmin::text,seq,src_type,dst_type FROM anchors ORDER BY id','graph_types':'SELECT type_name,ancestor FROM graph_types ORDER BY 1,2'}
  for t in ['identity_users','identity_lookups','kv_state']:
   if c.execute('SELECT to_regclass(%s)',(t,)).fetchone()[0]:queries[t]='SELECT * FROM '+t+' ORDER BY 1'
  for table,sql in queries.items():
   p=dest/(table+'.tsv');digest=hashlib.sha256();rows=0
   with c.cursor().copy('COPY ('+sql+') TO STDOUT WITH(FORMAT text)')as cp,p.open('wb')as f:
    for buf in cp:b=bytes(buf);f.write(b);digest.update(b);rows+=b.count(b'\n')
   cols=c.execute('SELECT column_name,data_type,udt_name FROM information_schema.columns WHERE table_schema=\'public\' AND table_name=%s ORDER BY ordinal_position',(table,)).fetchall();meta['tables'][table]={'path':str(p),'rows':rows,'bytes':p.stat().st_size,'sha256':digest.hexdigest(),'query':sql,'source_columns':cols}
  meta['types']=c.execute('SELECT kind,arch_type,count(*) FROM anchors GROUP BY 1,2 ORDER BY 1,2').fetchall();meta['root_orphans']=c.execute('SELECT count(*) FROM anchors a LEFT JOIN anchors r ON r.id=a.root_id WHERE a.root_id IS NOT NULL AND r.id IS NULL').fetchone()[0];meta['edge_orphans']=c.execute("SELECT count(*) FROM anchors e LEFT JOIN anchors s ON s.id=e.src LEFT JOIN anchors d ON d.id=e.dst WHERE e.kind='EdgeAnchor' AND(s.id IS NULL OR d.id IS NULL)").fetchone()[0];c.rollback();c.close();meta['ended_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());receipt.write_text(json.dumps(meta,indent=2)+'\n');print(tier,meta['tables']['anchors'],flush=True)
