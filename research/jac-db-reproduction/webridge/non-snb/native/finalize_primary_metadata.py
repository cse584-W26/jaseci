"""Index completed primary collection, actual shutdown proofs and portable raw joins."""
import pathlib,json,hashlib,datetime,shutil
R=pathlib.Path(__file__).resolve().parent;W=R.parents[1];L=R.parent/'littlex';O=R/'primary-rtt-completion';O.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
lat=read(R/'normalized-rtt-latency.json');refs=read(R/'normalized-rtt-reference.json');assert len(lat)==162 and len(refs)==42
stops={}
for history in [R/'launch-history',L/'native/launch-history']:
 for p in history.glob('*/stop-verification.json'):
  x=read(p);stops[x['owned_pid']]=(p,x)
checks=[];proofdir=O/'shutdown-proofs';proofdir.mkdir(exist_ok=True)
for kind,rows in [('latency',lat),('references',refs)]:
 for x in rows:
  assert x['status']=='accepted'and x['timer']=='compactSQLroundtrip_sum_ms'
  for k in ['requests_artifact','compact_trace_artifact','compact_trace_catalog_artifact','compact_trace_receipt_artifact','compact_trace_completeness_artifact']:assert(W/x[k]).is_file(),(k,x[k])
  folder=(W/x['requests_artifact']).parent;launch=read(folder/'launch.json');pid=launch['pid'];p,stop=stops[pid];assert stop['process_absent_or_zombie']and stop['database_sessions']==[];assert stop['owned_database']==launch['database']
  target=proofdir/(str(pid)+'.json');shutil.copy2(p,target)
  receipt=read(W/x['compact_trace_receipt_artifact']);status=read(W/x['compact_trace_completeness_artifact']);assert receipt['stopped']and not receipt.get('errors')and not any(status['pending_groups'].values());assert receipt['client_received_bytes']==receipt['client_forwarded_bytes']and receipt['server_received_bytes']==receipt['server_delivered_bytes']
  settings=read(folder/'settings-restored.json');assert settings['exact_prior_restored']
  checks.append({'method':kind,'family':x['family'],'workload':x['workload'],'arm':x['arm'],'delay_ms':x['delay_ms'],'sample_n':x['sample_n'],'warmup_n':x['warmup_n'],'requests_artifact':x['requests_artifact'],'shutdown_proof':str(target.relative_to(W)),'original_shutdown_proof':str(p.relative_to(W)),'owned_pid':pid,'shutdown_wall_ns':stop['verified_wall_ns'],'process_absence_and_no_owned_database_sessions':True,'settings_exactly_restored':True,'proxy_stopped_and_bytes_complete':True})
for home in [R/'baseline',R/'final',L/'native/baseline',L/'native/final']:assert not(home/'service.pid').exists(),home
ports=[]
for table in ['/proc/net/tcp','/proc/net/tcp6']:
 for line in pathlib.Path(table).read_text().splitlines()[1:]:
  a=line.split();port=int(a[1].split(':')[1],16)
  if a[3]=='0A'and port in [18132,18134,18532]:ports.append({'table':table,'port':port})
assert not ports,ports
result={'PASS':True,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'latency_cells':len(lat),'reference_cells':len(refs),'latency_measured_requests':sum(x['sample_n']for x in lat),'latency_warmup_requests':sum(x['warmup_n']for x in lat),'reference_measured_requests':sum(x['sample_n']for x in refs),'reference_warmup_requests':sum(x['warmup_n']for x in refs),'all_shutdown_proofs_indexed':True,'owned_service_pidfiles_absent':True,'owned_HTTP_and_proxy_ports_not_listening':[18132,18134,18532],'primary_timer':'compactSQLroundtrip_sum_ms','scope':'Metadata/receipt verification. Root raw verifier independently joins every compact raw exchange to every request and recomputes RTT/counts.','cells':checks}
(O/'completion.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items()if k!='cells'})
