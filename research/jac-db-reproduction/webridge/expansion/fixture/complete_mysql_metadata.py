#!/usr/bin/env python3
"""Add pinned original auth/schema metadata to an empty-metadata six-query fixture."""
import pathlib,subprocess,json
H=pathlib.Path(__file__).resolve().parent;source=H.parents[1]/'jac-comparison/fixture';container='jac-webridge-mysql57';db='jac_snb_six_20261020';receipt={}
for name in ['identity_users','kv_state']:
 check=subprocess.check_output(['docker','exec',container,'mysql','-uroot','-N','-B',db,'-e','SELECT count(*) FROM '+name],text=True).strip();assert check=='0',name+' already populated; refuse duplicate load'
 target='/tmp/snb-six-'+name+'.tsv';subprocess.run(['docker','cp',str(source/(name+'.tsv')),container+':'+target],check=True)
 try:
  subprocess.run(['docker','exec',container,'mysql','--local-infile=1','--default-character-set=utf8mb4','-uroot',db,'-e',"LOAD DATA LOCAL INFILE '"+target+"' INTO TABLE "+name+" CHARACTER SET utf8mb4"],check=True)
  receipt[name]=int(subprocess.check_output(['docker','exec',container,'mysql','-uroot','-N','-B',db,'-e','SELECT count(*) FROM '+name],text=True))
 finally:subprocess.run(['docker','exec',container,'rm','-f',target],check=True)
(H/'mysql-metadata-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
