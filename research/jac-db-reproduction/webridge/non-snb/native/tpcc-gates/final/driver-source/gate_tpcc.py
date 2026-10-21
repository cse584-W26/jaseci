"""Full original900-operation W1 plan, fresh state, unchanged native requests."""
import pathlib,json,sys,subprocess,time,os
import httpx
R=pathlib.Path(__file__).resolve().parent;REPRO=R.parents[2];sys.path[:0]=[str(R),str(R.parent),str(REPRO/'benchmark/scripts')]
from measurement_lease import lease
from tpcc_common import targets,state,reset
from tpcc_state import snapshot
import tpcc_run as T
class Recorder:
 def __init__(self,c):self.c=c
 def post(self,*args,**kw):self.response=self.c.post(*args,**kw);return self.response
variant=sys.argv[1];assert variant in ['baseline','final'];out=R/'tpcc-gates'/variant;out.mkdir(parents=True,exist_ok=False);DB='jac_non_snb_tpcc_work_20261020';cmd=[sys.executable,str(R/'service.py')];plan=json.loads((R.parent/'tpcc-plan-900.json').read_text());rows=[]
with lease('native TPC-C900 '+variant,out/'lease.json'):
 reset(DB);before=state(DB);snapshot(DB,out/'before-state')
 try:
  subprocess.run([*cmd,'start','--variant',variant,'--database',DB],check=True);jt=targets()
  with httpx.Client(base_url='http://127.0.0.1:18132',timeout=300)as c,(out/'rows.jsonl').open('w')as log:
   rc=Recorder(c)
   for idx,txn in enumerate(plan):
    wall=time.time_ns();start=time.monotonic_ns();ok,rollback,server_ms,result=T.one_txn(rc,'jaseci-pg',txn,{'Authorization':'Bearer '+jt.tokens['w1']},jt);row={'index':idx,'warmup':idx<100,'transaction':txn,'start_wall_ns':wall,'client_ms':(time.monotonic_ns()-start)/1e6,'server_ms':server_ms,'ok':ok,'rollback':rollback,'result':result,'headers':dict(rc.response.headers),'status':rc.response.status_code};rows.append(row);log.write(json.dumps(row)+'\n');log.flush();assert ok or(txn['kind']=='new_order'and txn['invalid']and rollback),(idx,result)
    if idx%50==0:print(variant,idx,flush=True)
 finally:subprocess.run([*cmd,'stop','--variant',variant],check=True)
 after=state(DB);snapshot(DB,out/'after-state');good=[x for x in rows if x['ok']];no=[x['transaction']for x in good if x['transaction']['kind']=='new_order'];pay=[x['transaction']for x in good if x['transaction']['kind']=='payment'];count=lambda typ:after['counts'].get(typ,0)-before['counts'].get(typ,0)
 checks={'all900':len(rows)==900,'new_order487':len(no)==487,'payment406':len(pay)==406,'rollback7':sum(x['rollback']for x in rows)==7,'orders':count('Order')==len(no),'lines':count('OrderLine')==sum(len(x['lines'])for x in no),'history':count('History')==len(pay),'district_consistency':after['district_order_consistency_bad']==0,'warehouse_payment_total':abs(float(after['numeric_sums']['Warehouse.w_ytd'])-float(before['numeric_sums']['Warehouse.w_ytd'])-sum(x['amount']for x in pay))<.01}
 (out/'summary.json').write_text(json.dumps({'variant':variant,'scope':'100 original mutating warm transactions +800 timed; no DB-delay proxy','before':before,'after':after,'checks':checks,'PASS':all(checks.values())},indent=2));assert all(checks.values()),checks
