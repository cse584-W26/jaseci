"""Independent offline validation of completed IC5/SNB/TPC-C evidence."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'benchmark/scripts'))
from tpcc_run import build_plan


def load(rel):return json.loads((ROOT/rel).read_text())
def csv_read(rel):
    with (ROOT/rel).open(newline='') as f:return list(csv.DictReader(f))


def main():
    result={'mode':'offline artifacts only','ic5':{},'snb':{},'tpcc':{}}
    for variant,total,n in [('baseline',278769,40),('final',432,60)]:
        c=load(f'results/{variant}-census/summary.json');rows=load(f'results/{variant}-census/rows.json');lat=load(f'results/{variant}-latency/rows.json');ls=load(f'results/{variant}-latency/summary.json')
        assert len(rows)==20 and {r['idx'] for r in rows}==set(range(20))
        assert all(r['query']=='ic5' and r['parity'] and not r['jac_error'] and not r['pg_error'] and r['structural_sql']==0 for r in rows)
        assert sum(r['stmts'] for r in rows)==c['queries']['ic5']['total_statements']==total
        ir=[r for r in lat if r['query']=='ic5'];assert len(ir)==n and all(r['parity'] for r in ir)
        assert ls['failed_including_warm']==c['failed_including_warm']==0
        result['ic5'][variant]={'census_requests':20,'sql_total':total,'structural_sql':0,'latency_requests':n,'parity':True,'app_sha256':c['app_sha256']}
    assert result['ic5']['baseline']['app_sha256']==result['ic5']['final']['app_sha256']
    historical=load('../DBHarness/session0904/run/data/snb/postgres/snb_postgres.hashes.json')
    schedule={'is1':750,'is2':750,'is3':750,'ic1':75,'ic2':75,'ic5':75,'ic13':75}
    for name,arm in [('jac','jaseci-pg'),('postgres','postgres'),('sqlalchemy','sqlalchemy'),('neo4j','neo4j')]:
        prefix=f'results/snb-canonical/{name}' if name=='jac' else f'results/locked/snb-canonical/{name}'
        base=prefix+'/snb_'+arm;meta=load(base+'.meta.json');hashes=load(base+'.hashes.json');warm=csv_read(base+'.warm.csv');timed=csv_read(base+'.csv')
        assert not meta['errors'] and len(warm)==140 and len(timed)==2550
        assert len(hashes)==140 and set(hashes)==set(historical) and hashes==historical
        for q,count in schedule.items():
            w=[r for r in warm if r['query']==q];t=[r for r in timed if r['query']==q]
            assert len(w)==20 and {int(r['param_idx']) for r in w}==set(range(20))
            assert len(t)==count and {int(r['param_idx']) for r in t}==set(range(20))
            assert all(r['arm']==arm and r['client_ms'] and r['server_ms'] for r in w+t)
        result['snb'][name]={'base':base,'warm':140,'timed':2550,'historical_hash_matches':140,'errors':0}
    plan=build_plan(900);planhash=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest();expected={'orders':30487,'order_line':305500,'new_order':9487,'history':30406,'next_o_sum':30497,'consistency_bad':0}
    for directory,arm in [('results/tpcc-jac','jaseci-pg'),('results/locked/tpcc-postgres','postgres'),('results/locked/tpcc-sqlalchemy','sqlalchemy')]:
        base=directory+'/tpcc_'+arm;oracle=load(base+'.oracle.json');meta=load(base+'.meta.json');warm=csv_read(base+'.warm.csv');timed=csv_read(base+'.csv')
        assert len(warm)==100 and len(timed)==800 and not meta['errors']
        assert all(oracle['oracle'].values()) and oracle['oracle_all_ok'] and oracle['plan_sha256']==planhash
        assert all(oracle['after'][k]==v for k,v in expected.items()) and abs(oracle['after']['w_ytd']-1362049.86)<.01
        assert oracle['ok_new_order']==487 and oracle['ok_payment']==406 and oracle['rolled_back']==7
        assert [int(r['param_idx']) for r in warm+timed]==list(range(900))
        assert all(r['query']==t['kind'] and r['arm']==arm for r,t in zip(warm+timed,plan))
        result['tpcc'][arm]={'base':base,'warm':100,'timed':800,'plan_sha256':planhash,'all_seven_oracles':True,'final_counts':oracle['after'],'errors':0}
    progress=load('results/locked-stage-progress.json');assert progress[-1]['stage']=='locked-tpcc-stop-sqlalchemy' and all(r['exit']==0 for r in progress)
    result['all_checks_passed']=True
    (ROOT/'results/core-artifact-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Offline core validation PASS: IC5 two revisions; SNB four arms140warm/2550timed/140hashes; TPC-C three arms900plan/seven oracles.')


if __name__=='__main__':main()
