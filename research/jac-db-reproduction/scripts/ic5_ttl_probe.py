"""Diagnose IC5 one-statement variation without changing TTL/cache settings.

The orchestrator enables statement/duration logging before invoking this script
and restores its logging settings afterwards. Run outside latency trials.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'benchmark/scripts'))
from bench_timed import SNB_QUERIES,build_surviving,issue_snb
from snb_validate import Jac,canon


def classify(raw):
    calls = []
    duration_calls = []
    for line in raw.splitlines():
        match = re.search(r'LOG:\s+(?:execute [^:]*|statement):\s*(.*)',line)
        duration = False
        if not match:
            match = re.search(r'LOG:\s+duration: [0-9.]+ ms\s+(?:execute [^:]*|statement):\s*(.*)',line)
            duration = True
        if not match:
            continue
        sql = match.group(1).strip()
        pid = re.search(r'\[(\d+)\]',line[:match.start()])
        (duration_calls if duration else calls).append({'pid':int(pid.group(1)) if pid else None,'sql':sql})
    # log_statement plus duration logging emits two entries for one execution.
    # Prefer pre-execution records when available, otherwise use duration logs.
    calls = calls or duration_calls
    # Match the actual memo existence probe, not general use of to_regclass.
    guard = re.compile(r'^SELECT\s+count\(\*\)\s+FROM\s+\(VALUES\s+.+\)\s+v\(n\)\s+WHERE\s+to_regclass\(v\.n\)\s+IS\s+NULL\s*;?$',re.I)
    guards = [call for call in calls if guard.match(call['sql'])]
    return calls,guards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag',default='ic5-ttl-probe')
    parser.add_argument('--base-url',default='http://127.0.0.1:18109')
    args = parser.parse_args()
    output = ROOT/'results'/args.tag
    if output.exists():
        raise RuntimeError(f'Refusing to overwrite existing probe: {output}')
    ctx = Jac('jaseci-pg')
    fixtures = dict(build_surviving(ctx,20)[SNB_QUERIES['ic5']['file']])
    historical_path = ROOT.parent/'DBHarness/session0904/run/data/snb/postgres/snb_postgres.hashes.json'
    historical = json.loads(historical_path.read_text())
    output.mkdir(parents=True)
    log = ROOT/'dbcache/pg/main/server.log'
    plan = [(3,0.0),(3,0.0),(3,5.5),(13,0.0),(13,0.0)]
    results = []
    with httpx.Client(base_url=args.base_url,timeout=900) as client, (output/'rows.jsonl').open('w') as rows_file:
        for sequence,(index,delay) in enumerate(plan):
            if delay:
                time.sleep(delay)  # Deliberately outside measured call/window.
            offset = log.stat().st_size
            start_wall = datetime.now(timezone.utc).isoformat()
            start_mono = time.monotonic()
            client_ms,server_ms,response,error = issue_snb('jaseci-pg',client,ctx,{},'ic5',fixtures[index])
            end_mono = time.monotonic()
            end_wall = datetime.now(timezone.utc).isoformat()
            time.sleep(.05)  # Flush allowance outside measured call.
            with log.open('rb') as handle:
                handle.seek(offset)
                raw_bytes = handle.read()
            raw = raw_bytes.decode('utf-8','replace')
            (output/f'postgres-{sequence:02d}-idx{index}.log').write_bytes(raw_bytes)
            calls,guards = classify(raw)
            digest = hashlib.sha256(canon(response).encode()).hexdigest() if error is None else None
            parity = error is None and digest==historical[f'ic5:{index}']
            row = {'sequence':sequence,'idx':index,'sleep_before_seconds':delay,
                   'call_start_wall_utc':start_wall,'call_end_wall_utc':end_wall,
                   'call_start_monotonic':start_mono,'call_end_monotonic':end_mono,
                   'log_start_offset':offset,'log_end_offset':offset+len(raw_bytes),
                   'client_ms':client_ms,'server_ms':server_ms,'error':error,
                   'response_sha256':digest,'historical_sha256':historical[f'ic5:{index}'],
                   'parity':parity,'execute_or_statement_count':len(calls),
                   'schema_guard_count':len(guards),'schema_guard_statements':guards,
                   'non_guard_statement_count':len(calls)-len(guards),
                   'statement_backend_pids':sorted({call['pid'] for call in calls if call['pid'] is not None})}
            results.append(row)
            rows_file.write(json.dumps(row)+'\n');rows_file.flush()
            (output/'rows.json').write_text(json.dumps(results,indent=2))
            print(json.dumps(row),flush=True)
    same_input = [row for row in results if row['idx']==3]
    observed_variation = len({row['execute_or_statement_count'] for row in same_input})>1
    invariant_non_guard = len({row['non_guard_statement_count'] for row in same_input})==1
    summary = {'tag':args.tag,'rows':results,'historical_reference':str(historical_path),
               'all_parity':all(row['parity'] for row in results),
               'all_statement_windows_nonempty':all(row['execute_or_statement_count']>0 for row in results),
               'idx3_total_count_varies':observed_variation,
               'idx3_non_guard_count_invariant':invariant_non_guard,
               'idx3_count_variation_accounted_for_by_guard':observed_variation and invariant_non_guard,
               'interpretation':'Compare exact schema-guard SQL counts and residual counts for the same input. Stable residual counts with differing total counts support TTL-guard attribution for these probe calls. Raw logs retain PID and timestamps. The probe does not change runtime TTL or caches.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if summary['all_parity'] and summary['all_statement_windows_nonempty'] else 2


if __name__=='__main__':
    sys.exit(main())
