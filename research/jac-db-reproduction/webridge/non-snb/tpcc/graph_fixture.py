#!/usr/bin/env python3
"""Exact native anchor fixture and bounded, write-set-based fresh-state resets."""
import argparse,hashlib,json,pathlib,subprocess,time
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];F=H.parent/'native/tpcc-fixture';BASE='jac_tpcc_graph_initial';WORK='jac_tpcc_graph'
def sql(q):
 r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--local-infile=1','--default-character-set=utf8mb4','-uroot','-N','-B'],input=q,text=True,capture_output=True,check=True);return r.stdout
def load():
 export=json.loads((F/'export.json').read_text());assert sql("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='"+BASE+"'").strip()=='0'
 schema=(B/'alignment/schema.sql').read_text().replace('jac_alignment',BASE).replace('CHARACTER SET ascii COLLATE ascii_bin','CHARACTER SET utf8mb4 COLLATE utf8mb4_bin').replace('CHARACTER SET ascii','CHARACTER SET utf8mb4 COLLATE utf8mb4_bin');schema+="\nUSE "+BASE+";CREATE TABLE identity_lookups(value_normalized VARCHAR(200) COLLATE utf8mb4_bin PRIMARY KEY,user_id VARCHAR(200) COLLATE utf8mb4_bin NOT NULL,KEY(user_id));\n";(H/'graph-schema.sql').write_text(schema);(H/'graph-compiler-schema.sql').write_text(schema.replace('kind VARCHAR(32)', 'c_last VARCHAR(100),kind VARCHAR(32)'));sql(schema)
 started=time.time_ns()
 for name in ['anchors','graph_types','identity_users','identity_lookups','kv_state']:
  source=F/(name+'.tsv');assert hashlib.sha256(source.read_bytes()).hexdigest()==export['tables'][name]['sha256'];destination='/tmp/tpcc-graph-'+name+'.tsv';subprocess.run(['docker','cp',str(source),'jac-webridge-mysql57:'+destination],capture_output=True,check=True)
  columns="(id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,@undirected,props,row_version,seq,src_type,dst_type) SET undirected=(@undirected='t')"if name=='anchors'else''
  sql("USE "+BASE+";LOAD DATA LOCAL INFILE '"+destination+"' INTO TABLE "+name+" CHARACTER SET utf8mb4 "+columns+';');subprocess.run(['docker','exec','jac-webridge-mysql57','rm','-f',destination],check=True)
 checks=sql('USE '+BASE+";SELECT COUNT(*),SUM(NOT JSON_VALID(props)) FROM anchors;SELECT COUNT(*)FROM anchors e LEFT JOIN anchors s ON s.id=e.src LEFT JOIN anchors d ON d.id=e.dst WHERE e.kind='EdgeAnchor'AND(s.id IS NULL OR d.id IS NULL);")
 assert checks.splitlines()==[str(export['tables']['anchors']['rows'])+'\t0','0'],checks
 sql('CREATE DATABASE '+WORK+' CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;'+''.join('CREATE TABLE '+WORK+'.'+name+' LIKE '+BASE+'.'+name+';INSERT INTO '+WORK+'.'+name+' SELECT * FROM '+BASE+'.'+name+';'for name in ['anchors','graph_types','identity_users','identity_lookups','kv_state']))
 # The source's promoted Customer.c_last predicate is represented by the same indexed scalar.
 for db in [BASE,WORK]:sql("ALTER TABLE "+db+".anchors ADD COLUMN c_last VARCHAR(100) GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.c_last'))) STORED,ADD KEY customer_last(arch_type,c_last)")
 (H/'graph-load.json').write_text(json.dumps({'initial_database':BASE,'working_database':WORK,'start_wall_ns':started,'end_wall_ns':time.time_ns(),'checks':checks,'export':export},indent=2))
def reset(receipt):
 started=time.time_ns();before=sql("SELECT COUNT(*)FROM "+WORK+".anchors WHERE row_version='java-dirty'");maxseq=int(sql('SELECT MAX(seq)FROM '+BASE+'.anchors').strip())
 fields=['kind','arch_type','arch_module','fingerprint','root_id','src','dst','undirected','props','row_version','src_type','dst_type']
 sql('UPDATE '+WORK+'.anchors a JOIN '+BASE+'.anchors b ON a.id=b.id SET '+','.join('a.'+f+'=b.'+f for f in fields)+" WHERE a.row_version='java-dirty';DELETE FROM "+WORK+'.anchors WHERE seq>'+str(maxseq)+';')
 checks=sql("SELECT COUNT(*),SUM(row_version='java-dirty'),SUM(seq>"+str(maxseq)+')FROM '+WORK+'.anchors');assert checks.strip()=='1281535\t0\t0',checks
 receipt.parent.mkdir(parents=True,exist_ok=True);assert not receipt.exists();receipt.write_text(json.dumps({'start_wall_ns':started,'end_wall_ns':time.time_ns(),'initial_database':BASE,'working_database':WORK,'dirty_rows_before':before,'after':checks,'method':'Restore marked existing write set from immutable initial rows; remove all postinitial sequence rows; no business SQL added to requests'},indent=2))
def verify_reset(receipt):
 """One-time full ordered digest proof of all source business columns after reset."""
 columns=['id','kind','arch_type','arch_module','fingerprint','root_id','src','dst','undirected','props','seq','src_type','dst_type'];proof={'columns':columns,'row_version':'Engine-specific MVCC marker excluded; reset independently checks no dirty markers','databases':{}};started=time.time_ns()
 for db in [BASE,WORK]:
  query='SELECT SHA2(JSON_ARRAY('+','.join(columns)+'),256)FROM '+db+'.anchors ORDER BY id'
  child=subprocess.Popen(['docker','exec','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot','-N','-B','--quick','-e',query],stdout=subprocess.PIPE,stderr=subprocess.PIPE);digest=hashlib.sha256();rows=0
  for line in child.stdout:digest.update(line);rows+=1
  error=child.stderr.read();assert child.wait()==0,error
  proof['databases'][db]={'rows':rows,'ordered_row_sha256_digest':digest.hexdigest()}
 assert proof['databases'][BASE]==proof['databases'][WORK],proof
 proof.update(status='PASS',start_wall_ns=started,end_wall_ns=time.time_ns(),method='SHA256 of ordered per-row SHA256(JSON_ARRAY(all13businessfields)); exact source initial and reset working rows')
 assert not receipt.exists();receipt.parent.mkdir(parents=True,exist_ok=True);receipt.write_text(json.dumps(proof,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['load','reset','verify-reset']);p.add_argument('--receipt',type=pathlib.Path);a=p.parse_args()
 if a.action=='load':
  load();subprocess.run(['python',str(H/'prepare_graph_context.py')],check=True);subprocess.run(['python',str(H/'graph_views.py')],check=True)
 elif a.action=='reset':reset(a.receipt)
 else:verify_reset(a.receipt)
