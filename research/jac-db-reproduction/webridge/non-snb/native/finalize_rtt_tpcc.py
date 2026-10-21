"""Full TPC-C result/eight-relation-state gates and actual compact DB RTT verification."""
import pathlib,json,sys,subprocess,statistics,collections,gzip,hashlib
R=pathlib.Path(__file__).resolve().parent;W=R.parents[1];sys.path[:0]=[str(R),str(R.parent)]
from rtt_sql import category
from measurement_lease import lease
O=R/sys.argv[1]
def sha_raw(p):
 h=hashlib.sha256()
 with gzip.open(p,'rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
with lease('Verify native TPC-C compact RTT '+O.name,O/'verification-lease.json'):
 accepted=[];proof=[]
 for home in sorted(O.glob('delay-*ms')):
  receipt=json.loads((home/'trace/receipt.json').read_text());status=json.loads((home/'trace/compact-status.json').read_text());assert receipt['stopped']and not receipt.get('errors')and not any(status['pending_groups'].values());assert receipt['client_received_bytes']==receipt['client_forwarded_bytes']and receipt['server_received_bytes']==receipt['server_delivered_bytes']
  flights=[json.loads(x)for x in(home/'trace/flights.jsonl').read_text().splitlines()];assert len(flights)==status['flight_count'];catalog=json.loads((home/'trace/sql-catalog.json').read_text());bytag=collections.defaultdict(list)
  for f in flights:
   assert f['terminal_backend_type']=='Z'and f['reply_delivered_ns']>=f['reply_complete_received_ns']>=f['frontend_received_ns'];assert f['roundtrip_ms']==(f['reply_delivered_ns']-f['frontend_received_ns'])/1e6;assert f['backend_pid']is not None and len(f['SQL_ids'])==f['SQL_count']<=1;bytag[f['request_tag']].append(f)
  for cell in json.loads((O/'summary.json').read_text()):
   if cell['delay_ms']!=int(home.name[6:-2]):continue
   folder=R/cell['path'];reference=cell['method']=='reference';expected_dir=R/'tpcc-gates'/cell['variant']if reference else R/'tpcc-timing/delay-0ms'/cell['variant']/cell['label'];expected_rows=[json.loads(x)for x in(expected_dir/'rows.jsonl').read_text().splitlines()];rows=[json.loads(x)for x in(folder/'rows.jsonl').read_text().splitlines()];assert len(rows)==len(expected_rows)==cell['warm']+cell['n']
   expected_manifest=json.loads((expected_dir/('after-state'if reference else'after40-state')/'manifest.json').read_text());manifest=json.loads((folder/'after-state/manifest.json').read_text());assert set(manifest)==set(expected_manifest)
   for table,d in manifest.items():
    e=expected_manifest[table];assert(d['rows'],d['sha256'],d['canonical_cents_sha256'])==(e['rows'],e['sha256'],e['canonical_cents_sha256']),(cell['label'],table,'state mismatch')
    assert sha_raw(folder/'after-state'/pathlib.Path(d['path']).name)==d['sha256'];assert sha_raw(folder/'after-state'/pathlib.Path(d['canonical_cents_path']).name)==d['canonical_cents_sha256']
   requests=[]
   for row,expected in zip(rows,expected_rows):
    assert row['ok']==expected['ok']and row['rollback']==expected['rollback'];assert hashlib.sha256(row['response_text'].encode()).hexdigest()==row['response_sha256']
    if row['rollback']:
     for k in ['code','message']:assert row['result']['error'][k]==expected['result']['error'][k]
    else:assert row['result']==expected['result'],(row['request_tag'],'result mismatch')
    fs=bytag.pop(row['request_tag'],[]);assert fs and not any(f['pipelined_before_prior_reply']for f in fs);counter=collections.Counter();times=collections.defaultdict(float)
    for f in fs:
     for sid in f['SQL_ids']:
      c=category(catalog[sid],family='tpcc');assert c!='unclassified',(sid,catalog[sid]);counter[c]+=1;times[c]+=f['roundtrip_ms']
    total=sum(f['roundtrip_ms']for f in fs);driver=sum(f['roundtrip_ms']for f in fs if not f['SQL_count']);requests.append({'request_tag':row['request_tag'],'warmup':row['warmup'],'iteration':row['iteration'],'sum_rtt_ms':total,'SQL_roundtrip_ms':total-driver,'prepare_and_control_roundtrip_ms':driver,'sql_command_count':sum(f['SQL_count']for f in fs),'response_exchange_count':len(fs),'SQL_category_counts':dict(counter),'SQL_category_roundtrip_ms':dict(times),'database_pids':sorted({f['backend_pid']for f in fs}),'calls':fs})
   measured=[r for r in requests if not r['warmup']];warm_pids={pid for r in requests if r['warmup']for pid in r['database_pids']};measured_pids={pid for r in measured for pid in r['database_pids']};assert len(measured)==cell['n'];assert json.loads((folder/'settings-restored.json').read_text())['exact_prior_restored'];assert cell['service_stopped']and json.loads((home/'cleanup.json').read_text())['proxy_stopped'];(folder/'rtt-requests.json').write_text(json.dumps(requests,indent=2)+'\n')
   accepted.append({'family':'tpcc','workload':cell['label'],'arm':'jac_original'if cell['variant']=='baseline'else'jac_final','delay_ms':cell['delay_ms'],'status':'accepted','median_ms':statistics.median(r['sum_rtt_ms']for r in measured),'timer':'compactSQLroundtrip_sum_ms','measurement_boundary':'Sum of all complete PostgreSQL exchanges from proxy frontend receive to ReadyForQuery delivery; all DB connections; prepare/control RTT included separately from SQL commands.','sample_n':len(measured),'warmup_n':cell['warm'],'sql_command_count_distribution':dict(collections.Counter(str(r['sql_command_count'])for r in measured)),'response_exchange_count_distribution':dict(collections.Counter(str(r['response_exchange_count'])for r in measured)),'requests_artifact':str((folder/'rtt-requests.json').relative_to(W)),'artifact':str((O/'rtt-summary.json').relative_to(W)),'gates':{'every_source_result':True,'all_eight_relation_full_state':True,'raw_and_exact_cents_state_hashes':True,'all_connections_captured':True,'complete_response_barriers':True,'cleanup_and_settings_restored':True,'validated_original_model_reference':str(expected_dir.relative_to(W))},'warm_database_pids':sorted(warm_pids),'measured_database_pids':sorted(measured_pids),'new_backend_pids_during_measured':sorted(measured_pids-warm_pids),'connection_initialization_scope':'SQL initialization commands inside a request are included; PostgreSQL startup/authentication handshake is not a SQL exchange.','secondary_HTTP_client_median_ms':cell['client_median_ms'],'secondary_application_server_median_ms':cell['server_median_ms'],'method':cell['method']});proof.append({'path':cell['path'],'expected_state_reference':str(expected_dir.relative_to(W)),'all_eight_tables_and_payload_hashes_equal':True,'all_results_equal':True})
  assert not[k for k in bytag if k.startswith(('request-','warmup-'))];(home/'outside-request-flights.json').write_text(json.dumps(bytag,indent=2)+'\n')
 (O/'independent-offline-verification.json').write_text(json.dumps({'PASS':True,'cells':proof},indent=2)+'\n');(O/'rtt-summary.json').write_text(json.dumps(accepted,indent=2)+'\n');p=R/'rtt-selections.json';s=json.loads(p.read_text())if p.exists()else{'latency':[],'references':[]};k='references'if accepted[0]['method']=='reference'else'latency';assert O.name not in s[k];s[k].append(O.name);p.write_text(json.dumps(s,indent=2)+'\n');subprocess.run([sys.executable,str(R/'normalize_rtt.py')],check=True);print(len(accepted),'TPC-C compact RTT cells verified')
