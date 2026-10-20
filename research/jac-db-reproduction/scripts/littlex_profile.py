"""Profile read requests against an already-running audited littleX service.

The orchestrator owns fixture restore, JAC_STAGE_HEADERS and SQL logging.
This helper launches/stops no service and changes no database settings.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import statistics
import sys
import time

import httpx
import psycopg

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ic5_full_helpers',ROOT/'scripts/profile_ic5_full.py')
full=importlib.util.module_from_spec(spec);spec.loader.exec_module(full)
sys.path.insert(0,str(ROOT/'littlex/harness'))
import run as harness_run
from oracle import load_tokens,expected_feeds,expected_pages,order_violations


def backends_once(pid,socket,database):
    cluster=ROOT/'dbcache/pg/main'
    tokens=shlex.split((cluster/'postmaster.opts').read_text())
    if '-D' not in tokens or Path(tokens[tokens.index('-D')+1]).resolve()!=cluster.resolve() or f'unix_socket_directories={socket}' not in tokens:
        raise RuntimeError('Dedicated PostgreSQL cluster/socket ownership check failed')
    postmaster=int((cluster/'postmaster.pid').read_text().splitlines()[0])
    # One monitoring SELECT after warmup; disconnect before measured calls.
    with psycopg.connect(host=socket,user='jac',dbname='postgres',autocommit=True,
                         application_name='littlex-profile-discovery') as connection:
        records=connection.execute("SELECT pid,datname,application_name FROM pg_stat_activity WHERE backend_type='client backend' AND datname=COALESCE(%s,(SELECT datname FROM pg_stat_activity WHERE application_name LIKE %s LIMIT 1)) ORDER BY pid",(database,f'jac:{pid}:%')).fetchall()
    if not records:
        raise RuntimeError('No warmed app backends; pass --database explicitly if app identity cannot identify it')
    return {'postmaster_pid':postmaster,'database':records[0][1],
            'backends':[{'pid':bp,'database':db,'application_name':name,
                         **full.owned_backend_ticks(bp,postmaster)} for bp,db,name in records]}


def describe(values):
    return {'n':len(values),'mean':statistics.mean(values),'median':statistics.median(values)} if values else {'n':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:18120')
    parser.add_argument('--tag',required=True)
    parser.add_argument('--tier',required=True,choices=['t20','t200'])
    parser.add_argument('--workload',required=True,choices=['feed_chain','feed_page'])
    parser.add_argument('--walker',help='Explicit audited walker override, e.g. load_feed_page_chain for W3')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pid',type=int);group.add_argument('--pid-file',type=Path)
    parser.add_argument('--tokens-dir',required=True,type=Path)
    parser.add_argument('--round-robin', action='store_true', help='Original driver sorted usernames round-robin, per-user oracle')
    parser.add_argument('--user',help='Fixed seed username; default first seed profile')
    parser.add_argument('--warmups',type=int,default=10)
    parser.add_argument('--repeats',type=int,default=10)
    parser.add_argument('--database',help='Explicit existing app DB; otherwise infer once from application_name')
    parser.add_argument('--socket',default='/tmp/jacpg-d6275e76eb')
    parser.add_argument('--seed',type=Path)
    parser.add_argument('--duration-off', action='store_true', help='Explicit CPU/stage-only control; no SQL protocol records expected')
    parser.add_argument('--skip-oracle',action='store_true',help='For explicitly labeled mutated fixtures; record missing seed oracle')
    args=parser.parse_args()
    if args.warmups<10 or args.repeats<10:
        parser.error('Use at least10 warmups and10 profiled calls')
    output=ROOT/'results'/args.tag
    if output.exists():raise RuntimeError(f'Refusing to overwrite {output}')
    pid=args.pid or int(args.pid_file.read_text())
    app_identity=full.process_ticks(pid)
    seed_path=args.seed or ROOT/f'littlex/dataset/{args.tier}_seed.json'
    seed=json.loads(seed_path.read_text())
    user=args.user or seed['profiles'][0]['username']
    tokens=load_tokens('jaseci',args.tokens_dir)
    token=tokens[user]
    all_wanted=expected_feeds(seed)
    all_pages=expected_pages(seed,all_wanted) if args.workload=='feed_page' else None
    wanted=all_wanted[user]
    page=all_pages[user] if args.workload=='feed_page' else None
    workload=harness_run.WORKLOADS[args.workload]
    walker=args.walker or ('load_feed_chain' if args.workload=='feed_chain' else 'load_feed_page')
    captured={}
    def capture(response):
        captured.clear();captured.update({k:float(v) for k,v in response.headers.items() if k.startswith('x-stg-') or k.startswith('x-server-')})
    def request(client,index):
        nonlocal user, token, wanted, page
        if args.round_robin:
            user=sorted(tokens)[index%len(tokens)]
            token=tokens[user]
            wanted=all_wanted[user]
            page=all_pages[user] if args.workload=='feed_page' else None
        if args.walker:
            payload,server=harness_run._jac_walker(client,walker,{},token)
            return payload['feed'],server
        return workload(client,'jaseci',token,index)
    output.mkdir(parents=True)
    ticks=os.sysconf('SC_CLK_TCK')
    log=ROOT/'dbcache/pg/main/server.log'
    rows=[]
    metadata={'tag':args.tag,'tier':args.tier,'workload':args.workload,'walker':walker,
              'user':user,'user_schedule':'sorted usernames round-robin' if args.round_robin else 'fixed user','pid':pid,'app_process_identity':app_identity,'base_url':args.base_url,
              'seed':str(seed_path),'seed_sha256':hashlib.sha256(seed_path.read_bytes()).hexdigest(),
              'tokens_dir':str(args.tokens_dir),'tokens_sha256':hashlib.sha256((args.tokens_dir/'tokens.jaseci.json').read_bytes()).hexdigest(),
              'cpu_tick_resolution_ms':1000/ticks,'warmups':args.warmups,'repeats':args.repeats,
              'oracle':'skipped on explicitly mutated fixture' if args.skip_oracle else 'seed-derived membership/order/page',
              'interpretation':'Stage db is driver execute+fetch wall time; SQL protocol records parse/bind/execute separately. Ser is a build sub-timer. CPU ticks sample entire app/client-backend processes and are not disjoint wall-time phases. This diagnostic reads one fixed user and does not execute a write mix.'}
    def oracle(feed):
        ids=[item['seed_id'] for item in feed]
        return (len(ids)==len(set(ids)) and not order_violations(feed)
                and (ids==page if page is not None else set(ids)==wanted))
    with httpx.Client(base_url=args.base_url,timeout=900,event_hooks={'response':[capture]}) as client,(output/'rows.jsonl').open('w') as incremental:
        for i in range(args.warmups):
            feed,_=request(client,i)
            if not args.skip_oracle and not oracle(feed):raise RuntimeError(f'Warmup seed oracle mismatch for {user}')
            if 'x-stg-db-ms' not in captured:raise RuntimeError('Stage headers missing: start diagnostic app with JAC_STAGE_HEADERS=1')
        info=backends_once(pid,args.socket,args.database)
        metadata['backend_discovery']=info
        known={entry['pid']:entry for entry in info['backends']}
        for index in range(args.repeats):
            offset=log.stat().st_size
            before_db={bp:full.owned_backend_ticks(bp,info['postmaster_pid']) for bp in known}
            before_app=full.process_ticks(pid)
            started=time.perf_counter();feed,server=request(client,index)
            client_ms=(time.perf_counter()-started)*1000
            after_app=full.process_ticks(pid)
            after_db={bp:full.owned_backend_ticks(bp,info['postmaster_pid']) for bp in known}
            if after_app['start_ticks']!=app_identity['start_ticks'] or any(after_db[bp]['start_ticks']!=known[bp]['start_ticks'] for bp in known):
                raise RuntimeError('A sampled process identity changed')
            time.sleep(.05)
            with log.open('rb') as handle:handle.seek(offset);raw=handle.read()
            (output/f'postgres-{index:02d}.log').write_bytes(raw)
            events=full.parse_protocol(raw.decode('utf-8','replace'))
            protocol={phase:{'ms':sum(event['ms'] for event in events if event['phase']==phase),'count':sum(event['phase']==phase for event in events)} for phase in ['parse','bind','execute','statement']}
            app_cpu=1000*sum(after_app[k]-before_app[k] for k in ['user_ticks','system_ticks'])/ticks
            db_deltas=[{'pid':bp,'user_ticks':after_db[bp]['user_ticks']-before_db[bp]['user_ticks'],'system_ticks':after_db[bp]['system_ticks']-before_db[bp]['system_ticks']} for bp in known]
            db_cpu=1000*sum(item['user_ticks']+item['system_ticks'] for item in db_deltas)/ticks
            headers=dict(captured)
            stage_sum=sum(headers.get(f'x-stg-{phase}-ms',0) for phase in ['auth','prep','db','build','commit'])
            record={'repeat':index,'client_ms':client_ms,'server_ms':server,'stage_headers':headers,
                    'stage_sum_ms':stage_sum,'stage_sum_minus_server_ms':stage_sum-server,
                    'application_process_cpu_ms':app_cpu,'database_backend_cpu_ms':db_cpu,'database_backend_cpu_deltas':db_deltas,
                    'protocol':protocol,'database_protocol_total_ms':sum(value['ms'] for value in protocol.values()),
                    'untracked_duration_pids':sorted({event['pid'] for event in events if event['pid'] is not None}-set(known)),
                    'log_start_offset':offset,'log_end_offset':offset+len(raw),'feed_size':len(feed),
                    'oracle_ok':None if args.skip_oracle else oracle(feed),
                    'response_sha256':hashlib.sha256(json.dumps(feed,sort_keys=True).encode()).hexdigest(),
                    'protocol_events':events}
            rows.append(record);incremental.write(json.dumps(record)+'\n');incremental.flush()
            (output/'profile.json').write_text(json.dumps({'metadata':metadata,'rows':rows},indent=2))
            print(json.dumps({k:v for k,v in record.items() if k!='protocol_events'}),flush=True)
            if record['oracle_ok'] is False:raise RuntimeError('Profile seed oracle mismatch')
    summary={'metadata':metadata,'n':len(rows),'oracle_passed':all(row['oracle_ok'] is not False for row in rows),
             'metrics':{key:describe([row[key] for row in rows]) for key in ['client_ms','server_ms','application_process_cpu_ms','database_backend_cpu_ms','database_protocol_total_ms','stage_sum_minus_server_ms']},
             'stages':{phase:describe([row['stage_headers'][f'x-stg-{phase}-ms'] for row in rows if f'x-stg-{phase}-ms' in row['stage_headers']]) for phase in ['dispatch','auth','prep','db','build','commit','ser']},
             'protocol':{phase:describe([row['protocol'][phase]['ms'] for row in rows]) for phase in ['parse','bind','execute','statement']},
             'app_cpu_total_ms':sum(row['application_process_cpu_ms'] for row in rows),
             'backend_cpu_total_ms':sum(row['database_backend_cpu_ms'] for row in rows)}
    (output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
    return 0 if summary['oracle_passed'] and (args.duration_off or all(row['protocol_events'] for row in rows)) else 2


if __name__=='__main__':
    sys.exit(main())
