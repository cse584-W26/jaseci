"""Export fresh W1 generic graph for the Java/WeBridge counterparts."""
import pathlib,json,hashlib,time,sys,shutil
import psycopg
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent));from measurement_lease import lease
with lease('native TPC-C initial graph export',R/'tpcc-export-lease.json'):
 assert(R/'tpcc-seed-complete.json').exists()
 assert shutil.disk_usage(R).free>15*1024**3,'Reserve15GiB free space'
 out=R/'tpcc-fixture';out.mkdir(exist_ok=False);receipt={'database':'jac_non_snb_tpcc_seed_20261020','snapshot':'jac_non_snb_tpcc_initial_20261020','tables':{},'wall_ns':time.time_ns()}
 with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname=receipt['database'])as c:
  c.execute('SET TRANSACTION READ ONLY')
  queries={'anchors':'SELECT id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,undirected,props::text,xmin::text,seq,src_type,dst_type FROM anchors ORDER BY id','graph_types':'SELECT type_name,ancestor FROM graph_types ORDER BY 1,2'}
  for t in ['identity_users','identity_lookups','kv_state']:
   if c.execute('SELECT to_regclass(%s)',(t,)).fetchone()[0]:queries[t]='SELECT * FROM '+t+' ORDER BY 1'
  for table,q in queries.items():
   p=out/(table+'.tsv');h=hashlib.sha256();n=0
   with c.cursor().copy('COPY ('+q+') TO STDOUT WITH(FORMAT text)')as cp,p.open('wb')as f:
    for b in cp:b=bytes(b);f.write(b);h.update(b);n+=b.count(b'\n')
   
   if table.startswith('identity_'):p.chmod(0o600)
   receipt['tables'][table]={'rows':n,'bytes':p.stat().st_size,'sha256':h.hexdigest(),'query':q,'columns':c.execute("SELECT column_name,data_type,udt_name FROM information_schema.columns WHERE table_schema='public'AND table_name=%s ORDER BY ordinal_position",(table,)).fetchall()}
  receipt['types']=c.execute('SELECT arch_type,count(*) FROM anchors GROUP BY 1 ORDER BY 1').fetchall()
 (out/'export.json').write_text(json.dumps(receipt,indent=2))
 print(json.dumps({'ready':True,'export':str(out),'anchors':receipt['tables']['anchors']}),flush=True)
