"""Read historical W2 masters/logs and export an auditable comparison; no DB."""
import csv
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT.parent/'DBHarness'
OUT=ROOT/'write-investigation'


def read_csv(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))


def main():
    sources={arm:DB/f'session0904/run/data/{folder}/w2_master.csv' for arm,folder in [('postgres','littlex_baselines'),('jaseci-pg','littlex_control')]}
    records={}
    for arm,p in sources.items():
        for row in read_csv(p):
            if row['arm']!=arm:continue
            assert int(row['requests'])==500 and int(row['errors'])==0
            assert row['oracle_ok']=='True' and row['oracle_actual']==row['oracle_expected']=='610'
            records[(row['tier'],row['op'],arm)]=row
    comparison=[]
    for tier in ('t20','t50','t100','t200'):
        for op in ('like','follow','create_tweet'):
            pg,j=records[(tier,op,'postgres')],records[(tier,op,'jaseci-pg')]
            gap=(datetime.datetime.fromisoformat(j['ts'])-datetime.datetime.fromisoformat(pg['ts'])).total_seconds()
            comparison.append({'tier':tier,'operation':op,'pg_complete_utc':pg['ts'],'jac_complete_utc':j['ts'],'completion_gap_seconds':gap,'pg_server_p50_ms':float(pg['server_p50_ms']),'pg_server_p95_ms':float(pg['server_p95_ms']),'pg_server_p99_ms':float(pg['server_p99_ms']),'pg_client_p50_ms':float(pg['client_p50_ms']),'jac_server_p50_ms':float(j['server_p50_ms']),'jac_server_p95_ms':float(j['server_p95_ms']),'jac_server_p99_ms':float(j['server_p99_ms']),'jac_client_p50_ms':float(j['client_p50_ms']),'jac_over_pg_server_p50':float(j['server_p50_ms'])/float(pg['server_p50_ms']),'request_count':500,'warm_success_count_inferred_from_oracle':110,'oracle_delta_each_arm':610})
    cohorts=[]
    logs={'postgres':DB/'session0904/run/logs/littlex_baselines.log','jaseci-pg':DB/'session0904/run/data/littlex_control/.cell_W2_t20-t50-t100-t200.log'}
    for arm,p in logs.items():
        for line in p.read_text().splitlines():
            if f'phase=w2 reseed arm={arm}' not in line:continue
            name=line.split('seed=')[1];tier='t50' if name=='uniform_seed.json' else name.split('_')[0]
            cohort=[r for r in comparison if r['tier']==tier]
            cohorts.append({'arm':arm,'tier':tier,'reseed_started_log_time':line.split(' ')[0],'first_operation_completed_utc':cohort[0]['pg_complete_utc' if arm=='postgres' else 'jac_complete_utc'],'last_operation_completed_utc':cohort[-1]['pg_complete_utc' if arm=='postgres' else 'jac_complete_utc'],'timed_request_start_not_recorded':True})
    historical_app=subprocess.check_output(['git','-C',str(DB),'show','b94e08e^:littleXs/jaseci-pg/app.jac'])
    output={'masters':{k:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for k,p in sources.items()},'comparison':comparison,'cohort_windows':cohorts,'historical_jac_app_revision':'b94e08e^','historical_jac_app_sha256':hashlib.sha256(historical_app).hexdigest(),'pg_app_sha256':hashlib.sha256((DB/'littleXs/postgres/app.py').read_bytes()).hexdigest(),'raw_availability':'Tracked W2 master summaries and cohort logs available. Referenced original harness/.run/night unit files and per-request raw CSV not found in current clone. These summaries do not expose per-request commit/CPU/protocol events.'}
    (OUT/'historical-w2.json').write_text(json.dumps(output,indent=2)+'\n')
    with (OUT/'historical-w2.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(comparison[0]));w.writeheader();w.writerows(comparison)
    print('Historical W2 audit exported12 operation/tier pairs and8cohort bounds.')


if __name__=='__main__':main()
