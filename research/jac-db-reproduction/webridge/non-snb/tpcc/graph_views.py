#!/usr/bin/env python3
"""Business-state oracle views over Jac anchors; never used inside timed requests."""
import pathlib,subprocess
H=pathlib.Path(__file__).resolve().parent
def field(alias,key,kind='int'):
 e="JSON_UNQUOTE(JSON_EXTRACT("+alias+".props,'$.archetype."+key+"'))"
 return e if kind=='text'else'CAST('+e+(' AS DECIMAL(20,2))'if kind=='money'else' AS SIGNED)')
def simple(view,typ,columns,extra=''):
 return 'CREATE OR REPLACE VIEW '+view+' AS SELECT '+','.join((expr+' AS '+name)for name,expr in columns.items())+" FROM anchors a "+extra+" WHERE a.arch_type='"+typ+"' AND a.kind='NodeAnchor';"
sql=[]
sql.append(simple('warehouse','Warehouse',{'w_id':field('a','w_id'),'w_ytd':field('a','w_ytd','money')}))
sql.append(simple('district','District',{'d_w_id':'1','d_id':field('a','d_id'),'d_ytd':field('a','d_ytd','money'),'d_next_o_id':field('a','d_next_o_id')}))
customer_parent="JOIN anchors e ON e.dst=a.id AND e.arch_type='GenericEdge' AND e.kind='EdgeAnchor' JOIN anchors d ON d.id=e.src AND d.arch_type='District'"
cols={'c_w_id':'1','c_d_id':field('d','d_id'),'c_id':field('a','c_id'),'c_balance':field('a','c_balance','money'),'c_ytd_payment':field('a','c_ytd_payment','money'),'c_payment_cnt':field('a','c_payment_cnt'),'c_data':field('a','c_data','text')};sql.append(simple('customer','Customer',cols,customer_parent))
cols={'s_w_id':'1',**{k:field('a',k)for k in ['s_i_id','s_quantity','s_ytd','s_order_cnt','s_remote_cnt']}};sql.append(simple('stock','Stock',cols))
cols={'o_w_id':'1',**{k:field('a',k)for k in ['o_d_id','o_id','o_c_id','o_carrier_id','o_ol_cnt','o_all_local']}};sql.append(simple('orders','Order',cols))
sql.append(simple('new_order','Order',{'no_w_id':'1','no_d_id':field('a','o_d_id'),'no_o_id':field('a','o_id')})[:-1]+" AND JSON_UNQUOTE(JSON_EXTRACT(a.props,'$.archetype.new_order'))='true';")
cols={'ol_w_id':'1','ol_d_id':field('p','o_d_id'),'ol_o_id':field('p','o_id'),**{k:field('a',k)for k in ['ol_number','ol_i_id','ol_supply_w_id','ol_quantity']},'ol_amount':field('a','ol_amount','money'),'ol_dist_info':field('a','ol_dist_info','text')}
sql.append(simple('order_line','OrderLine',cols,"JOIN anchors e ON e.dst=a.id AND e.kind='EdgeAnchor' AND e.arch_type='GenericEdge' JOIN anchors p ON p.id=e.src AND p.arch_type='Order'"))
cols={'h_c_w_id':'1','h_c_d_id':field('d','d_id'),'h_c_id':field('c','c_id'),'h_w_id':field('a','h_w_id'),'h_d_id':field('a','h_d_id'),'h_amount':field('a','h_amount','money'),'h_data':field('a','h_data','text')}
sql.append(simple('history','History',cols,"JOIN anchors e ON e.dst=a.id AND e.kind='EdgeAnchor' AND e.arch_type='GenericEdge' JOIN anchors c ON c.id=e.src AND c.arch_type='Customer' JOIN anchors ce ON ce.dst=c.id AND ce.kind='EdgeAnchor' AND ce.arch_type='GenericEdge' JOIN anchors d ON d.id=ce.src AND d.arch_type='District'"))
text='USE jac_tpcc_graph;\n'+'\n'.join(sql);(H/'graph-oracle-views.sql').write_text(text)
if __name__=='__main__':subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','-uroot'],input=text,text=True,check=True)
