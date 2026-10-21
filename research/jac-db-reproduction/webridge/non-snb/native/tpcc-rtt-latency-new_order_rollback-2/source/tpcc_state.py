"""Logical-key snapshots matching TpccGate.state, outside measured requests."""
import pathlib,json,gzip,hashlib,decimal
import psycopg
Q={
'warehouse':"SELECT 1,(props->'archetype'->>'w_ytd')::numeric FROM anchors WHERE arch_type='Warehouse' ORDER BY 1",
'district':"SELECT 1,(props->'archetype'->>'d_id')::int,(props->'archetype'->>'d_ytd')::numeric,(props->'archetype'->>'d_next_o_id')::int FROM anchors WHERE arch_type='District' ORDER BY 1,2",
'customer':"SELECT 1,(d.props->'archetype'->>'d_id')::int,(c.props->'archetype'->>'c_id')::int,(c.props->'archetype'->>'c_balance')::numeric,(c.props->'archetype'->>'c_ytd_payment')::numeric,(c.props->'archetype'->>'c_payment_cnt')::int,c.props->'archetype'->>'c_data' FROM anchors c JOIN anchors e ON e.dst=c.id AND e.kind='EdgeAnchor'JOIN anchors d ON d.id=e.src AND d.arch_type='District'WHERE c.arch_type='Customer'ORDER BY 1,2,3",
'stock':"SELECT 1,(props->'archetype'->>'s_i_id')::int,(props->'archetype'->>'s_quantity')::int,(props->'archetype'->>'s_ytd')::int,(props->'archetype'->>'s_order_cnt')::int,(props->'archetype'->>'s_remote_cnt')::int FROM anchors WHERE arch_type='Stock' ORDER BY 1,2",
'orders':"SELECT 1,(props->'archetype'->>'o_d_id')::int,(props->'archetype'->>'o_id')::int,(props->'archetype'->>'o_c_id')::int,coalesce((props->'archetype'->>'o_carrier_id')::int,0),(props->'archetype'->>'o_ol_cnt')::int,(props->'archetype'->>'o_all_local')::int FROM anchors WHERE arch_type='Order' ORDER BY 1,2,3",
'new_order':"SELECT 1,(props->'archetype'->>'o_d_id')::int,(props->'archetype'->>'o_id')::int FROM anchors WHERE arch_type='Order'AND(props->'archetype'->>'new_order')::boolean ORDER BY 1,2,3",
'order_line':"SELECT 1,(o.props->'archetype'->>'o_d_id')::int,(o.props->'archetype'->>'o_id')::int,(l.props->'archetype'->>'ol_number')::int,(l.props->'archetype'->>'ol_i_id')::int,(l.props->'archetype'->>'ol_supply_w_id')::int,(l.props->'archetype'->>'ol_quantity')::int,(l.props->'archetype'->>'ol_amount')::numeric,l.props->'archetype'->>'ol_dist_info'FROM anchors l JOIN anchors e ON e.dst=l.id AND e.kind='EdgeAnchor'JOIN anchors o ON o.id=e.src AND o.arch_type='Order'WHERE l.arch_type='OrderLine'ORDER BY 1,2,3,4",
'history':"SELECT 1,(d.props->'archetype'->>'d_id')::int,(c.props->'archetype'->>'c_id')::int,(h.props->'archetype'->>'h_w_id')::int,(h.props->'archetype'->>'h_d_id')::int,(h.props->'archetype'->>'h_amount')::numeric,h.props->'archetype'->>'h_data'FROM anchors h JOIN anchors e ON e.dst=h.id AND e.kind='EdgeAnchor'JOIN anchors c ON c.id=e.src AND c.arch_type='Customer'JOIN anchors p ON p.dst=c.id AND p.kind='EdgeAnchor'JOIN anchors d ON d.id=p.src AND d.arch_type='District'WHERE h.arch_type='History'ORDER BY 1,2,3,4,5,6,7"}
def text(x):
 if x is None:return None
 if isinstance(x,decimal.Decimal):return format(x.normalize(),'f')if x else'0'
 return str(x)
MONEY={'warehouse':{1},'district':{2},'customer':{3,4},'order_line':{7},'history':{5}}
def snapshot(database,out):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False);manifest={}
 with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname=database)as c:
  c.execute('SET TRANSACTION READ ONLY')
  for name,q in Q.items():
   h=hashlib.sha256();ch=hashlib.sha256();n=0;p=out/(name+'.jsonl.gz');canonical=out/(name+'.canonical-cents.jsonl.gz')
   with c.cursor(name='snapshot_'+name)as cur,gzip.open(p,'wb')as f,gzip.open(canonical,'wb')as cf:
    cur.execute(q)
    for row in cur:
     values=[text(x)for x in row];line=(json.dumps(values,ensure_ascii=False,separators=(',',':'))+'\n').encode();f.write(line);h.update(line);n+=1
     for index in MONEY.get(name,set()):
      if values[index]is not None:values[index]=format(decimal.Decimal(values[index]).quantize(decimal.Decimal('.01')),'.2f')
     cline=(json.dumps(values,ensure_ascii=False,separators=(',',':'))+'\n').encode();cf.write(cline);ch.update(cline)
   manifest[name]={'rows':n,'sha256':h.hexdigest(),'path':str(p),'sql':q,'canonical_cents_path':str(canonical),'canonical_cents_sha256':ch.hexdigest(),'money_canonicalization':'Two decimal places, exact cents equality; raw values retained separately.'}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2));return manifest
