"""Offline per-request-tag WAL wait and counter attribution."""
import collections,gzip,json,pathlib,statistics
R=pathlib.Path(__file__).resolve().parent;D=R/'tpcc-wal-diagnostic'
cert=json.loads((D/'certified-requests.json').read_text());cells={}
for p in sorted((D/'delay-2ms/baseline').iterdir()):
    req=[x for x in cert if x['label']==p.name]
    pids={q['pid'] for x in req for q in x['operations']};tags={x['request_tag'] for x in req}
    samples=[json.loads(s) for s in gzip.open(p/'wait-events.jsonl.gz','rt')]
    samples=[s for s in samples if s['pid'] in pids and s['request_tag'] in tags]
    before=json.loads((p/'counters-before-measured.json').read_text())['counters'];after=json.loads((p/'counters-after-service-stop.json').read_text())['counters']
    base={(x['backend_type'],x['context']):x for x in before['wal_io_rows']};delta={}
    for x in after['wal_io_rows']:
        k=(x['backend_type'],x['context']);v={n:x[n]-base[k][n] for n in ['writes','write_time','fsyncs','fsync_time'] if x.get(n)is not None and base[k].get(n)is not None}
        if any(v.values()):delta['/'.join(k)]=v
    def waits(xs):return dict(collections.Counter(str(s['wait_event_type'])+'/'+str(s['wait_event']) for s in xs))
    cells[p.name]={'n':len(req),'application_backend_PIDs':sorted(pids),'commit_execute_median_ms':statistics.median(q['execute_ms'] for x in req for q in x['operations'] if q['category']=='transaction.commit'),'active_owned_app_samples':len(samples),'sampled_wait_counts':waits(samples),'sampled_COMMIT_wait_counts':waits(s for s in samples if s['query_prefix'].strip().upper()=='COMMIT'),'WAL_IO_delta':delta,'effective_settings':before['effective_settings']}
result={'scope':'Instrumented diagnostic: measured request tags and actual traced application backend PIDs only; wait frequencies are sampled occupancy, not exact time. WAL counter deltas span measured-phase boundary through application shutdown and include shared backend-class counters.','cells':cells}
(D/'WAL-analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
