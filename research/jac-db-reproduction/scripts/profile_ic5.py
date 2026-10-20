"""Measure IC5 process CPU and PostgreSQL execute durations outside trials."""
import argparse
import json
import os
from pathlib import Path
import re
import statistics
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


def summarize(rows):
    fields = ['client_ms', 'server_ms', 'application_process_cpu_ms',
              'application_process_user_cpu_ms', 'application_process_system_cpu_ms',
              'database_execute_ms', 'remaining_transport_driver_app_ms']
    return {key: {'mean': statistics.mean(values), 'median': statistics.median(values)}
            for key in fields
            if (values := [float(row[key]) for row in rows if row.get(key) is not None])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--row', type=int, default=19)
    parser.add_argument('--repeats', type=int, default=5)
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
              'interpretation': 'Application CPU is the Jac server process user+system CPU delta, including its threads/background work. PostgreSQL execute/statement durations exclude protocol parse/bind. Remaining client wall time includes transport, driver conversion and application work; it is not a pure CPU measurement. CPU and wall-time quantities must not be added as disjoint portions. PostgreSQL duration logging is enabled for this separate diagnostic run.'}
    with httpx.Client(base_url='http://127.0.0.1:18109',timeout=900) as client, (output_dir/'profile-rows.jsonl').open('w') as incremental:
        for _ in range(args.warmups):
            _,_,_,err = issue_snb('jaseci-pg',client,ctx,{},'ic5',row)
            if err:
                raise RuntimeError(err)
        for repeat in range(args.repeats):
            offset = log.stat().st_size
            before = process_ticks(pid)
            client_ms,server,out,err = issue_snb('jaseci-pg',client,ctx,{},'ic5',row)
            after = process_ticks(pid)
            if before['start_ticks'] != after['start_ticks'] or after['start_ticks'] != process['start_ticks']:
                raise RuntimeError('Jac server process changed during profiling')
            time.sleep(.1)
            with log.open('rb') as handle:
                handle.seek(offset)
                raw = handle.read().decode('utf-8','replace')
            (output_dir/f'postgres-{repeat:02d}.log').write_text(raw)
            raw_logs.append(raw)
            statements = [{'ms':float(match.group(1)), 'sql_prefix':match.group(2).strip()}
                          for match in re.finditer(r'duration: ([0-9.]+) ms\s+(?:execute [^:]*|statement): (.*)',raw)]
            database_ms = sum(statement['ms'] for statement in statements)
            user_ticks = after['user_ticks']-before['user_ticks']
            system_ticks = after['system_ticks']-before['system_ticks']
            entry = {'repeat':repeat, 'client_ms':client_ms, 'server_ms':server,
                     'application_process_user_ticks':user_ticks, 'application_process_system_ticks':system_ticks,
                     'application_process_user_cpu_ms':1000*user_ticks/clock_ticks,
                     'application_process_system_cpu_ms':1000*system_ticks/clock_ticks,
                     'application_process_cpu_ms':1000*(user_ticks+system_ticks)/clock_ticks,
                     'database_execute_ms':database_ms,
                     'remaining_transport_driver_app_ms':client_ms-database_ms,
                     'statement_count':len(statements),
                     'statements':sorted(statements,key=lambda statement:-statement['ms']), 'error':err}
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
