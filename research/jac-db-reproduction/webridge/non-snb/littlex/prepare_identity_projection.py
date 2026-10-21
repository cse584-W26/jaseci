#!/usr/bin/env python3
"""Prepare non-secret, cardinality-preserving guest-identity reads and freeze full Java."""
import pathlib,json,hashlib,subprocess,sys,time,os,signal,argparse
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
sys.path.insert(0,str(H.parent/'native'));from littlex_oracle import uncopy
p=argparse.ArgumentParser();p.add_argument('--supervisor-pid',type=int);a=p.parse_args();out=H/('identity-projection-'+str(time.time_ns()));out.mkdir();receipt={'scope':'All fixture identity rows projected to user_id/root_id/status; no credentials/profile/identity payload columns','connection_scope':'Native auxiliary identity PID reads while graph RO transaction is open; Java full issues equivalent immutable-projection reads on its single graph JDBC connection','order':'After first root ACL and before first projected traversal; both bind keys __guest__','tiers':{},'status':'queued'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mysql(db,q):
 r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot','-N','-B',db],input=q.encode(),capture_output=True);assert r.returncode==0,r.stderr;return r.stdout.decode()
def literal(v):return 'CONVERT(0x'+v.encode().hex()+' USING utf8mb4)'
ddl="CREATE TABLE identity_users_business(user_id VARCHAR(100) COLLATE utf8mb4_bin PRIMARY KEY,doc LONGTEXT CHARACTER SET utf8mb4 NOT NULL) ENGINE=InnoDB;\nCREATE TABLE identity_lookups_business(value_normalized VARCHAR(190) COLLATE utf8mb4_bin PRIMARY KEY,user_id VARCHAR(100) COLLATE utf8mb4_bin NOT NULL) ENGINE=InnoDB;\n"
with lease('littlex safe identity projections and source-aligned full build',out/'lease.json'):
 for tier in ['t20','t50','t100','t200']:
  f=H/'fixtures'/tier;users={}
  for line in(f/'identity_users.tsv').read_text().splitlines():
   key,raw=line.split('\t',1);d=json.loads(uncopy(raw));users[key]={'user_id':key,'root_id':d.get('root_id'),'status':d.get('status','active')}
  lookups=[]
  for line in(f/'identity_lookups.tsv').read_text().splitlines():
   fields=[uncopy(x)for x in line.split('\t')];assert len(fields)==2;key,uid=fields;assert uid in users and len(key)<=190;lookups.append([key,uid])
  assert len(users)==103 and len(lookups)==103
  rows={'users':[[key,users[key]]for key in sorted(users)],'lookups':sorted(lookups)};(f/'identity-business-projection.json').write_text(json.dumps(rows,indent=2)+'\n')
  load='DROP TABLE IF EXISTS identity_lookups_business;DROP TABLE IF EXISTS identity_users_business;\n'+ddl+'INSERT INTO identity_users_business VALUES '+','.join('('+literal(k)+','+literal(json.dumps(v,separators=(',',':')))+')'for k,v in rows['users'])+';\nINSERT INTO identity_lookups_business VALUES '+','.join('('+literal(k)+','+literal(v)+')'for k,v in rows['lookups'])+';\n'
  (f/'identity-business-projection.sql').write_text(load);db='jac_lx_'+tier+'_20261020';mysql(db,load);proof=mysql(db,"SELECT COUNT(*) FROM identity_users_business;SELECT COUNT(*) FROM identity_lookups_business;SELECT COUNT(*) FROM identity_users_business WHERE user_id='__guest__';SELECT COUNT(*) FROM identity_users_business t JOIN identity_lookups_business lk ON t.user_id=lk.user_id WHERE lk.value_normalized='__guest__' AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(t.doc,'$.status')),'active')<>'disabled';");assert proof.strip().splitlines()==['103','103','0','1'],proof
  for name in ['mysql-schema.sql','mysql-compiler-schema.sql']:
   path=f/name;text=path.read_text();marker='\n-- SAFE IDENTITY BUSINESS PROJECTION\n'
   if marker not in text:path.write_text(text+marker+ddl)
  receipt['tiers'][tier]={'users':103,'lookups':103,'guest_id_rows':0,'guest_normalized_rows':1,'public_projection':str(f/'identity-business-projection.json'),'public_sha256':sha(f/'identity-business-projection.json'),'ddl_load_sha256':sha(f/'identity-business-projection.sql'),'private_source_sha256':{name:sha(f/name)for name in ['identity_users.tsv','identity_lookups.tsv']}}
 for label,script in [('build','build.py'),('freeze','freeze_build.py')]:
  r=subprocess.run([sys.executable,str(H/script)],capture_output=True);(out/(label+'.stdout')).write_bytes(r.stdout);(out/(label+'.stderr')).write_bytes(r.stderr);assert r.returncode==0,(label,r.stderr)
 snapshot=r.stdout.decode().strip().splitlines()[-1];previous=json.loads((H/'final-build-snapshot.json').read_text());receipt.update(status='PASS',previous_build=previous,final_snapshot=snapshot);(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');(H/'final-build-snapshot.json').write_text(json.dumps({'path':snapshot,'batch':previous['batch'],'identity_projection_receipt':str(out/'receipt.json')},indent=2)+'\n')
if a.supervisor_pid:
 cmdline=pathlib.Path('/proc')/str(a.supervisor_pid)/'cmdline';assert cmdline.exists()and b'littlex/run_pipeline_batch.py'in cmdline.read_bytes();os.kill(a.supervisor_pid,signal.SIGCONT);receipt['supervisor_resumed']=True;(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(out)
