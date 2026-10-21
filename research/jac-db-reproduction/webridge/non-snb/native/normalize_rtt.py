"""Portable primary per-request database-exchange RTT table and same-run count evidence."""
import pathlib,json,collections
def publish(path,data):
 tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)
R=pathlib.Path(__file__).resolve().parent;W=R.parents[1];S=json.loads((R/'rtt-selections.json').read_text());lat=[];refs=[]
for kind,target in [('latency',lat),('references',refs)]:
 for name in S[kind]:
  for x in json.loads((R/name/'rtt-summary.json').read_text()):
   assert x['status']=='accepted'and x['timer']=='compactSQLroundtrip_sum_ms'
   home=pathlib.Path(x['artifact']).parent/('delay-'+str(x['delay_ms'])+'ms')/'trace'
   x.update(compact_trace_artifact=str(home/'flights.jsonl'),compact_trace_catalog_artifact=str(home/'sql-catalog.json'),compact_trace_receipt_artifact=str(home/'receipt.json'),compact_trace_completeness_artifact=str(home/'compact-status.json'))
   if kind=='references':x.update(request_n=x['sample_n']+x['warmup_n'],warmup_count=x['warmup_n'],measured_count=x['sample_n'],measurement_role='Original reference plan; primary summed complete database-exchange RTT')
   target.append(x)
keys=['family','workload','tweets_per_user','write_percent','arm','delay_ms']
def key(x):return tuple((k,x[k])for k in keys if k in x)
for rows,name in [(lat,'normalized-rtt-latency.json'),(refs,'normalized-rtt-reference.json')]:
 assert len({key(x)for x in rows})==len(rows);publish(R/name,sorted(rows,key=lambda x:str(key(x))))
required=[x for x in json.loads((R.parent/'coverage-contract.json').read_text())['cells']if x['arm']in('jac_original','jac_final')];seen={key(x)for x in lat}
publish(R/'normalized-rtt-coverage.json',{'accepted_latency_cells':len(lat),'required_latency_cells':162,'pending':[x for x in required if key(x)not in seen],'accepted_reference_cells':len(refs),'required_reference_cells':42,'primary_timer':'Per-request sum of actual completed PostgreSQL database exchanges; includes prepare-only/control RTT, separately classified from SQL commands.','selection':S})
cycles={}
for r in lat:
 case=('tpcc-'+r['workload']if r['family']=='tpcc'else'littlex-mixed-t200-w'+str(r['write_percent'])if r['workload']=='mixed'else'littlex-'+r['workload']+'-t'+str(r['tweets_per_user']))
 a=cycles.setdefault(case,{}).setdefault(r['arm'],{'display':'','artifact':'non-snb/native/rtt-cycle-evidence.json','observations':[]})
 a['observations'].append({'delay_ms':r['delay_ms'],'sample_n':r['sample_n'],'sql_command_count_distribution':r['sql_command_count_distribution'],'response_exchange_count_distribution':r['response_exchange_count_distribution'],'median_sum_rtt_ms':r['median_ms'],'artifact':r['requests_artifact'],'scope':'Counts and RTTs from the same primary timing requests across all database connections; preparation/control count as exchanges, not SQL commands.'})
for arms in cycles.values():
 for a in arms.values():
  a['observations'].sort(key=lambda x:x['delay_ms']);a['display']='; '.join(str(o['delay_ms'])+'ms SQL'+str(o['sql_command_count_distribution'])+' /exchanges'+str(o['response_exchange_count_distribution'])for o in a['observations'])
publish(R/'rtt-cycle-evidence.json',cycles);print(len(lat),'RTT latency cells;',len(refs),'RTT references')
