"""Run the original SNB timing driver with relocated reproduction services.

Canonical workload:20 parameter rows,140 warm calls,2550 timed calls
(750 per IS query;75 per IC query), and140 historical response hashes.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'benchmark/scripts'))
import bench_timed

HISTORICAL = ROOT.parent/'DBHarness/session0904/run/data/snb/postgres/snb_postgres.hashes.json'
DEFAULT_URLS = {'jaseci-pg':'http://127.0.0.1:18109',
                'postgres':'http://127.0.0.1:18111',
                'sqlalchemy':'http://127.0.0.1:18113',
                'neo4j':'http://127.0.0.1:18114'}


def metric(values):
    if not values:
        return {'n':0, 'mean_ms':None, 'median_ms':None,
                'upper_middle_ms':None, 'p95_nearest_rank_ms':None}
    values = sorted(values)
    return {'n':len(values), 'mean_ms':statistics.mean(values),
            'median_ms':statistics.median(values),
            'upper_middle_ms':values[len(values)//2],
            'p95_nearest_rank_ms':values[math.ceil(.95*len(values))-1]}


def summarize(output, arm):
    prefix = output/f'snb_{arm}'
    meta = json.loads(prefix.with_suffix('.meta.json').read_text())
    hashes = json.loads(prefix.with_suffix('.hashes.json').read_text())
    historical = json.loads(HISTORICAL.read_text())
    with prefix.with_suffix('.csv').open(newline='') as handle:
        timed = list(csv.DictReader(handle))
    with prefix.with_suffix('.warm.csv').open(newline='') as handle:
        warm = list(csv.DictReader(handle))
    expected_counts = {q:750 if q.startswith('is') else 75 for q in bench_timed.QUERY_ORDER}
    summary = {'arm':arm, 'queries':{}, 'warm_n':len(warm), 'timed_n':len(timed),
               'errors':meta.get('errors',[]),
               'historical_reference':str(HISTORICAL),
               'historical_reference_sha256':hashlib.sha256(HISTORICAL.read_bytes()).hexdigest(),
               'historical_hash_matches':sum(hashes.get(k)==v for k,v in historical.items()),
               'historical_hash_expected':len(historical),
               'hash_missing':sorted(set(historical)-set(hashes)),
               'hash_extra':sorted(set(hashes)-set(historical)),
               'hash_mismatches':[k for k in sorted(set(historical)&set(hashes)) if historical[k]!=hashes[k]],
               'percentile_definition':'p95 uses nearest rank: sorted[ceil(0.95*n)-1]. Upper-middle uses sorted[n//2]; conventional median averages two middle values when n is even.',
               'hash_scope':'Original run_snb hashes warm rep0 responses; timed responses retain the original runner behavior.'}
    for query in bench_timed.QUERY_ORDER:
        rows = [row for row in timed if row['query']==query]
        summary['queries'][query] = {'expected_n':expected_counts[query], 'actual_n':len(rows),
                                    'client':metric([float(row['client_ms']) for row in rows if row['client_ms']]),
                                    'server':metric([float(row['server_ms']) for row in rows if row['server_ms']])}
    summary['passed'] = (not summary['errors'] and len(warm)==140 and len(timed)==2550
                         and len(historical)==140 and len(hashes)==140
                         and not summary['hash_missing'] and not summary['hash_extra'] and not summary['hash_mismatches']
                         and all(summary['queries'][q]['actual_n']==n for q,n in expected_counts.items())
                         and meta['counts']['warm_total']==140 and meta['counts']['timed_total']==2550)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', required=True, choices=list(DEFAULT_URLS))
    parser.add_argument('--base-url', help='Override the selected reproduction service URL')
    parser.add_argument('--out-dir', required=True, type=Path)
    parser.add_argument('--dry-run', action='store_true', help='Use original runner plan-only mode; no HTTP requests')
    args = parser.parse_args()
    output = args.out_dir.resolve()
    if not args.dry_run and output.exists() and any(output.glob(f'snb_{args.arm}.*')):
        parser.error('Output already contains this arm; use a new output directory to preserve raw results')
    bench_timed.SNB_ARMS.update(DEFAULT_URLS)
    bench_timed.SNB_ARMS[args.arm] = args.base_url or DEFAULT_URLS[args.arm]
    original = argparse.Namespace(arm=args.arm,rows=20,warm_reps=1,is_reps=750,
                                  ic_reps=75,ic13_reps=None,queries=','.join(bench_timed.QUERY_ORDER),
                                  jac_source='jaseci-pg',out_dir=output,dry_run=args.dry_run)
    if args.dry_run:
        bench_timed.run_snb(original)
        return 0
    output.mkdir(parents=True,exist_ok=True)
    invocation = {key:str(value) if isinstance(value,Path) else value for key,value in vars(original).items()}
    invocation.update(base_url=bench_timed.SNB_ARMS[args.arm],python=sys.version,
                      runner_path=bench_timed.__file__,
                      runner_sha256=hashlib.sha256(Path(bench_timed.__file__).read_bytes()).hexdigest())
    (output/'canonical-invocation.json').write_text(json.dumps(invocation,indent=2))
    status = 0
    try:
        bench_timed.run_snb(original)
    except SystemExit as error:
        status = error.code if isinstance(error.code,int) else 1
    try:
        summary = summarize(output,args.arm)
    except Exception as error:
        summary = {'passed':False,'summary_error':f'{type(error).__name__}: {error}',
                   'runner_exit_status':status}
    summary['runner_exit_status'] = status
    if status:
        summary['passed'] = False
    (output/'canonical-summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if summary['passed'] else 2


if __name__ == '__main__':
    sys.exit(main())
