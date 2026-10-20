"""Historical 100 warm + 800 timed plan, original requests, plus DB-truth checks.

Only transport endpoints and oracle database connections are parameterized.
Raw CSV timing includes rollbacks, exactly as original bench_timed.run_tpcc.
"""
import argparse,ast,hashlib,inspect,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'benchmark/scripts'))
import tpcc_run as T
import bench_timed as B
import psycopg
p=argparse.ArgumentParser();p.add_argument('--arm',required=True,choices=['postgres','sqlalchemy','jaseci-pg']);p.add_argument('--base-url',required=True);p.add_argument('--dsn',required=True);p.add_argument('--out-dir',required=True,type=Path);p.add_argument('--txns',type=int,default=800);a=p.parse_args()
# Preserve original oracle query text while changing only the connection.
if a.arm in ('postgres','sqlalchemy'):
 source=inspect.getsource(T.counts_pg).replace('"postgresql://postgres@localhost:5433/tpcc"',repr(a.dsn))
 ns={};exec(source,ns);counts=ns['counts_pg']
else:
 tree=ast.parse(inspect.getsource(T.counts_jaseci_pg))
 query=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='q' for t in n.targets))
 def counts():
  with psycopg.connect(a.dsn) as c:return c.execute(query).fetchone()[0]
T.ARMS[a.arm]=a.base_url;B.TPCC_ARMS[a.arm]=a.base_url;B.COUNTS[a.arm]=counts
plan=T.build_plan(100+a.txns);before=counts();observed=[];original=B.one_txn

def one_txn(*args,**kw):
 result=original(*args,**kw);observed.append((args[2],result[0],result[1]));return result
B.one_txn=one_txn
a.dry_run=False
try:B.run_tpcc(a)
finally:
 after=counts();ok_no=[t for t,ok,rb in observed if ok and t['kind']=='new_order'];ok_pay=[t for t,ok,rb in observed if ok and t['kind']=='payment']
 delta={k:after[k]-before[k] for k in ('orders','order_line','new_order','history','next_o_sum')}
 ytd=round(after['w_ytd']-before['w_ytd'],2);expected_ytd=round(sum(t['amount'] for t in plan if t['kind']=='payment'),2)
 checks={'orders':delta['orders']==len(ok_no),'order_line':delta['order_line']==sum(len(t['lines']) for t in ok_no),'new_order_rows':delta['new_order']==len(ok_no),'history':delta['history']==len(ok_pay),'next_o_sum':delta['next_o_sum']==len(ok_no),'w_ytd':abs(ytd-expected_ytd)<0.01,'consistency':after['consistency_bad']==0}
 result={'arm':a.arm,'warmup':100,'timed':a.txns,'plan_seed':T.PLAN_SEED,'plan_sha256':hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest(),'before':before,'after':after,'deltas':delta,'w_ytd_delta':ytd,'w_ytd_expected':expected_ytd,'ok_new_order':len(ok_no),'ok_payment':len(ok_pay),'rolled_back':sum(rb for t,ok,rb in observed),'oracle':checks,'oracle_all_ok':all(checks.values())}
 a.out_dir.mkdir(parents=True,exist_ok=True);(a.out_dir/f'tpcc_{a.arm}.oracle.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
if not all(checks.values()):sys.exit(2)
