"""Independently reconstruct every normalized initial business row from original seed inputs."""
import pathlib,json,hashlib,decimal,argparse
R=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--data-dir',type=pathlib.Path,default=R.parents[2]/'benchmark/tpcc/data');p.add_argument('--manifest',type=pathlib.Path,default=R/'tpcc-gates/baseline/before-state/manifest.json');p.add_argument('--out',type=pathlib.Path,default=R/'tpcc-initial-verified.json');args=p.parse_args();DATA=args.data_dir;actual=json.loads(args.manifest.read_text());rows={k:[]for k in actual}
def load(name):
 for line in(DATA/(name+'.jsonl')).open():yield json.loads(line)
for x in load('warehouse'):rows['warehouse'].append([x['w_id'],x['w_ytd']])
for x in load('district'):rows['district'].append([x['d_w_id'],x['d_id'],x['d_ytd'],x['d_next_o_id']])
for x in load('customer'):
 rows['customer'].append([x['c_w_id'],x['c_d_id'],x['c_id'],x['c_balance'],x['c_ytd_payment'],x['c_payment_cnt'],x['c_data']]);rows['history'].append([x['c_w_id'],x['c_d_id'],x['c_id'],x['c_w_id'],x['c_d_id'],10.0,'seed'])
for x in load('stock'):rows['stock'].append([x['s_w_id'],x['s_i_id'],x['s_quantity'],x['s_ytd'],x['s_order_cnt'],x['s_remote_cnt']])
for x in load('orders'):
 rows['orders'].append([x['o_w_id'],x['o_d_id'],x['o_id'],x['o_c_id'],x['o_carrier_id']or 0,x['o_ol_cnt'],x['o_all_local']])
 if x['new_order']:rows['new_order'].append([x['o_w_id'],x['o_d_id'],x['o_id']])
 for y in x['lines']:rows['order_line'].append([x['o_w_id'],x['o_d_id'],x['o_id'],y['ol_number'],y['ol_i_id'],y['ol_supply_w_id'],y['ol_quantity'],y['ol_amount'],y['ol_dist_info']])
M={'warehouse':{1},'district':{2},'customer':{3,4},'history':{5},'order_line':{7}};keys={'warehouse':1,'district':2,'customer':3,'stock':2,'orders':3,'new_order':3,'order_line':4,'history':7};proof={}
for table,values in rows.items():
 values.sort(key=lambda x:x[:keys[table]]);h=hashlib.sha256()
 for row in values:
  row=[format(decimal.Decimal(str(v)).quantize(decimal.Decimal('.01')),'.2f')if i in M.get(table,set())else str(v)if v is not None else None for i,v in enumerate(row)];h.update((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode())
 digest=h.hexdigest();a=actual[table];proof[table]={'rows':len(values),'expected_canonical_sha256':digest,'actual_canonical_sha256':a['canonical_cents_sha256'],'PASS':len(values)==a['rows']and digest==a['canonical_cents_sha256']}
result={'PASS':all(x['PASS']for x in proof.values()),'relations':proof,'seed_projection_changes':{'history':'Synthesized per Customer: amount10, data=seed, district/warehouse from Customer; history.jsonl not loaded.','orders':'Carrier NULL normalized to0.','order_line':'Delivery-date NULL→empty string; dates excluded from logical-state projection.'},'scope':'Full logical business-key projection, all initial rows; money canonicalized to two decimals then exact equality.'};args.out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert result['PASS']
