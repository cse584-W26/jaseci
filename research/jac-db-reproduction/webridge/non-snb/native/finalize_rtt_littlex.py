"""Independently verify source results/state and compact complete-response SQL RTTs."""
import pathlib,json,sys,subprocess,statistics,collections,hashlib
R=pathlib.Path(__file__).resolve().parent;sys.path[:0]=[str(R),str(R.parent)]
from jsonl_chunks import rows_lines,export
from rtt_sql import category
from measurement_lease import lease
O=R/sys.argv[1]
with lease('Verify native compact RTT '+O.name,O/'verification-lease.json'):
 for cell in json.loads((O/'summary.json').read_text()):
  folder=R/cell['path']
  if cell['method']=='reference'and cell['operation']=='feed'and not(folder/'rows.chunks.json').exists():export(folder)
 subprocess.run([sys.executable,str(R/'verify_littlex.py'),'--input',str(O)],check=True)
 accepted=[];allrequests=[]
 for delayhome in sorted(O.glob('delay-*ms')):
  status=json.loads((delayhome/'trace/compact-status.json').read_text());assert not any(status['pending_groups'].values()),status
  receipt=json.loads((delayhome/'trace/receipt.json').read_text());assert receipt['stopped']and not receipt.get('errors');assert receipt['client_received_bytes']==receipt['client_forwarded_bytes']and receipt['server_received_bytes']==receipt['server_delivered_bytes']
  flights=[json.loads(x)for x in(delayhome/'trace/flights.jsonl').read_text().splitlines()];assert len(flights)==status['flight_count'];catalog=json.loads((delayhome/'trace/sql-catalog.json').read_text());bytag=collections.defaultdict(list)
  for f in flights:
   assert f['terminal_backend_type']=='Z'and f['reply_delivered_ns']>=f['reply_complete_received_ns']>=f['frontend_received_ns'];assert f['roundtrip_ms']==(f['reply_delivered_ns']-f['frontend_received_ns'])/1e6;assert f['backend_pid']is not None
   assert len(f['SQL_ids'])==f['SQL_count']<=1
   for sid in f['SQL_ids']+f['parse_SQL_ids']:assert sid in catalog
   bytag[f['request_tag']].append(f)
  for cell in json.loads((O/'summary.json').read_text()):
   if cell['delay_ms']!=int(delayhome.name[6:-2]):continue
   folder=R/cell['path'];requests=[]
   for row in map(json.loads,rows_lines(folder)):
    fs=bytag.pop(row['request_tag'],[]);assert fs,(row['request_tag'],'no completed DB flights')
    assert not any(f['pipelined_before_prior_reply']for f in fs),'Pipeline requires separately stated overlapping-call sum semantics'
    sql_n=sum(f['SQL_count']for f in fs);driver=sum(f['roundtrip_ms']for f in fs if not f['SQL_count']);total=sum(f['roundtrip_ms']for f in fs);cats=collections.defaultdict(float);counter=collections.Counter()
    for f in fs:
     for sid in f['SQL_ids']:
      c=category(catalog[sid]);assert c!='unclassified',(sid,catalog[sid]);counter[c]+=1;cats[c]+=f['roundtrip_ms']
    item={'request_tag':row['request_tag'],'warmup':row['warmup'],'operation':row['operation'],'iteration':row['iteration'],'sum_rtt_ms':total,'SQL_roundtrip_ms':total-driver,'prepare_and_control_roundtrip_ms':driver,'sql_command_count':sql_n,'response_exchange_count':len(fs),'SQL_category_counts':dict(counter),'SQL_category_roundtrip_ms':dict(cats),'database_pids':sorted({f['backend_pid']for f in fs}),'calls':fs}
    requests.append(item)
   measured=[x for x in requests if not x['warmup']];warm_pids={pid for x in requests if x['warmup']for pid in x['database_pids']};measured_pids={pid for x in measured for pid in x['database_pids']};assert len(measured)==cell['n'];assert len(requests)-len(measured)==cell['warm'];(folder/'rtt-requests.json').write_text(json.dumps(requests,indent=2)+'\n')
   workload='mixed'if cell['workload']=='W3'else cell['operation'];x={'family':'littlex','workload':workload,'tweets_per_user':int(cell['tier'][1:]),'arm':'jac_original'if cell['variant']=='baseline'else'jac_final','delay_ms':cell['delay_ms'],'status':'accepted','median_ms':statistics.median(r['sum_rtt_ms']for r in measured),'timer':'compactSQLroundtrip_sum_ms','measurement_boundary':'Sum of complete database protocol exchanges from first frontend bytes received by proxy through ReadyForQuery bytes delivered to database client; all application database connections. Includes prepare-only/control exchanges; excludes HTTP/Python/Java time outside these exchanges.','sample_n':len(measured),'warmup_n':len(requests)-len(measured),'sql_command_count_distribution':dict(collections.Counter(str(r['sql_command_count'])for r in measured)),'response_exchange_count_distribution':dict(collections.Counter(str(r['response_exchange_count'])for r in measured)),'requests_artifact':str((folder/'rtt-requests.json').relative_to(R.parents[1])),'artifact':str((O/'rtt-summary.json').relative_to(R.parents[1])),'gates':{'all_source_results':True,'full_business_state':True,'all_connections_captured':True,'actual_complete_response_barriers':True,'settings_and_owned_cleanup':True,'source_oracle_verification':str((O/'independent-offline-verification.json').relative_to(R.parents[1]))},'warm_database_pids':sorted(warm_pids),'measured_database_pids':sorted(measured_pids),'new_backend_pids_during_measured':sorted(measured_pids-warm_pids),'connection_initialization_scope':'SQL initialization commands are included when inside a tagged request; PostgreSQL startup/authentication handshake is not a SQL exchange.','secondary_HTTP_client_median_ms':cell['client_median_ms'],'secondary_application_server_median_ms':cell['server_median_ms'],'method':cell['method']}
   if workload=='mixed':x['write_percent']=int(cell['operation'])
   accepted.append(x);allrequests+=measured
  # Remaining groups are explicitly outside a recorded HTTP request, including calibration/startup.
  (delayhome/'outside-request-flights.json').write_text(json.dumps({k:v for k,v in bytag.items()},indent=2)+'\n');assert not[k for k in bytag if k.startswith(('request-','warmup-'))],list(bytag)
 (O/'rtt-summary.json').write_text(json.dumps(accepted,indent=2)+'\n')
 selection=R/'rtt-selections.json';d=json.loads(selection.read_text())if selection.exists()else{'latency':[],'references':[]};method=accepted[0]['method'];key='latency'if method=='latency'else'references';assert O.name not in d[key];d[key].append(O.name);selection.write_text(json.dumps(d,indent=2)+'\n')
 subprocess.run([sys.executable,str(R/'normalize_rtt.py')],check=True)
 print(len(accepted),'compact RTT cells verified')
