#!/usr/bin/env python3
"""Profile an immutable Java command through actual MySQL wire and P_S events.

Command JSON is an argv array. {endpoint} and {profile_output} are replaced
literally with the owned proxy endpoint and result directory. This collector
takes the common measurement lease; callers must not hold that lease already.
"""
import argparse
import fcntl
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback

from measurement_lease import lease

HERE = Path(__file__).resolve().parent
WB = HERE.parent


def sql(query):
    return subprocess.check_output(['docker', 'exec', 'jac-webridge-mysql57',
                                   'mysql', '-uroot', '-N', '-B', '-r', '-e', query],
                                  text=True, timeout=20).strip()


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--command-json', type=Path, required=True)
    parser.add_argument('--database', required=True)
    parser.add_argument('--prepare-command-json', type=Path,
                        help='Fresh-state reset argv; runs inside the lease, before instrumentation')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18552)
    parser.add_argument('--delay-ms', type=float, default=2)
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--command-limit', type=float, default=15)
    parser.add_argument('--all-control-events', action='store_true')
    args = parser.parse_args()
    assert all(char.isalnum() or char == '_' for char in args.database)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    template = json.loads(args.command_json.read_text())
    assert isinstance(template, list) and all(isinstance(item, str) for item in template)
    assert any('{endpoint}' in item for item in template), 'Use the actual owned proxy endpoint'
    assert any('{profile_output}' in item for item in template), 'Use the owned output directory'
    command = [item.replace('{endpoint}', f'127.0.0.1:{args.port}')
               .replace('{profile_output}', str(out / 'run')) for item in template]
    write(out / 'request-command.json', command)
    write(out / 'config.json', {**vars(args), 'command_json': str(args.command_json.resolve()),
                              'prepare_command_json': str(args.prepare_command_json.resolve()) if args.prepare_command_json else None,
                              'out': str(out), 'command_sha256': hashlib.sha256(args.command_json.read_bytes()).hexdigest(),
                              'instrumentation': 'all stored-program events' if args.all_control_events else 'stored-program statements and cursor opens'})
    with lease('MySQL wire/P_S ' + args.database, out / 'lease.json'):
        with (WB / 'integration/.mysql-sp-profile.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if args.prepare_command_json:
                prepare = json.loads(args.prepare_command_json.read_text())
                assert isinstance(prepare, list) and all(isinstance(item, str) for item in prepare)
                with (out / 'prepare-stdout.log').open('w') as stdout, (out / 'prepare-stderr.log').open('w') as stderr:
                    started = time.time_ns()
                    prepared = subprocess.run(prepare, stdout=stdout, stderr=stderr, timeout=args.timeout)
                write(out / 'prepare.json', {'command': prepare, 'started_wall_ns': started,
                                              'ended_wall_ns': time.time_ns(), 'returncode': prepared.returncode,
                                              'source_sha256': hashlib.sha256(args.prepare_command_json.read_bytes()).hexdigest()})
                prepared.check_returncode()
            profile(args, out, command)


def profile(args, out, command):
    instrument_query = "SELECT NAME,ENABLED,TIMED FROM performance_schema.setup_instruments WHERE NAME LIKE 'statement/sp/%' ORDER BY NAME"
    consumer_query = "SELECT NAME,ENABLED FROM performance_schema.setup_consumers WHERE NAME IN ('events_statements_current','events_statements_history','events_statements_history_long') ORDER BY NAME"
    before = [line.split('\t') for line in sql(instrument_query).splitlines()]
    consumers = [line.split('\t') for line in sql(consumer_query).splitlines()]
    write(out / 'SP-instruments-before.json', before)
    write(out / 'consumers-before.json', consumers)
    (out / 'server-settings.tsv').write_text(sql("SELECT @@global.general_log;SHOW VARIABLES LIKE 'performance_schema_events_statements_history_long_size';SHOW VARIABLES LIKE 'performance_schema_max_sql_text_length'"))
    assert sql('SELECT @@global.general_log') == '0'
    proxy = None
    monitor = None
    stop = threading.Event()
    events = {}
    polls = []
    summaries = []
    errors = []
    owned = {}
    foreign_events = []
    foreign_count = 0

    def process_state():
        if 'connection_id' not in owned:
            return None
        text = sql("SELECT JSON_OBJECT('id',ID,'db',DB,'command',COMMAND,'state',STATE,'info',INFO) FROM information_schema.PROCESSLIST WHERE ID=" + str(owned['connection_id']))
        return json.loads(text) if text else None

    def kill_owned(reason):
        state = process_state()
        result = {'reason': reason, 'wall_ns': time.time_ns(), 'owned': dict(owned), 'before': state}
        if state:
            assert state['db'] == args.database and state['id'] == owned['connection_id'], state
            sql('KILL CONNECTION ' + str(state['id']))
        for _ in range(100):
            if process_state() is None:
                break
            time.sleep(.05)
        result['absence_verified'] = process_state() is None
        assert result['absence_verified']
        write(out / ('cleanup-' + str(time.time_ns()) + '.json'), result)

    def collect():
        nonlocal foreign_count
        offset = 0
        partial = ''
        pending = {}
        final_polls = 0
        try:
            while True:
                trace = out / 'protocol.jsonl'
                if trace.exists():
                    with trace.open() as handle:
                        handle.seek(offset)
                        chunk = handle.read()
                        offset = handle.tell()
                    lines = (partial + chunk).splitlines(keepends=True)
                    partial = ''
                    for line in lines:
                        if not line.endswith('\n'):
                            partial = line
                            continue
                        event = json.loads(line)
                        if event['event'] == 'server_greeting':
                            assert not owned, 'A profile command must use exactly one JDBC connection'
                            owned['connection_id'] = event['server_connection_id']
                        elif event['event'] == 'command':
                            pending[event['id']] = event
                        elif event['event'] == 'response_complete' and event['stage'] == 'delivered':
                            pending.pop(event['command_id'], None)
                    slow = [event for event in pending.values()
                            if event.get('sql') is not None and time.monotonic() - event['at'] > args.command_limit]
                    if slow and process_state() is not None:
                        write(out / 'command-timeout.json', {'limit_s': args.command_limit, 'commands': slow})
                        kill_owned('command exceeded wall-time bound')
                        errors.append('command timeout')
                        break
                if 'connection_id' in owned and 'thread_id' not in owned:
                    tid = sql('SELECT THREAD_ID FROM performance_schema.threads WHERE PROCESSLIST_ID=' + str(owned['connection_id']))
                    if tid:
                        owned['thread_id'] = int(tid)
                        write(out / 'connection.json', owned)
                if 'thread_id' in owned:
                    tid = owned['thread_id']
                    started = time.monotonic_ns()
                    query = "SELECT JSON_OBJECT('thread',THREAD_ID,'event',EVENT_ID,'end_event',END_EVENT_ID,'nest',NESTING_EVENT_ID,'nest_type',NESTING_EVENT_TYPE,'name',EVENT_NAME,'sql',SQL_TEXT,'timer_start',TIMER_START,'timer_end',TIMER_END,'timer_ps',TIMER_WAIT,'rows_examined',ROWS_EXAMINED,'rows_sent',ROWS_SENT,'no_index',NO_INDEX_USED,'no_good_index',NO_GOOD_INDEX_USED,'object',OBJECT_NAME,'error',MYSQL_ERRNO) FROM performance_schema.events_statements_history_long WHERE THREAD_ID=" + str(tid) + ' ORDER BY EVENT_ID'
                    raw = sql(query)
                    added = 0
                    for line in raw.splitlines():
                        event = json.loads(line)
                        if event['thread'] != tid:
                            foreign_count += 1
                            if len(foreign_events) < 50:
                                foreign_events.append(event)
                            continue
                        key = (event['thread'], event['event'])
                        added += key not in events
                        events[key] = event
                    counters = sql("SELECT JSON_OBJECT('thread',THREAD_ID,'name',EVENT_NAME,'count',COUNT_STAR,'timer_ps',SUM_TIMER_WAIT) FROM performance_schema.events_statements_summary_by_thread_by_event_name WHERE THREAD_ID=" + str(tid) + " AND EVENT_NAME LIKE 'statement/%'")
                    summaries.append({'at_mono_ns': time.monotonic_ns(), 'rows': [json.loads(line) for line in counters.splitlines()]})
                    polls.append({'start_mono_ns': started, 'end_mono_ns': time.monotonic_ns(),
                                  'returned_rows': len(raw.splitlines()), 'new_events': added})
                if stop.is_set():
                    final_polls += 1
                    if final_polls >= 2:
                        break
                stop.wait(.1)
        except BaseException:
            errors.append(traceback.format_exc())
            try:
                if owned:
                    kill_owned('P_S collector failed; bound the owned request')
            except BaseException:
                errors.append(traceback.format_exc())
            # The controller owns this fresh process group and its PID receipt.
            pid_receipt = out / 'run/pid.json'
            if pid_receipt.exists():
                pid = json.loads(pid_receipt.read_text())['pid']
                try:
                    if os.getpgid(pid) == pid:
                        os.killpg(pid, signal.SIGTERM)
                        write(out / 'collector-client-stop.json', {'owned_process_group': pid, 'signal': 'SIGTERM'})
                except ProcessLookupError:
                    pass

    failure = None
    proxy_log = (out / 'proxy.log').open('w')
    try:
        sql("UPDATE performance_schema.setup_consumers SET ENABLED='YES' WHERE NAME IN ('events_statements_current','events_statements_history_long')")
        if args.all_control_events:
            sql("UPDATE performance_schema.setup_instruments SET ENABLED='YES',TIMED='YES' WHERE NAME LIKE 'statement/sp/%'")
        else:
            sql("UPDATE performance_schema.setup_instruments SET ENABLED=IF(NAME IN ('statement/sp/stmt','statement/sp/copen'),'YES','NO'),TIMED=IF(NAME IN ('statement/sp/stmt','statement/sp/copen'),'YES','NO') WHERE NAME LIKE 'statement/sp/%'")
        (out / 'SP-instruments-active.tsv').write_text(sql(instrument_query))
        proxy_command = [sys.executable, str(WB / 'benchmark-comparison/mysql-profile/trace_proxy.py'),
                         '--port', str(args.port), '--delay-ms', str(args.delay_ms),
                         '--quit-grace-ms', '1000', '--trace', str(out / 'protocol.jsonl'),
                         '--receipt', str(out / 'proxy-cleanup.json')]
        write(out / 'proxy-command.json', proxy_command)
        proxy = subprocess.Popen(proxy_command, stdout=proxy_log, stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(100):
            if '"ready": true' in (out / 'proxy.log').read_text():
                break
            assert proxy.poll() is None, 'Proxy exited during startup'
            time.sleep(.05)
        else:
            raise TimeoutError('Proxy readiness')
        monitor = threading.Thread(target=collect)
        monitor.start()
        spec = importlib.util.spec_from_file_location('original_webridge_control', WB / 'integration/control.py')
        ctl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ctl)
        ctl.LIMITS = {'rss_bytes': 12 * 1024 ** 3, 'output_bytes': 8 * 1024 ** 3}
        ctl.command(command, out / 'run', args.timeout)
    except BaseException:
        failure = traceback.format_exc()
    finally:
        stop.set()
        if monitor:
            monitor.join(timeout=60)
            if monitor.is_alive():
                errors.append('P_S collector did not finish')
        if owned:
            try:
                kill_owned('owned profiling command ended')
            except BaseException:
                errors.append(traceback.format_exc())
        if proxy and proxy.poll() is None:
            try:
                os.killpg(proxy.pid, signal.SIGTERM)
                proxy.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proxy.pid, signal.SIGKILL)
                proxy.wait()
            except ProcessLookupError:
                proxy.wait()
        if proxy and proxy.returncode != 0:
            errors.append('Proxy return code ' + str(proxy.returncode))
        proxy_log.close()
        # Attempt every restoration even if an earlier individual command fails.
        restoration_errors = []
        for name, enabled, timed in before:
            try:
                sql(f"UPDATE performance_schema.setup_instruments SET ENABLED='{enabled}',TIMED='{timed}' WHERE NAME='{name}'")
            except BaseException:
                restoration_errors.append(traceback.format_exc())
        for name, enabled in consumers:
            try:
                sql(f"UPDATE performance_schema.setup_consumers SET ENABLED='{enabled}' WHERE NAME='{name}'")
            except BaseException:
                restoration_errors.append(traceback.format_exc())
        restored = [line.split('\t') for line in sql(instrument_query).splitlines()]
        restored_consumers = [line.split('\t') for line in sql(consumer_query).splitlines()]
        exact = restored == before and restored_consumers == consumers
        write(out / 'instrumentation-restored.json', {'exact_prior_settings_restored': exact,
                                                      'instruments': restored, 'consumers': restored_consumers,
                                                      'errors': restoration_errors})
        errors.extend(restoration_errors)
        if not exact:
            errors.append('Instrumentation differs from its exact prior settings')
        if 'thread_id' not in owned or not events:
            errors.append('Missing owned P_S thread or statement events')
        if foreign_count:
            errors.append('Foreign decoded P_S events: ' + str(foreign_count))
        (out / 'pfs.jsonl').write_text(''.join(json.dumps(event) + '\n' for _, event in sorted(events.items())))
        write(out / 'pfs-polls.json', {'polls': polls, 'errors': errors, 'unique_key': 'THREAD_ID,EVENT_ID',
                                     'deduplicated_events': len(events), 'whole_process_error': failure,
                                     'foreign_decoded_events': foreign_count, 'foreign_examples': foreign_events})
        write(out / 'P_S-thread-summary-snapshots.json', summaries)
        if proxy:
            write(out / 'proxy-process.json', {'pid': proxy.pid, 'returncode': proxy.returncode, 'stopped': proxy.poll() is not None})
        if (out / 'protocol.jsonl').exists():
            with (out / 'protocol.jsonl').open('rb') as source, gzip.open(out / 'protocol.jsonl.gz', 'wb') as dest:
                shutil.copyfileobj(source, dest)
    write(out / 'collection.json', {'status': 'PASS' if not failure and not errors else 'FAILED',
                                    'owned_connection': owned, 'errors': errors, 'command_error': failure,
                                    'P_S_events': len(events), 'delay_ms': args.delay_ms})
    if failure or errors:
        raise RuntimeError(failure or errors)
    print(out)


if __name__ == '__main__':
    main()
