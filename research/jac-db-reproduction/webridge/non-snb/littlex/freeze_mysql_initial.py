#!/usr/bin/env python3
"""Freeze dedicated initial generic anchors before the first full graph mutation."""
import pathlib,json,subprocess,sys,time,argparse
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
p=argparse.ArgumentParser();p.add_argument('--lease-held',action='store_true');a=p.parse_args()
def cli(s):
 r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','-uroot','-N','-B'],input=s.encode(),capture_output=True);assert r.returncode==0,r.stderr.decode();return r.stdout.decode()
def freeze():
 for tier in ['t20','t50','t100','t200']:
  d=H/'fixtures'/tier;p=d/'pristine.json'
  if p.exists():continue
  db=json.loads((d/'mysql-load.json').read_text())['database'];verification=json.loads((d/'mysql-business-verification.json').read_text());assert verification['exact_field_equality'];sql='USE '+db+';CREATE TABLE _pristine_anchors LIKE anchors;INSERT INTO _pristine_anchors SELECT * FROM anchors;CREATE TABLE _pristine_graph_types LIKE graph_types;INSERT INTO _pristine_graph_types SELECT * FROM graph_types;';cli(sql)
  columns=['id','kind','arch_type','arch_module','fingerprint','root_id','src','dst','undirected','props','seq','src_type','dst_type'];diff=cli('USE '+db+';SELECT count(*) FROM anchors a LEFT JOIN _pristine_anchors p ON p.id=a.id WHERE p.id IS NULL OR NOT('+ ' AND '.join('(a.`'+x+'`<=>p.`'+x+'`)'for x in columns)+');SELECT count(*) FROM _pristine_anchors;').splitlines();assert diff==['0',str(verification['rows'])]
  p.write_text(json.dumps({'database':db,'initial_business_fields_sha256':verification['actual_sha256'],'rows':verification['rows'],'all13_fields_equal':True,'tables':['_pristine_anchors','_pristine_graph_types'],'snapshot_sql':sql,'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())},indent=2)+'\n');print(tier,'initialgraph frozen',flush=True)
if a.lease_held:freeze()
else:
 with lease('littlex initial MySQL graph freeze',H/('freeze-initial-lease-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'.json')):freeze()
