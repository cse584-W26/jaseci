#!/usr/bin/env python3
"""Pinned original JSONL -> MySQL relational fixture, with reproducible reset."""
import argparse,ast,hashlib,json,pathlib,subprocess,time
H=pathlib.Path(__file__).resolve().parent;R=H.parents[2];DATA=R/'benchmark/tpcc/data'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sql(text):
 return subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--local-infile=1','-N','-B','-uroot'],input=text,text=True,capture_output=True,check=True).stdout
def columns():
 tree=ast.parse((R/'benchmark/tpcc/postgres/loader.py').read_text())
 node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name)and t.id=='COLS'for t in n.targets))
 return eval(compile(ast.Expression(node.value),'<original COLS>','eval'),{'range':range})
def encode(value):
 if value is None:return '\\N'
 return str(value).replace('\\','\\\\').replace('\t','\\t').replace('\n','\\n').replace('\r','\\r')
def prepare(out):
 out.mkdir(parents=True,exist_ok=False);cols=columns();handles={k:(out/(k+'.tsv')).open('w')for k in cols};counts={k:0 for k in cols};customer_since={}
 def emit(k,row):handles[k].write('\t'.join(encode(row.get(c))for c in cols[k])+'\n');counts[k]+=1
 try:
  for k in ['warehouse','district','customer','history','item','stock']:
   for line in (DATA/(k+'.jsonl')).open():
    row=json.loads(line)
    if k=='customer':customer_since[row['c_w_id'],row['c_d_id'],row['c_id']]=row['c_since']
    if k=='history':row={**row,'h_data':'seed','h_date':customer_since[row['h_c_w_id'],row['h_c_d_id'],row['h_c_id']]}
    emit(k,row)
  for line in (DATA/'orders.jsonl').open():
   row=json.loads(line);emit('orders',row)
   for ol in row['lines']:emit('order_line',{**ol,'ol_o_id':row['o_id'],'ol_d_id':row['o_d_id'],'ol_w_id':row['o_w_id']})
   if row['new_order']:emit('new_order',{'no_o_id':row['o_id'],'no_d_id':row['o_d_id'],'no_w_id':row['o_w_id']})
 finally:
  for f in handles.values():f.close()
 receipt={'seed_projection':'Jac HTTP import_data.jac initial History.h_data=seed and h_date=Customer.c_since; other source business fields unchanged','source':{p.name:sha(p)for p in DATA.glob('*.jsonl')},'columns':cols,'counts':counts,'tsv':{p.name:sha(p)for p in out.glob('*.tsv')},'schema_sha256':sha(H/'relational-schema.sql')};(out/'manifest.json').write_text(json.dumps(receipt,indent=2));return receipt
def load(out,db):
 assert db.startswith('jac_tpcc_') and db.replace('_','').isalnum();manifest=json.loads((out/'manifest.json').read_text());started=time.time_ns();container='/tmp/'+db
 subprocess.run(['docker','exec','jac-webridge-mysql57','mkdir','-p',container],check=True)
 for table in manifest['columns']:
  p=out/(table+'.tsv');assert sha(p)==manifest['tsv'][p.name];subprocess.run(['docker','cp',str(p),'jac-webridge-mysql57:'+container+'/'+p.name],check=True,capture_output=True)
 schema=(H/'relational-schema.sql').read_text();assert sha(H/'relational-schema.sql')==manifest['schema_sha256']
 sql('DROP DATABASE IF EXISTS '+db+';CREATE DATABASE '+db+' CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;USE '+db+';SET FOREIGN_KEY_CHECKS=0;'+schema)
 commands=['USE '+db+';SET FOREIGN_KEY_CHECKS=0;']
 for table,cols in manifest['columns'].items():commands.append("LOAD DATA LOCAL INFILE '"+container+'/'+table+".tsv' INTO TABLE "+table+" CHARACTER SET utf8mb4 FIELDS TERMINATED BY '\\t' ESCAPED BY '\\\\' LINES TERMINATED BY '\\n'("+','.join(cols)+');')
 sql('\n'.join(commands));counts={table:int(sql('SELECT COUNT(*) FROM '+db+'.'+table).strip())for table in manifest['columns']};assert counts==manifest['counts'];receipt={'database':db,'start_wall_ns':started,'end_wall_ns':time.time_ns(),'counts':counts,'fixture_sha256':sha(out/'manifest.json')};(out/('load-'+str(receipt['end_wall_ns'])+'.json')).write_text(json.dumps(receipt,indent=2));return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','load']);p.add_argument('--out',type=pathlib.Path,default=H/'relational-fixture-jac-seed');p.add_argument('--database',default='jac_tpcc_conventional');a=p.parse_args()
 print(json.dumps(prepare(a.out)if a.action=='prepare'else load(a.out,a.database),indent=2))
