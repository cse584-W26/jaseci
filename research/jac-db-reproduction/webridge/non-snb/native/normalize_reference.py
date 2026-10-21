"""Original-schedule correctness/reference evidence, separate from the RTT matrix."""
import pathlib,json,statistics,hashlib,collections
R=pathlib.Path(__file__).resolve().parent;W=R.parents[1];L=R.parent/'littlex'
select=json.loads((R/'latency-selections.json').read_text());out=[]
logs={v:list(map(json.loads,(R/'tpcc-gates'/v/'rows.jsonl').read_text().splitlines()))for v in ['baseline','final']}
assert len(logs['baseline'])==len(logs['final'])==900
for a,b in zip(logs['baseline'],logs['final']):
    for k in ['index','warmup','transaction','ok','rollback']:assert a[k]==b[k],(a['index'],k)
    if a['rollback']:
        for k in ['code','message']:assert a['result']['error'][k]==b['result']['error'][k]
        assert a['result']['error']['message']=='item not found'
    else:assert a['result']==b['result'],a['index']
paired=json.loads((R/'tpcc-gates/paired-state-verification.json').read_text());assert all(x['raw_equal']and x['canonical_equal']for phase in paired.values()for x in phase.values())
model=R/'tpcc-gates/baseline/independent-model-verification.json';assert json.loads(model.read_text())['status']=='PASS'
for v,rows in logs.items():
    p=R/'tpcc-gates'/v;summary=json.loads((p/'summary.json').read_text());assert summary['PASS']and all(summary['checks'].values());measured=[x for x in rows if not x['warmup']];assert len(measured)==800
    out.append({'family':'tpcc','workload':'original900','arm':'jac_original'if v=='baseline'else'jac_final','status':'accepted','measurement_role':'original-plan correctness/reference; separate from controlled representative RTT matrix','request_n':900,'warmup_n':100,'warmup_count':100,'sample_n':800,'measured_count':800,'outcomes':dict(collections.Counter('rollback'if x['rollback']else x['transaction']['kind']for x in rows)),'timer':'HTTP_client_wall_ms','observed_client_median_ms':statistics.median(x['client_ms']for x in measured),'transport':'direct PostgreSQL Unix socket; no injected latency proxy','artifact':str((p/'summary.json').relative_to(W)),'requests_artifact':str((p/'rows.jsonl').relative_to(W)),'requests_sha256':hashlib.sha256((p/'rows.jsonl').read_bytes()).hexdigest(),'gates':{'source_plan900':True,'every_business_result_equal_between_native_versions':True,'rollback_comparison':'Exact error code/message; source-version-specific traceback retained raw','independent_model_artifact':str(model.relative_to(W)),'full_eight_relation_initial_final_state_equality_artifact':str((R/'tpcc-gates/paired-state-verification.json').relative_to(W))}})
for name in select['references']:
    path=R/name;verification=path.parent/'independent-offline-verification.json';assert json.loads(verification.read_text())['PASS']
    for s in json.loads(path.read_text()):
        assert s['method']=='reference'and not s['instrumented']and s['delay_ms']==0;p=R/s['path'];n=1000 if s['workload']=='W3'else 500;assert s['n']==n and s['warm']==110
        row={'family':'littlex','workload':'mixed'if s['workload']=='W3'else s['operation'],'tweets_per_user':int(s['tier'][1:]),'arm':'jac_original'if s['variant']=='baseline'else'jac_final','status':'accepted','measurement_role':'original reference schedule; separate from RTT matrix','request_n':s['warm']+s['n'],'warmup_n':s['warm'],'warmup_count':s['warm'],'sample_n':s['n'],'measured_count':s['n'],'timer':'HTTP_client_wall_ms','observed_client_median_ms':s['client_median_ms'],'observed_server_median_ms':s['server_median_ms'],'transport':'shared PostgreSQL proxy with zero injected delay','measured_operation_counts':s['measured_operation_counts'],'artifact':str((p/'summary.json').relative_to(W)),'requests_artifact':str((p/('rows.chunks.json'if(p/'rows.chunks.json').exists()else'rows.jsonl.gz')).relative_to(W)),'logical_rows_path':str((p/'rows.jsonl.gz').relative_to(W)),'gates':{'every_request_source_oracle':s['all_request_oracles_verified'],'full_final_state':s['state']['exact_business_state_verified'],'independent_offline_artifact':str(verification.relative_to(W))}}
        if s['workload']=='W3':row['write_percent']=int(s['operation'])
        out.append(row)
def key(x):return tuple((k,x[k])for k in ['family','workload','tweets_per_user','write_percent','arm']if k in x)
expected=[]
for e in json.loads((L/'plans/manifest.json').read_text()):
    if e['method']!='reference':continue
    for arm in ['jac_original','jac_final']:
        x={'family':'littlex','workload':'mixed'if e['workload']=='W3'else e['operation'],'tweets_per_user':int(e['tier'][1:]),'arm':arm}
        if e['workload']=='W3':x['write_percent']=int(e['operation'])
        expected.append(x)
expected +=[{'family':'tpcc','workload':'original900','arm':a}for a in ['jac_original','jac_final']];seen={key(x)for x in out};assert len(seen)==len(out)
(R/'normalized-reference.json').write_text(json.dumps(out,indent=2)+'\n');(R/'normalized-reference-coverage.json').write_text(json.dumps({'required':42,'accepted':len(out),'failed_primary':0,'accepted_request_n':sum(x['request_n']for x in out),'accepted_warmup_count':sum(x['warmup_count']for x in out),'accepted_measured_count':sum(x['measured_count']for x in out),'pending':[x for x in expected if key(x)not in seen],'scope':'Original schedules and source-state correctness references are independent of the 162 native RTT cells.'},indent=2)+'\n');print(len(out),'accepted references of42')
