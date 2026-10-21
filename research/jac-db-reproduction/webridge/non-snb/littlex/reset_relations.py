#!/usr/bin/env python3
"""Restore only dedicated conventional littleX relations from immutable loaded anchors."""
import pathlib,json,subprocess,sys,time,argparse,hashlib
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
p=argparse.ArgumentParser();p.add_argument('tier',choices=['t20','t50','t100','t200']);p.add_argument('--lease-held',action='store_true');p.add_argument('--bundle',type=pathlib.Path);p.add_argument('--install-receipt',type=pathlib.Path);a=p.parse_args();d=H/'fixtures'/a.tier;db=json.loads((d/'mysql-load.json').read_text())['database'];assert db=='jac_lx_'+a.tier+'_20261020';text=(d/'mysql-schema.sql').read_text();mirror=text[text.index('CREATE TABLE lx_profiles'):].split('-- SAFE IDENTITY BUSINESS PROJECTION',1)[0];pristine=d/'pristine.json';restore="SET @wb_loading=1;TRUNCATE anchors;INSERT INTO anchors SELECT * FROM _pristine_anchors;TRUNCATE graph_types;INSERT INTO graph_types SELECT * FROM _pristine_graph_types;"if pristine.exists()else''
mirror_snapshot=d/'mirror-pristine.json'
if mirror_snapshot.exists():
 for name in json.loads(mirror_snapshot.read_text())['tables']:restore+='TRUNCATE `'+name+'`;INSERT INTO `'+name+'` SELECT * FROM `_pristine_'+name+'`;'
sql='USE '+db+';'+restore+'DROP TABLE lx_follows,lx_tweets,lx_profiles;'+mirror+'SET @wb_loading=0;'
out=H/'resets'/a.tier/(time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+str(time.time_ns())+'.json');out.parent.mkdir(parents=True,exist_ok=True)
def run():
 assert not out.exists(),'Preserve prior reset receipt'
 r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot'],input=sql.encode(),capture_output=True);out.open('x').write(json.dumps({'database':db,'scope':'restore pristine generic graph and projections when frozen, then conventional relations','pristine_receipt':str(pristine)if pristine.exists()else None,'initial_business_fields_sha256':json.loads((d/'mysql-business-verification.json').read_text())['actual_sha256'],'sql_sha256':hashlib.sha256(sql.encode()).hexdigest(),'returncode':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode()},indent=2));assert r.returncode==0,r.stderr
 if a.bundle:
  receipt=a.install_receipt or out.with_name(out.stem+'-bundle-install.json');subprocess.run([sys.executable,str(H/'install_bundle.py'),'--tier',a.tier,'--bundle',str(a.bundle),'--out',str(receipt),'--lease-held'],check=True)
if a.lease_held:run()
else:
 with lease('littlex conventional relations reset '+a.tier,out.with_suffix('.lease.json')):run()
