"""Measure IC5 process CPU and PostgreSQL protocol durations and backend CPU outside trials."""
import argparse
import json
import os
from pathlib import Path
import re
import statistics
import shlex
import psycopg
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'benchmark/scripts'))
from bench_timed import SNB_QUERIES, build_surviving, issue_snb
from snb_validate import Jac


def process_ticks(pid):
    """Read user/system CPU ticks and process identity from our server PID."""
    proc = Path(f'/proc/{pid}')
    command = (proc/'cmdline').read_bytes().replace(b'\0', b' ').decode()
    if str(ROOT) not in command:
        raise RuntimeError(f'PID {pid} is not a reproduction process: {command}')
    # comm may contain spaces/parentheses; fields after its last ')' start at3.
    fields = (proc/'stat').read_text().rsplit(')', 1)[1].split()
    return {'user_ticks': int(fields[11]), 'system_ticks': int(fields[12]),
            'start_ticks': int(fields[19]), 'command': command}


def raw_process_ticks(pid):
    proc = Path(f'/proc/{pid}')
    fields = (proc/'stat').read_text().rsplit(')', 1)[1].split()
    return {'user_ticks':int(fields[11]), 'system_ticks':int(fields[12]),
            'start_ticks':int(fields[19]), 'parent_pid':int(fields[1]),
            'command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()}


def owned_backend_ticks(pid, postmaster):
    sample = raw_process_ticks(pid)
    ancestor = sample['parent_pid']
    for _ in range(16):
        if ancestor == postmaster:
            return sample
        if ancestor <= 1:
            break
        ancestor = raw_process_ticks(ancestor)['parent_pid']
    raise RuntimeError(f'Backend {pid} is not descended from dedicated postmaster {postmaster}')


def discover_backends(socket, database):
    cluster = ROOT/'dbcache/pg/main'
    opts = (cluster/'postmaster.opts').read_text().strip()
    tokens = shlex.split(opts)
    if '-D' not in tokens or Path(tokens[tokens.index('-D')+1]).resolve()!=cluster.resolve():
        raise RuntimeError('postmaster.opts does not identify the dedicated reproduction cluster')
    if f'unix_socket_directories={socket}' not in tokens:
        raise RuntimeError('Requested socket differs from dedicated postmaster.opts')
    postmaster = int((cluster/'postmaster.pid').read_text().splitlines()[0])
    master = raw_process_ticks(postmaster)
    if 'postgres' not in master['command']:
        raise RuntimeError('Dedicated postmaster PID is not PostgreSQL')
    # Exactly one monitoring SELECT; its connection uses postgres DB, not the
    # measured SNB DB, and is closed before the first sampled request.
    with psycopg.connect(host=socket,user='jac',dbname='postgres',autocommit=True,
                         application_name='reproduction-profile-discovery') as conn:
        backends = conn.execute("SELECT pid, application_name, state FROM pg_stat_activity WHERE datname = %s AND backend_type = 'client backend' ORDER BY pid", (database,)).fetchall()
    if not backends:
        raise RuntimeError(f'No warmed client backends for {database}')
    identities = {pid:owned_backend_ticks(pid,postmaster) for pid,_,_ in backends}
    return {'postmaster_pid':postmaster,'postmaster_start_ticks':master['start_ticks'],
            'postmaster_options':opts,'socket':socket,'database':database,
            'backends':[{'pid':pid,'application_name':name,'state_at_discovery':state,
                         **identities[pid]} for pid,name,state in backends]}


def parse_protocol(raw):
    events = []
    pattern = re.compile(r'duration: ([0-9.]+) ms\s+(?:(parse|bind|execute) [^:]*|(statement)): (.*)')
    for line in raw.splitlines():
        match = pattern.search(line)
        if not match:
            continue
        pid = re.search(r'\[(\d+)\]',line[:match.start()])
        events.append({'phase':match.group(2) or match.group(3),'ms':float(match.group(1)),
                       'pid':int(pid.group(1)) if pid else None,'sql_prefix':match.group(4).strip()})
    return events


def summarize(rows):
    fields = ['client_ms', 'server_ms', 'application_process_cpu_ms',
              'application_process_user_cpu_ms', 'application_process_system_cpu_ms',
              'database_execute_ms','database_parse_ms','database_bind_ms','database_simple_statement_ms',
              'database_protocol_total_ms','database_backend_cpu_ms','database_backend_user_cpu_ms',
              'database_backend_system_cpu_ms','remaining_transport_driver_app_ms']
    return {key: {'mean': statistics.mean(values), 'median': statistics.median(values)}
            for key in fields
            if (values := [float(row[key]) for row in rows if row.get(key) is not None])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--row', type=int, default=19)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--socket', default='/tmp/jacpg-d6275e76eb')
    parser.add_argument('--database', default='jac_snb_bench_pg_fbdb3a2c')
    parser.add_argument('--warmups', type=int, default=2)
    args = parser.parse_args()
    if args.repeats < 1 or args.warmups < 0:
        parser.error('repeats must be positive; warmups must be nonnegative')
    ctx = Jac('jaseci-pg')
    row = dict(build_surviving(ctx,20)[SNB_QUERIES['ic5']['file']])[args.row]
    pid = int((ROOT/'logs/jac.pid').read_text())
    clock_ticks = os.sysconf('SC_CLK_TCK')
    process = process_ticks(pid)
    log = ROOT/'dbcache/pg/main/server.log'
    output_dir = ROOT/'results'/args.tag
    output_dir.mkdir(parents=True,exist_ok=True)
    rows = []
    raw_logs = []
    result = {'tag': args.tag, 'row': args.row, 'pid': pid,
              'process_start_ticks': process['start_ticks'], 'command': process['command'],
              'clock_ticks_per_second': clock_ticks, 'cpu_tick_resolution_ms': 1000/clock_ticks,
              'warmups': args.warmups, 'requested_repeats': args.repeats, 'rows': rows,
              'interpretation': 'Backend CPU measures only the discovered existing client backend processes, excluding parallel workers/autovacuum and later connections. Application CPU is the Jac server process user+system CPU delta, including its threads/background work. PostgreSQL parse/bind/execute/simple-statement durations are separately recorded; their sum is logged protocol processing wall time. Remaining client wall time subtracts the complete logged protocol sum and includes transport, driver conversion and application work; it is not a pure CPU measurement. CPU and wall-time quantities must not be added as disjoint portions. PostgreSQL duration logging is enabled for this separate diagnostic run.'}
    with httpx.Client(base_url='http://127.0.0.1:18109',timeout=900) as client, (output_dir/'profile-rows.jsonl').open('w') as incremental:
        for _ in range(args.warmups):
            _,_,_,err = issue_snb('jaseci-pg',client,ctx,{},'ic5',row)
            if err:
                raise RuntimeError(err)
        backend_info = discover_backends(args.socket,args.database)
        result['backend_discovery'] = backend_info
        known_pids = {entry['pid'] for entry in backend_info['backends']}
        backend_start_ticks = {entry['pid']:entry['start_ticks'] for entry in backend_info['backends']}
        for repeat in range(args.repeats):
            offset = log.stat().st_size
            backend_before = {bp:owned_backend_ticks(bp,backend_info['postmaster_pid']) for bp in known_pids}
            before = process_ticks(pid)
            client_ms,server,out,err = issue_snb('jaseci-pg',client,ctx,{},'ic5',row)
            after = process_ticks(pid)
            backend_after = {bp:owned_backend_ticks(bp,backend_info['postmaster_pid']) for bp in known_pids}
            if any(backend_after[bp]['start_ticks'] != backend_start_ticks[bp] or backend_before[bp]['start_ticks'] != backend_start_ticks[bp] for bp in known_pids):
                raise RuntimeError('A discovered PostgreSQL backend changed during profiling')
            if before['start_ticks'] != after['start_ticks'] or after['start_ticks'] != process['start_ticks']:
                raise RuntimeError('Jac server process changed during profiling')
            time.sleep(.1)
            with log.open('rb') as handle:
                handle.seek(offset)
                raw = handle.read().decode('utf-8','replace')
            (output_dir/f'postgres-{repeat:02d}.log').write_text(raw)
            raw_logs.append(raw)
            events = parse_protocol(raw)
            protocol = {phase:{'ms':sum(event['ms'] for event in events if event['phase']==phase),
                               'count':sum(event['phase']==phase for event in events)}
                        for phase in ['parse','bind','execute','statement']}
            database_ms = protocol['execute']['ms']
            protocol_total = sum(value['ms'] for value in protocol.values())
            backend_deltas = [{'pid':bp,
                               'user_ticks':backend_after[bp]['user_ticks']-backend_before[bp]['user_ticks'],
                               'system_ticks':backend_after[bp]['system_ticks']-backend_before[bp]['system_ticks']}
                              for bp in sorted(known_pids)]
            db_user_ticks = sum(delta['user_ticks'] for delta in backend_deltas)
            db_system_ticks = sum(delta['system_ticks'] for delta in backend_deltas)
            unknown_log_pids = sorted({event['pid'] for event in events if event['pid'] is not None}-known_pids)
            statements = [event for event in events if event['phase'] in ('execute','statement')]
            user_ticks = after['user_ticks']-before['user_ticks']
            system_ticks = after['system_ticks']-before['system_ticks']
            entry = {'repeat':repeat, 'client_ms':client_ms, 'server_ms':server,
                     'application_process_user_ticks':user_ticks, 'application_process_system_ticks':system_ticks,
                     'application_process_user_cpu_ms':1000*user_ticks/clock_ticks,
                     'application_process_system_cpu_ms':1000*system_ticks/clock_ticks,
                     'application_process_cpu_ms':1000*(user_ticks+system_ticks)/clock_ticks,
                     'database_execute_ms':database_ms,
                     'database_parse_ms':protocol['parse']['ms'], 'database_bind_ms':protocol['bind']['ms'],
                     'database_simple_statement_ms':protocol['statement']['ms'],
                     'database_protocol_total_ms':protocol_total, 'protocol':protocol,
                     'database_backend_user_cpu_ms':1000*db_user_ticks/clock_ticks,
                     'database_backend_system_cpu_ms':1000*db_system_ticks/clock_ticks,
                     'database_backend_cpu_ms':1000*(db_user_ticks+db_system_ticks)/clock_ticks,
                     'database_backend_cpu_deltas':backend_deltas,
                     'duration_log_pids_outside_discovery':unknown_log_pids,
                     'backend_cpu_covers_duration_log_pids':not unknown_log_pids,
                     'remaining_transport_driver_app_ms':client_ms-protocol_total,
                     'statement_count':len(statements),
                     'protocol_events':events, 'statements':sorted(statements,key=lambda statement:-statement['ms']), 'error':err}
            rows.append(entry)
            incremental.write(json.dumps(entry)+'\n')
            incremental.flush()
            result['summary'] = summarize(rows)
            (output_dir/'profile.json').write_text(json.dumps(result,indent=2))
            (output_dir/'postgres.log').write_text(''.join(raw_logs))
            print(json.dumps(entry),flush=True)
            if err:
                raise RuntimeError(err)
    print(json.dumps({'tag':args.tag,'repeats':len(rows),'summary':result['summary']},indent=2),flush=True)


if __name__ == '__main__':
    main()
