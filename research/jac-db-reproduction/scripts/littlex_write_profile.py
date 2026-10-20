"""Isolated write diagnostics using original littleX payloads and target plan.

Restore a fresh audited fixture before invoking this helper. The orchestrator
owns service startup, stage headers and PostgreSQL duration logging settings.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time

import httpx

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('littlex_read_profile_helpers',ROOT/'scripts/littlex_profile.py')
read=importlib.util.module_from_spec(spec);spec.loader.exec_module(read)
full=read.full
sys.path.insert(0,str(ROOT/'littlex/harness'))
import write_run
from oracle import load_tokens


def metric(values):
    return {'n':len(values),'mean':statistics.mean(values),'median':statistics.median(values),'sum':sum(values)} if values else {'n':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration-off',action='store_true',help='CPU/stage-only run without SQL protocol expectation')
    parser.add_argument('--pause',type=float,default=.05,help='Seconds between measured calls;0 for continuous controls')
    parser.add_argument('--tag',required=True)
    parser.add_argument('--base-url',default='http://127.0.0.1:18120')
    parser.add_argument('--tier',required=True,choices=['t20','t50','t100','t200'])
    parser.add_argument('--operation',default='create_tweet',choices=['create_tweet','follow','like'])
    parser.add_argument('--tokens-dir',required=True,type=Path)
    parser.add_argument('--app-dir',required=True,type=Path)
    parser.add_argument('--jac-bin',type=Path,default=ROOT/'runtime/bin/jac314-ad469')
    parser.add_argument('--seed',type=Path)
    parser.add_argument('--database')
    parser.add_argument('--socket',default='/tmp/jacpg-d6275e76eb')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pid',type=int);group.add_argument('--pid-file',type=Path)
    parser.add_argument('--warmups',type=int,default=100)
    parser.add_argument('--repeats',type=int,default=100)
    args=parser.parse_args()
    if args.warmups<100 or args.repeats<100:parser.error('Use at least100 warmups plus100 profiled writes for aggregate CPU resolution')
    output=ROOT/'results'/args.tag
    if output.exists():raise RuntimeError(f'Refusing to overwrite {output}')
    pid=args.pid or int(args.pid_file.read_text())
    app_identity=full.process_ticks(pid)
    seed_path=args.seed or ROOT/'littlex/dataset'/('uniform_seed.json' if args.tier=='t50' else f'{args.tier}_seed.json')
    seed=json.loads(seed_path.read_text())
    tokens=load_tokens('jaseci',args.tokens_dir)
    targets=write_run.load_targets('jaseci',args.tokens_dir)
    usernames=sorted(tokens)
    plan=write_run.TargetPlan(seed,targets,usernames)
    fetch,counter_key=write_run.OPS[args.operation]
    if args.operation=='follow' and plan.follow_capacity()<args.warmups+args.repeats:
        raise RuntimeError('Fresh fixture lacks enough distinct follow targets for requested warm+profile writes')
    os.environ.update(JAC_PG_ARM='1',JAC_CACHE_HOME=str(ROOT/'dbcache'),JAC_PG_VERSION='18',
                      JAC_PG_DIST='/home/baichuan/.cache/jac/pg/dist/linux-amd64-18.6.0',
                      JAC_PG_BIN=str(args.jac_bin),JAC_PG_APP_DIR=str(args.app_dir))
    os.environ.pop('JAC_DB_URL',None)
    def counts():return write_run.COUNTERS['jaseci']()
    output.mkdir(parents=True)
    captured={}
    def capture(response):
        captured.clear();captured.update({k:float(v) for k,v in response.headers.items() if k.startswith('x-stg-') or k.startswith('x-server-')})
    metadata={'tag':args.tag,'operation':args.operation,'tier':args.tier,'base_url':args.base_url,
              'pid':pid,'app_process_identity':app_identity,'app_dir':str(args.app_dir),'jac_bin':str(args.jac_bin),
              'warmups':args.warmups,'repeats':args.repeats,'seed':str(seed_path),
              'seed_sha256':hashlib.sha256(seed_path.read_bytes()).hexdigest(),
              'tokens_dir':str(args.tokens_dir),'tokens_sha256':hashlib.sha256((args.tokens_dir/'tokens.jaseci.json').read_bytes()).hexdigest(),
              'target_sha256':hashlib.sha256((args.tokens_dir/'targets.jaseci.json').read_bytes()).hexdigest(),
              'sequence':'Original write_run fixed warmup: sorted token usernames round-robin; warm i=-1-index; profile i=index. One TargetPlan persists across both phases. No RNG is used.',
              'payloads':'Original write_run.OPS functions, unchanged. create_tweet seed_id=w2_i, content=write bench tweet i #bench; negative warm indices keep warm/profile IDs distinct.',
              'oracle_method':'Original write_run.COUNTERS[jaseci] before warm, after warm, after profile; all outside measured SQL windows.',
              'measurement_role':'Diagnostic restored-fixture write run; excluded from formal latency metrics',
              'cpu_tick_resolution_ms':1000/os.sysconf('SC_CLK_TCK'),
              'interpretation':'Per-call CPU has10ms granularity; aggregate100+ calls. Protocol duration includes parse/bind/execute. COMMIT is separately reported without attributing its time to fsync. DB protocol wall and app/backend CPU are distinct measurements.'}
    before=counts();metadata['before_counts']=before
    warm_rows=[];rows=[]
    log=ROOT/'dbcache/pg/main/server.log';ticks=os.sysconf('SC_CLK_TCK')
    with httpx.Client(base_url=args.base_url,timeout=900,event_hooks={'response':[capture]}) as client,(output/'rows.jsonl').open('w') as incremental:
        for index in range(args.warmups):
            user=usernames[index%len(usernames)]
            started=time.perf_counter();_,server=fetch(client,'jaseci',tokens[user],user,-1-index,plan)
            warm_rows.append({'index':index,'payload_index':-1-index,'user':user,'client_ms':(time.perf_counter()-started)*1000,'server_ms':server})
            if 'x-stg-db-ms' not in captured:raise RuntimeError('JAC_STAGE_HEADERS=1 required on the running diagnostic app')
        after_warm=counts();metadata['after_warm_counts']=after_warm
        warm_delta={key:after_warm[key]-before[key] for key in before}
        metadata['warm_delta']=warm_delta
        (output/'warm.json').write_text(json.dumps(warm_rows,indent=2))
        (output/'metadata.json').write_text(json.dumps(metadata,indent=2))
        if warm_delta[counter_key]!=args.warmups or any(value for key,value in warm_delta.items() if key!=counter_key):
            raise RuntimeError(f'Warm write delta failed: {warm_delta}')
        info=read.backends_once(pid,args.socket,args.database);metadata['backend_discovery']=info
        known={entry['pid']:entry for entry in info['backends']}
        for index in range(args.repeats):
            user=usernames[index%len(usernames)]
            offset=log.stat().st_size
            db_before={bp:full.owned_backend_ticks(bp,info['postmaster_pid']) for bp in known}
            app_before=full.process_ticks(pid)
            wall=datetime.now(timezone.utc).isoformat();mono=time.monotonic();started=time.perf_counter()
            response,server=fetch(client,'jaseci',tokens[user],user,index,plan)
            client_ms=(time.perf_counter()-started)*1000;end_mono=time.monotonic()
            app_after=full.process_ticks(pid)
            db_after={bp:full.owned_backend_ticks(bp,info['postmaster_pid']) for bp in known}
            if app_after['start_ticks']!=app_identity['start_ticks'] or any(db_after[bp]['start_ticks']!=known[bp]['start_ticks'] for bp in known):raise RuntimeError('Sampled process identity changed')
            time.sleep(args.pause)
            with log.open('rb') as handle:handle.seek(offset);raw=handle.read()
            (output/f'postgres-{index:03d}.log').write_bytes(raw)
            events=full.parse_protocol(raw.decode('utf-8','replace'))
            protocol={phase:{'ms':sum(event['ms'] for event in events if event['phase']==phase),'count':sum(event['phase']==phase for event in events)} for phase in ['parse','bind','execute','statement']}
            commits=[event for event in events if event['sql_prefix'].strip().upper().rstrip(';')=='COMMIT']
            commit={phase:{'ms':sum(event['ms'] for event in commits if event['phase']==phase),'count':sum(event['phase']==phase for event in commits)} for phase in ['parse','bind','execute','statement']}
            app_cpu=1000*sum(app_after[key]-app_before[key] for key in ['user_ticks','system_ticks'])/ticks
            db_deltas=[{'pid':bp,'user_ticks':db_after[bp]['user_ticks']-db_before[bp]['user_ticks'],'system_ticks':db_after[bp]['system_ticks']-db_before[bp]['system_ticks']} for bp in known]
            db_cpu=1000*sum(item['user_ticks']+item['system_ticks'] for item in db_deltas)/ticks
            record={'repeat':index,'payload_index':index,'user':user,'start_wall_utc':wall,
                    'start_monotonic':mono,'end_monotonic':end_mono,'client_ms':client_ms,'server_ms':server,
                    'stage_headers':dict(captured),'application_process_cpu_ms':app_cpu,'database_backend_cpu_ms':db_cpu,
                    'database_backend_cpu_deltas':db_deltas,'protocol':protocol,'commit_protocol':commit,
                    'commit_protocol_ms':sum(value['ms'] for value in commit.values()),
                    'database_protocol_total_ms':sum(value['ms'] for value in protocol.values()),
                    'untracked_duration_pids':sorted({event['pid'] for event in events if event['pid'] is not None}-set(known)),
                    'log_start_offset':offset,'log_end_offset':offset+len(raw),
                    'response_sha256':hashlib.sha256(json.dumps(response,sort_keys=True).encode()).hexdigest(),
                    'protocol_events':events}
            rows.append(record);incremental.write(json.dumps(record)+'\n');incremental.flush()
            (output/'profile.json').write_text(json.dumps({'metadata':metadata,'rows':rows},indent=2))
            print(json.dumps({key:value for key,value in record.items() if key!='protocol_events'}),flush=True)
    after=counts();metadata['after_profile_counts']=after
    measured_delta={key:after[key]-metadata['after_warm_counts'][key] for key in after}
    total_delta={key:after[key]-before[key] for key in after}
    oracle_ok=(measured_delta[counter_key]==args.repeats and total_delta[counter_key]==args.warmups+args.repeats
               and all(value==0 for key,value in measured_delta.items() if key!=counter_key))
    summary={'metadata':metadata,'warm_delta':metadata['warm_delta'],'profile_delta':measured_delta,'total_delta':total_delta,
             'oracle_ok':oracle_ok,'n':len(rows),
             'metrics':{key:metric([row[key] for row in rows]) for key in ['client_ms','server_ms','application_process_cpu_ms','database_backend_cpu_ms','database_protocol_total_ms','commit_protocol_ms']},
             'stages':{phase:metric([row['stage_headers'][f'x-stg-{phase}-ms'] for row in rows if f'x-stg-{phase}-ms' in row['stage_headers']]) for phase in ['dispatch','auth','prep','db','build','commit','ser']},
             'protocol':{phase:metric([row['protocol'][phase]['ms'] for row in rows]) for phase in ['parse','bind','execute','statement']},
             'commit_protocol':{phase:metric([row['commit_protocol'][phase]['ms'] for row in rows]) for phase in ['parse','bind','execute','statement']}}
    (output/'metadata.json').write_text(json.dumps(metadata,indent=2));(output/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if oracle_ok and (args.duration_off or all(row['protocol_events'] for row in rows)) else 2


if __name__=='__main__':sys.exit(main())
