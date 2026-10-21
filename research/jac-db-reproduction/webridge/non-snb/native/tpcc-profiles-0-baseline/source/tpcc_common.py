"""Shared unchanged-driver input translation and business-state receipts."""
import pathlib,json,types
import psycopg
R=pathlib.Path(__file__).resolve().parent

def targets():
 d=R/'baseline/app/targets'
 return types.SimpleNamespace(tokens=json.loads((d/'tokens.json').read_text()),districts={int(k):v for k,v in json.loads((d/'warehouse.json').read_text())['districts'].items()},customers=json.loads((d/'customers.json').read_text()),items={int(k):v for k,v in json.loads((d/'items.json').read_text()).items()},stocks={int(k):v for k,v in json.loads((d/'stocks.json').read_text()).items()})

def state(database):
 with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname=database)as db:
  counts=dict(db.execute('SELECT arch_type,count(*) FROM anchors GROUP BY 1 ORDER BY 1').fetchall());sums={}
  for typ,fields in [('Warehouse',['w_ytd']),('District',['d_ytd','d_next_o_id']),('Customer',['c_balance','c_ytd_payment','c_payment_cnt']),('Stock',['s_quantity','s_ytd','s_order_cnt','s_remote_cnt']),('History',['h_amount']),('OrderLine',['ol_amount'])]:
   for field in fields:sums[typ+'.'+field]=str(db.execute("SELECT sum((props->'archetype'->>%s)::numeric)FROM anchors WHERE arch_type=%s",(field,typ)).fetchone()[0])
  consistency=db.execute("SELECT count(*) FROM anchors d WHERE d.arch_type='District'AND(d.props->'archetype'->>'d_next_o_id')::int-1<>(SELECT max((o.props->'archetype'->>'o_id')::int)FROM anchors o WHERE o.arch_type='Order'AND o.props->'archetype'->>'o_d_id'=d.props->'archetype'->>'d_id')").fetchone()[0]
  return {'counts':counts,'numeric_sums':sums,'district_order_consistency_bad':consistency}

def reset(database):
 assert database.startswith('jac_non_snb_tpcc_')and database!='jac_non_snb_tpcc_initial_20261020'
 with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname='postgres',autocommit=True)as admin:
  assert admin.execute('SELECT count(*)FROM pg_stat_activity WHERE datname=%s',(database,)).fetchone()[0]==0
  admin.execute(psycopg.sql.SQL('DROP DATABASE IF EXISTS {}').format(psycopg.sql.Identifier(database)))
  admin.execute(psycopg.sql.SQL('CREATE DATABASE {} TEMPLATE jac_non_snb_tpcc_initial_20261020').format(psycopg.sql.Identifier(database)))
