#!/usr/bin/env python3
"""Copy exact native projected node relations, preserving fields and declared source indexes."""
import pathlib,json,sys,time,hashlib,subprocess,psycopg
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
C='jac-webridge-mysql57'
def cli(s):
 p=subprocess.run(['docker','exec','-i',C,'mysql','--local-infile=1','--default-character-set=utf8mb4','-uroot','-N','-B'],input=s.encode(),capture_output=True);assert p.returncode==0,p.stderr.decode();return p.stdout.decode()
with lease('littlex native projected relations copy',H/('mirror-copy-lease-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'.json')):
 for tier in ['t20','t50','t100','t200']:
  d=H/'fixtures'/tier;db=json.loads((d/'mysql-load.json').read_text())['database'];pg=json.loads((d/'export.json').read_text())['clone_database'];out=d/'mirrors';out.mkdir(exist_ok=True);receipt={}
  with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname=pg)as c:
   c.execute('SET TRANSACTION READ ONLY');tables=[r[0]for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND(tablename LIKE 'g_n_profile_%'OR tablename LIKE 'g_n_tweet_%') ORDER BY 1").fetchall()]
   if not tables:
    subprocess.run([sys.executable,str(H/'warm_projected.py'),'--tier',tier,'--lease-held'],check=True)
    tables=[r[0]for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND(tablename LIKE 'g_n_profile_%'OR tablename LIKE 'g_n_tweet_%') ORDER BY 1").fetchall()]
    assert len(tables)==2,(tier,tables)
   for t in tables:
    cols=c.execute('SELECT column_name,udt_name FROM information_schema.columns WHERE table_schema=\'public\' AND table_name=%s ORDER BY ordinal_position',(t,)).fetchall();p=out/(t+'.tsv');sha=hashlib.sha256();rows=0
    with c.cursor().copy('COPY (SELECT * FROM '+t+' ORDER BY id) TO STDOUT WITH(FORMAT text)')as cp,p.open('wb')as f:
     for b in cp:z=bytes(b);f.write(z);sha.update(z);rows+=z.count(b'\n')
    names={col[0]for col in cols};parts=[];load=[];sets=[]
    for name,typ in cols:
     mt='CHAR(36) COLLATE utf8mb4_bin'if typ=='uuid'else'BIGINT'if typ in ['int4','int8','int2']else'TINYINT'if typ=='bool'else'VARCHAR(100)'if name=='f_created_at'else'LONGTEXT'
     parts.append('`'+name+'` '+mt+(' PRIMARY KEY'if name=='id'else''));load.append('@'+name if typ=='bool'else'`'+name+'`')
     if typ=='bool':sets.append('`'+name+"`=(@"+name+"='t')")
    for col in ['root_id','src_endpoint','f_created_at']:
     if col in names:parts.append('KEY `idx_'+col+'`(`'+col+'`)')
    ddl='CREATE TABLE `'+t+'`('+','.join(parts)+') CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;';cli('USE '+db+';'+ddl);tmp='/tmp/lx-'+tier+'-'+t+'.tsv';subprocess.run(['docker','cp',str(p),C+':'+tmp],check=True,capture_output=True)
    try:cli('USE '+db+";LOAD DATA LOCAL INFILE '"+tmp+"' INTO TABLE `"+t+'` CHARACTER SET utf8mb4 ('+','.join(load)+')'+(' SET '+','.join(sets)if sets else'')+';ANALYZE TABLE `'+t+'`;')
    finally:subprocess.run(['docker','exec',C,'rm','-f',tmp],check=True)
    sample=c.execute('SELECT row_to_json(t) FROM '+t+' t LIMIT 1').fetchone()[0];idx=c.execute('SELECT indexname,indexdef FROM pg_indexes WHERE schemaname=\'public\' AND tablename=%s ORDER BY indexname',(t,)).fetchall();(out/(t+'.sql')).write_text(ddl+'\n');receipt[t]={'columns':cols,'rows':rows,'sha256':sha.hexdigest(),'source_indexes':idx,'mysql_DDL':ddl,'sample':sample}
  (out/'receipt.json').write_text(json.dumps(receipt,indent=2,default=str)+'\n');print(tier,[(k,v['rows'])for k,v in receipt.items()],flush=True)
