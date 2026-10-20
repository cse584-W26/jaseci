"""Profile an already-started SQL littleX service using its original writes.

Fixture restore/loader, token export, taskset launch, PROF_TIMERS and target-DB
protocol logging are owned by the diagnostic runner. No service is launched here.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

import httpx
import psycopg
from psycopg.conninfo import conninfo_to_dict,make_conninfo

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sql_diag_helpers',ROOT/'scripts/profile_ic5_full.py')
full=importlib.util.module_from_spec(spec);spec.loader.exec_module(full)
sys.path.insert(0,str(ROOT/'littlex/harness'))
import write_run
from oracle import load_tokens


def discover(dsn,container):
    details=json.loads(subprocess.check_output(['docker','inspect',container],text=True))[0]
    if details['Name']!='/jac-db-reproduction-pg16' or not details['State']['Running']:
        raise RuntimeError('Expected owned PG16 reproduction container')
    bindings=details['HostConfig']['PortBindings'].get('5432/tcp',[])
    if not any(binding['HostPort']=='55436' for binding in bindings):raise RuntimeError('Unexpected PG16 port binding')
    init=details['State']['Pid']
    cfg=conninfo_to_dict(dsn)
    with psycopg.connect(make_conninfo(dsn,dbname='postgres'),autocommit=True,application_name='littlex-sql-profile-discovery') as connection:
        backends=connection.execute("SELECT pid,application_name FROM pg_stat_activity WHERE datname=%s AND backend_type='client backend' ORDER BY pid",(cfg['dbname'],)).fetchall()
    top=subprocess.check_output(['docker','top',container,'-eo','pid'],text=True)
    namespace_map={}
    for line in top.splitlines()[1:]:
        host=int(line.strip())
        status=Path(f'/proc/{host}/status').read_text()
        match=re.search(r'^NSpid:\s+(.+)$',status,re.M)
        if match:namespace_map[int(match.group(1).split()[-1])]=host
    result=[]
    for backend,name in backends:
        if backend not in namespace_map:raise RuntimeError(f'Backend{backend} not mapped to owned container')
        host=namespace_map[backend]
        result.append({'namespace_pid':backend,'host_pid':host,'application_name':name,
                       **full.owned_backend_ticks(host,init)})
    if not result:raise RuntimeError('No warmed SQL client backends')
    return {'container':container,'image':details['Config']['Image'],'container_init_host_pid':init,
            'database':cfg['dbname'],'backends':result}


def metric(values):
    return {'n':len(values),'mean':statistics.mean(values),'median':statistics.median(values),'sum':sum(values)} if values else {'n':0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--duration-off',action='store_true',help='CPU/stage-only run without SQL protocol expectation')
    p.add_argument('--pause',type=float,default=.05,help='Seconds between measured calls;0 for continuous controls')
    p.add_argument('--tag',required=True);p.add_argument('--tier',required=True,choices=['t20','t50','t100','t200'])
    p.add_argument('--operation',default='create_tweet',choices=['create_tweet','follow','like'])
    p.add_argument('--base-url',default='http://127.0.0.1:18121')
    p.add_argument('--dsn',default='postgresql://postgres@127.0.0.1:55436/littlex_reproduction_sql')
    p.add_argument('--container',default='jac-db-reproduction-pg16')
    p.add_argument('--tokens-dir',required=True,type=Path);p.add_argument('--pid',required=True,type=int)
    p.add_argument('--seed',type=Path);p.add_argument('--warmups',type=int,default=100);p.add_argument('--repeats',type=int,default=100)
    a=p.parse_args()
    if a.warmups<100 or a.repeats<100:p.error('At least100 warm and100 profile writes required')
    cfg=conninfo_to_dict(a.dsn)
    if cfg.get('host')!='127.0.0.1' or cfg.get('port')!='55436' or cfg.get('dbname')!='littlex_reproduction_sql':raise RuntimeError('Use the dedicated littleX SQL database at127.0.0.1:55436')
    if set(os.sched_getaffinity(a.pid))!=set(range(6,14)):raise RuntimeError('SQL HTTP server must be launched with taskset CPUs6-13')
    identity=full.process_ticks(a.pid)
    out=ROOT/'results'/a.tag
    if out.exists():raise RuntimeError(f'Refusing to overwrite {out}')
    seed_path=a.seed or ROOT/'littlex/dataset'/('uniform_seed.json' if a.tier=='t50' else f'{a.tier}_seed.json')
    seed=json.loads(seed_path.read_text());tokens=load_tokens('postgres',a.tokens_dir)
    targets=write_run.load_targets('postgres',a.tokens_dir);users=sorted(tokens)
    plan=write_run.TargetPlan(seed,targets,users);fetch,key=write_run.OPS[a.operation]
    if a.operation=='follow' and plan.follow_capacity()<a.warmups+a.repeats:raise RuntimeError('Insufficient distinct follow targets')
    os.environ['DATABASE_URL']=a.dsn
    def counts():return write_run.COUNTERS['postgres']()
    captured={}
    def hook(response):
        captured.clear();captured.update({key:float(value) for key,value in response.headers.items() if key.startswith(('x-stg-','x-server-'))})
    out.mkdir(parents=True);before=counts();rows=[];warm=[];hz=os.sysconf('SC_CLK_TCK')
    metadata={'tag':a.tag,'tier':a.tier,'operation':a.operation,'pid':a.pid,'process_identity':identity,
              'app_affinity':sorted(os.sched_getaffinity(a.pid)),'warmups':a.warmups,'repeats':a.repeats,
              'database':cfg['dbname'],'seed':str(seed_path),'seed_sha256':hashlib.sha256(seed_path.read_bytes()).hexdigest(),
              'tokens_sha256':hashlib.sha256((a.tokens_dir/'tokens.postgres.json').read_bytes()).hexdigest(),
              'targets_sha256':hashlib.sha256((a.tokens_dir/'targets.postgres.json').read_bytes()).hexdigest(),
              'sequence':'Original write_run OPS/TargetPlan; sorted token usernames round-robin; warm i=-1-index then profile i=index; persistent target plan; no RNG',
              'role':'Isolated write diagnostic; not formal timing','cpu_tick_resolution_ms':1000/hz}
    with httpx.Client(base_url=a.base_url,timeout=900,event_hooks={'response':[hook]}) as client:
        for i in range(a.warmups):
            user=users[i%len(users)];_,server=fetch(client,'postgres',tokens[user],user,-1-i,plan)
            warm.append({'index':i,'user':user,'server_ms':server})
            if 'x-stg-db-ms' not in captured:raise RuntimeError('Start SQL service with PROF_TIMERS=1')
        mid=counts();warm_delta={k:mid[k]-before[k] for k in before}
        if warm_delta[key]!=a.warmups or any(value for k,value in warm_delta.items() if k!=key):raise RuntimeError(f'Warm delta failed:{warm_delta}')
        info=discover(a.dsn,a.container);metadata['backend_discovery']=info
        known={entry['host_pid']:entry for entry in info['backends']};namespace={entry['namespace_pid'] for entry in info['backends']}
        capture_start=datetime.now(timezone.utc).isoformat()
        with (out/'rows.jsonl').open('w') as incremental:
            for i in range(a.repeats):
                user=users[i%len(users)]
                db0={pid:full.owned_backend_ticks(pid,info['container_init_host_pid']) for pid in known};app0=full.process_ticks(a.pid)
                wall=time.time();mono=time.monotonic();start=time.perf_counter()
                response,server=fetch(client,'postgres',tokens[user],user,i,plan)
                client_ms=(time.perf_counter()-start)*1000
                app1=full.process_ticks(a.pid);db1={pid:full.owned_backend_ticks(pid,info['container_init_host_pid']) for pid in known}
                if app1['start_ticks']!=identity['start_ticks'] or any(db1[pid]['start_ticks']!=known[pid]['start_ticks'] for pid in known):raise RuntimeError('Sampled process changed')
                record={'repeat':i,'user':user,'start_unix':wall,'end_unix':time.time(),'start_monotonic':mono,
                        'client_ms':client_ms,'server_ms':server,'stage_headers':dict(captured),
                        'application_process_cpu_ms':1000*sum(app1[k]-app0[k] for k in ['user_ticks','system_ticks'])/hz,
                        'database_backend_cpu_ms':1000*sum(db1[pid][k]-db0[pid][k] for pid in known for k in ['user_ticks','system_ticks'])/hz,
                        'response_sha256':hashlib.sha256(json.dumps(response,sort_keys=True).encode()).hexdigest()}
                rows.append(record);incremental.write(json.dumps(record)+'\n');incremental.flush();time.sleep(a.pause)
        capture_end=datetime.now(timezone.utc).isoformat()
    # Counter query runs after the SQL-log capture endpoint; it is excluded.
    after=counts();profile_delta={k:after[k]-mid[k] for k in before};total_delta={k:after[k]-before[k] for k in before}
    raw=subprocess.check_output(['docker','logs','--timestamps','--since',capture_start,'--until',capture_end,a.container],stderr=subprocess.STDOUT)
    (out/'postgres-all.log').write_bytes(raw)
    lines=[]
    for line in raw.decode('utf-8','replace').splitlines():
        stamp=line.split(' ',1)[0]
        try:when=datetime.fromisoformat(re.sub(r'(\.\d{6})\d+(?=Z|[+-])',r'\1',stamp).replace('Z','+00:00')).timestamp()
        except ValueError:continue
        lines.append((when,line))
    for index,row in enumerate(rows):
        end=rows[index+1]['start_unix'] if index+1<len(rows) else datetime.fromisoformat(capture_end).timestamp()
        segment='\n'.join(line for when,line in lines if row['start_unix']<=when<end)+'\n'
        (out/f'postgres-{index:03d}.log').write_text(segment)
        events=full.parse_protocol(segment)
        scoped=[event for event in events if event['pid'] in namespace]
        row['untracked_duration_pids']=sorted({event['pid'] for event in events if event['pid'] is not None}-namespace)
        row['protocol']={phase:{'ms':sum(event['ms'] for event in scoped if event['phase']==phase),'count':sum(event['phase']==phase for event in scoped)} for phase in ['parse','bind','execute','statement']}
        commit=[event for event in scoped if event['sql_prefix'].strip().upper().rstrip(';')=='COMMIT']
        row['commit_protocol']={phase:{'ms':sum(event['ms'] for event in commit if event['phase']==phase),'count':sum(event['phase']==phase for event in commit)} for phase in ['parse','bind','execute','statement']}
        row['database_protocol_total_ms']=sum(value['ms'] for value in row['protocol'].values());row['commit_protocol_ms']=sum(value['ms'] for value in row['commit_protocol'].values());row['protocol_events']=scoped
    oracle=(warm_delta[key]==a.warmups and profile_delta[key]==a.repeats and total_delta[key]==a.warmups+a.repeats and all(value==0 for k,value in total_delta.items() if k!=key))
    summary={'metadata':metadata,'warm_delta':warm_delta,'profile_delta':profile_delta,'total_delta':total_delta,'oracle_ok':oracle,
             'metrics':{k:metric([row[k] for row in rows]) for k in ['client_ms','server_ms','application_process_cpu_ms','database_backend_cpu_ms','database_protocol_total_ms','commit_protocol_ms']},
             'protocol':{phase:metric([row['protocol'][phase]['ms'] for row in rows]) for phase in ['parse','bind','execute','statement']},
             'commit_protocol':{phase:metric([row['commit_protocol'][phase]['ms'] for row in rows]) for phase in ['parse','bind','execute','statement']},
             'stages':{phase:metric([row['stage_headers'][f'x-stg-{phase}-ms'] for row in rows if f'x-stg-{phase}-ms' in row['stage_headers']]) for phase in ['auth','db','build','commit']}}
    (out/'warm.json').write_text(json.dumps(warm,indent=2));(out/'profile.json').write_text(json.dumps({'metadata':metadata,'rows':rows},indent=2));(out/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if oracle and (a.duration_off or all(row['protocol_events'] for row in rows)) else 2


if __name__=='__main__':sys.exit(main())
