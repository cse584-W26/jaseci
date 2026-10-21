#!/usr/bin/env python3
"""Install every accepted generated API into the target schema before request timing."""
import argparse,pathlib,json,subprocess,hashlib,re,time,sys
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
p=argparse.ArgumentParser();p.add_argument('--tier',required=True,choices=['t20','t50','t100','t200']);p.add_argument('--bundle',required=True,type=pathlib.Path);p.add_argument('--out',required=True,type=pathlib.Path);p.add_argument('--lease-held',action='store_true');a=p.parse_args();db='jac_lx_'+a.tier+'_20261020';a.out=a.out.resolve();assert not a.out.exists(),'Preserve installation receipt';meta=json.loads((a.bundle/'metadata.json').read_text());sources=[pathlib.Path(r['copied_path'])for r in meta['generated_sources']if pathlib.Path(r['copied_path']).name=='graph-SP-function.sql'or re.fullmatch(r'graph-SP-.*_sp_.*\.sql',pathlib.Path(r['copied_path']).name)];assert sources
source_hashes={r['copied_path']:r['sha256']for r in meta['generated_sources']}
# Functions precede each API procedure set, exactly as in the accepted cold pipeline.
sources=sorted(sources,key=lambda f:(f.parent.name,0 if f.name=='graph-SP-function.sql'else 1,f.name));expected={};payload=[];inventory=[]
for f in sources:
 data=f.read_bytes();assert hashlib.sha256(data).hexdigest()==source_hashes[str(f)],('Generated SQL changed',f);text=data.decode();payload.append(data);inventory.append({'path':str(f),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
 for kind,name in re.findall(r'CREATE\s+(?:DEFINER\s*=\s*\S+\s+)?(PROCEDURE|FUNCTION)\s+`?([A-Za-z0-9_]+)`?',text,re.I):expected[name]=kind.upper()
assert expected,'No generated routine definitions'
def mysql(sql):
 r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-N','-B','-uroot',db],input=sql,capture_output=True);
 if r.returncode:
  a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps({'status':'failed installation','database':db,'sources':inventory,'returncode':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')},indent=2)+'\n');raise RuntimeError(r.stderr.decode(errors='replace'))
 return r.stdout.decode()
def run():
 start=time.time_ns();sql=b"SET SESSION sql_mode=CONCAT(@@session.sql_mode,IF(FIND_IN_SET('NO_UNSIGNED_SUBTRACTION',@@session.sql_mode),'',',NO_UNSIGNED_SUBTRACTION'));\n"+b'\n'.join(payload);output=mysql(sql)
 rows=[]
 for line in mysql(b"SELECT JSON_OBJECT('name',ROUTINE_NAME,'type',ROUTINE_TYPE,'definition_sha256',SHA2(ROUTINE_DEFINITION,256),'sql_mode',SQL_MODE) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE() ORDER BY ROUTINE_NAME;").split('\n'):
  if line.strip():rows.append(json.loads(line))
 actual={r['name']:r for r in rows};assert all(name in actual and actual[name]['type']==kind and actual[name]['definition_sha256'] for name,kind in expected.items()),('Missing or empty installed generated routine',expected,actual)
 assert all('NO_UNSIGNED_SUBTRACTION'in actual[name]['sql_mode'].split(',')for name in expected)
 receipt={'status':'PASS','database':db,'bundle':str(a.bundle.resolve()),'bundle_metadata_sha256':hashlib.sha256((a.bundle/'metadata.json').read_bytes()).hexdigest(),'scope':'Every generated accepted API installed into target schema outside request timer; generated SQL bodies unchanged','sources':inventory,'expected_routines':expected,'installed_routines':[actual[n]for n in sorted(expected)],'start_wall_ns':start,'end_wall_ns':time.time_ns(),'mysql_stdout':output};a.out.parent.mkdir(parents=True,exist_ok=True);a.out.open('x').write(json.dumps(receipt,indent=2)+'\n');print(a.out)
if a.lease_held:run()
else:
 with lease('littleX complete accepted bundle install '+a.tier,a.out.with_suffix('.lease.json')):run()
