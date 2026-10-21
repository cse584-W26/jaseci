#!/usr/bin/env python3
"""Install MySQL equivalents of the canonical native projection-maintenance triggers.

The pristine copies are local reset inputs. Trigger bodies keep generic anchor writes
and the same typed read projections consistent throughout mixed workloads.
"""
import pathlib,json,sys,time,hashlib,subprocess
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
C='jac-webridge-mysql57'
def cli(s):
 r=subprocess.run(['docker','exec','-i',C,'mysql','--default-character-set=utf8mb4','-uroot','-N','-B'],input=s.encode(),capture_output=True);assert r.returncode==0,r.stderr.decode();return r.stdout.decode()
def body(receipt,verb):
 out=[]
 for table,v in receipt.items():
  typ='Profile'if'profile'in table else'Tweet';cols=[x[0]for x in v['columns']]
  if verb in ['UPDATE','DELETE']:out.append('DELETE FROM `'+table+'` WHERE id=OLD.id;')
  if verb=='DELETE':continue
  vals=[]
  for col in cols:
   if col in ['id','root_id']:q='NEW.'+col
   elif col=='acl_all':q="COALESCE(CAST(JSON_UNQUOTE(JSON_EXTRACT(NEW.props,'$.access.all')) AS SIGNED),-1)"
   elif col=='acl_spec':q="(COALESCE(JSON_LENGTH(JSON_EXTRACT(NEW.props,'$.access.roots.anchors')),0)>0)"
   elif col=='frag':q="JSON_SET(JSON_REMOVE(JSON_EXTRACT(NEW.props,'$.archetype'),'$.__type__','$.__module__'),'$._jac_type',NEW.arch_type,'$._jac_id',REPLACE(NEW.id,'-',''),'$._jac_archetype','node')"
   elif col=='src_endpoint':q="(SELECT src FROM anchors WHERE kind='EdgeAnchor' AND arch_type='Post' AND dst=NEW.id ORDER BY seq,id LIMIT 1)"
   elif col.startswith('f_'):q="CAST(JSON_EXTRACT(NEW.props,'$.archetype."+col[2:]+"') AS CHAR CHARACTER SET utf8mb4)"
   else:raise AssertionError((table,col))
   vals.append(q)
  out.append("IF NEW.kind='NodeAnchor' AND NEW.arch_type='"+typ+"' THEN INSERT INTO `"+table+'`('+','.join('`'+c+'`'for c in cols)+') VALUES('+','.join(vals)+'); END IF;')
  if'src_endpoint'in cols:
   out.append("IF NEW.kind='EdgeAnchor' AND NEW.arch_type='Post' THEN UPDATE `"+table+"` SET src_endpoint=NEW.src WHERE id=NEW.dst; END IF;")
 return '\n'.join(out)
with lease('littlex graph projection mutation adapters',H/('graph-writes-lease-'+str(time.time_ns())+'.json')):
 for tier in ['t20','t50','t100','t200']:
  d=H/'fixtures'/tier;r=json.loads((d/'mirrors/receipt.json').read_text());assert len(r)==2;db=json.loads((d/'mysql-load.json').read_text())['database'];assert not(d/'mirror-pristine.json').exists()
  sql='USE '+db+';\n'
  for t in r:sql+='CREATE TABLE `_pristine_'+t+'` LIKE `'+t+'`;INSERT INTO `_pristine_'+t+'` SELECT * FROM `'+t+'`;\n'
  # Native sequence values are retained. New-row sequence values are deterministic request inputs.
  sql+='DELIMITER //\n'
  for verb in ['INSERT','UPDATE','DELETE']:
   sql+='CREATE TRIGGER littlex_graph_'+verb.lower()+' AFTER '+verb+' ON anchors FOR EACH ROW BEGIN IF COALESCE(@wb_loading,0)=0 THEN\n'+body(r,verb)+'\nEND IF;END//\n'
  sql+='DELIMITER ;\n';p=d/'graph-write-adapters.sql';p.write_text(sql);output=cli(sql)
  (d/'mirror-pristine.json').write_text(json.dumps({'tables':list(r),'source_mirror_receipt_sha256':hashlib.sha256((d/'mirrors/receipt.json').read_bytes()).hexdigest(),'DDL_sha256':hashlib.sha256(sql.encode()).hexdigest(),'stdout':output,'scope':'canonical projected node relations maintained by generic-anchor mutations; initial rows copied before writes'},indent=2)+'\n');print(tier,'projection mutation adapters installed',flush=True)
