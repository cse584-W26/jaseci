#!/usr/bin/env python3
"""Attribute existing compact PRIMARY RTT; no database requests or P_S inference."""
import argparse,collections,gzip,hashlib,json,math,pathlib,re,statistics,sys
N=pathlib.Path(__file__).resolve().parents[2];R=N.parent;sys.path.insert(0,str(N))
from measurement_lease import lease

def resolve(s):
 p=pathlib.Path(s)
 if p.is_absolute():return p
 return (R/p) if str(p).startswith('non-snb/') else N/p

def load(p):
 p=resolve(p)
 with (gzip.open(p,'rt')if p.suffix=='.gz'else p.open())as f:
  return [json.loads(s)for s in f if s.strip()]if p.name.endswith(('.jsonl','.jsonl.gz'))else json.load(f)

def category(sql):
 s=' '.join(sql.upper().split())
 if s.startswith('CALL '):return 'CALL_inclusive'
 if s.startswith(('BEGIN','COMMIT','ROLLBACK','SAVEPOINT','RELEASE SAVEPOINT','SET ','START TRANSACTION')):return 'transaction_or_session'
 if s.startswith(('INSERT ','UPDATE ','DELETE ','REPLACE ')):return 'write'
 if s.startswith(('CREATE ','ALTER ','DROP ')):return 'schema_DDL'
 if any(t in s for t in ['IDENTITY_USERS','IDENTITY_LOOKUPS']):return 'identity'
 if 'GRAPH_TYPES' in s:return 'type_registry'
 if 'KV_STATE' in s:return 'schema_guard'
 if s.startswith(('SHOW ','DEALLOCATE ','DISCARD ','SELECT VERSION','SELECT @@','SELECT 1')):return 'driver_control'
 # SQL stored inside a wrapper function still performs a read. Preserve exact SQL below.
 if s.startswith(('SELECT ','WITH ')):return 'business_SELECT'
 return 'other_SQL'

def wanted(c):
 return (c['family']=='tpcc'and c['workload']=='payment_name_GC')or(c['family']=='littlex'and c.get('tweets_per_user')in(20,200)and(c['workload']=='feed'or(c['workload']=='mixed'and c.get('write_percent',c.get('write_pct'))==15)))

def distributions(rows,key):return dict(collections.Counter(str(r[key])for r in rows))

def process(cell):
 native=cell['arm'].startswith('jac_');rows=load(cell['requests_artifact']);assert isinstance(rows,list)
 rows=[r for r in rows if not r['warmup']]
 summary=load(cell['rtt_summary_artifact'])if not native else None
 catpath=cell.get('compact_trace_catalog_artifact')if native else summary['sql_catalog']
 catalog=load(catpath);assert isinstance(catalog,dict)
 for sid,sql in catalog.items():
  digest=hashlib.sha256((' '.join(sql.split())if native else sql).encode()).hexdigest()
  assert sid==(digest[:16]if native else digest),(sid,'SQL catalog hash mismatch')
 requests=[];sql_stats=collections.defaultdict(list);sql_counts=collections.Counter()
 for row in rows:
  groups=collections.defaultdict(float);counts=collections.Counter();ops=[]
  operations=row['calls']if native else row['operations']
  for op in operations:
   ids=op['SQL_ids']if native else[op['sql_sha256']]
   value=op['roundtrip_ms']if native else op['rtt_ms']
   assert value>=0
   if not ids:
    cat='prepare_only_exchange';sqlkey='prepare:'+','.join(op.get('parse_SQL_ids',[]))
   elif len(ids)>1:
    # Do not invent how a pipelined flight's inclusive RTT splits across SQL.
    cat='multi_SQL_exchange';sqlkey='multi:'+','.join(ids)
   else:
    sqlkey=ids[0];assert sqlkey in catalog;cat=category(catalog[sqlkey])
   groups[cat]+=value;counts[cat]+=1;sql_stats[sqlkey].append(value);sql_counts[sqlkey]+=1
   ops.append({'category':cat,'sql_id':sqlkey,'rtt_ms':value,'command_or_flight':op.get('command_id',op.get('frontend_received_ns'))})
  total=row['sum_rtt_ms']if native else row['summed_db_call_rtt_ms']
  assert math.isclose(sum(groups.values()),total,rel_tol=1e-12,abs_tol=1e-8),(cell,row.get('iteration'),'category sum')
  assert len(operations)==row['response_exchange_count'if native else'command_count']
  requests.append({'iteration':row['iteration'],'operation':row.get('operation',row.get('op')),'total_ms':total,'category_ms':dict(groups),'category_exchanges':dict(counts),'source_native_SQL_category_counts':row.get('SQL_category_counts'),'source_native_SQL_category_RTT_ms':row.get('SQL_category_roundtrip_ms'),'SQL_command_count':row.get('sql_command_count',row.get('command_count')),'operations':ops})
 assert len(requests)==cell.get('sample_n',cell.get('measured_count')),(len(requests),cell)
 assert math.isclose(statistics.median(r['total_ms']for r in requests),cell['median_ms'],rel_tol=1e-9,abs_tol=1e-7)
 cats=sorted({c for r in requests for c in r['category_ms']});mean_total=statistics.mean(r['total_ms']for r in requests)
 categories={c:{'mean_ms':statistics.mean(r['category_ms'].get(c,0)for r in requests),'median_ms':statistics.median(r['category_ms'].get(c,0)for r in requests),'min_ms':min(r['category_ms'].get(c,0)for r in requests),'max_ms':max(r['category_ms'].get(c,0)for r in requests),'mean_exchanges':statistics.mean(r['category_exchanges'].get(c,0)for r in requests),'exchange_distribution':dict(collections.Counter(r['category_exchanges'].get(c,0)for r in requests))}for c in cats}
 assert math.isclose(sum(x['mean_ms']for x in categories.values()),mean_total,rel_tol=1e-12,abs_tol=1e-8)
 concrete=[]
 for sid,values in sql_stats.items():
  concrete.append({'sql_id':sid,'sql':catalog.get(sid),'exchange_n':len(values),'mean_ms_per_request':sum(values)/len(requests),'median_ms_per_exchange':statistics.median(values),'category':category(catalog[sid])if sid in catalog else sid.split(':')[0]})
 concrete.sort(key=lambda x:x['mean_ms_per_request'],reverse=True)
 operation_groups={}
 for op in sorted({str(r['operation'])for r in requests}):
  rr=[r for r in requests if str(r['operation'])==op];operation_groups[op]={'n':len(rr),'mean_total_ms':statistics.mean(r['total_ms']for r in rr),'median_total_ms':statistics.median(r['total_ms']for r in rr),'category_mean_ms':{c:statistics.mean(r['category_ms'].get(c,0)for r in rr)for c in cats}}
 return {'by_operation':operation_groups,'cell':{k:cell[k]for k in ['family','workload','arm','delay_ms','tweets_per_user','write_percent','write_pct']if k in cell},'engine':'PostgreSQL'if native else'MySQL5.7','n':len(requests),'median_total_ms':cell['median_ms'],'mean_total_ms':mean_total,'categories':categories,'concrete_SQL':concrete,'requests_artifact':cell['requests_artifact'],'compact_trace_artifact':cell['compact_trace_artifact'],'sql_catalog':str(resolve(catpath)),'category_sums_equal_request_RTT':True,'category_means_equal_mean_total':True,'requests':requests}

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--allow-incomplete',action='store_true');p.add_argument('--native-input',type=pathlib.Path,default=N/'native/normalized-rtt-latency.json');p.add_argument('--extra-native-input',type=pathlib.Path);p.add_argument('--results',type=pathlib.Path,help='Canonical results.json; uses latency only, never references');a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 with lease('PRIMARY compact RTT category attribution; offline only',out/'lease.json'):
  paths=[a.native_input,N/'tpcc/normalized-rtt-latency.json',N/'littlex/normalized-rtt-results.json'];allcells=[];coverage=[]
  for path in paths:
   payload=load(path);cells=payload if isinstance(payload,list)else payload['cells'];cells=[c for c in cells if c.get('method','latency')=='latency'];coverage.append({'source':str(path),'terminal_latency_cells':len(cells)});allcells.extend(cells)
  if not a.allow_incomplete and not a.results:assert[len(load(paths[0])),len(load(paths[1])),len([c for c in load(paths[2])['cells']if c['method']=='latency'])]==[162,126,360],coverage
  if a.extra_native_input:
   extra=load(a.extra_native_input);assert isinstance(extra,list);allcells.extend(extra);coverage.append({'source':str(a.extra_native_input),'terminal_latency_cells':len(extra)})
  if a.results:
   payload=load(a.results);allcells=payload['latency'];coverage=[{'source':str(a.results),'terminal_latency_cells':len(allcells)}]
   if not a.allow_incomplete:assert len(allcells)==648
  keys=[(c['family'],c['workload'],c.get('tweets_per_user'),c.get('write_percent'),c['arm'],c['delay_ms'])for c in allcells];assert len(keys)==len(set(keys)),'Duplicate latency cell keys'
  selected=[c for c in allcells if wanted(c)];results=[];unavailable=[]
  for c in selected:
   if c['status']!='accepted':unavailable.append(c);continue
   results.append(process(c))
  result={'metric':'PRIMARY sum of complete DB-call RTT, including execution and communication; excludes application gaps','scope':'Existing compact capture only. CALL is one inclusive exchange; no nested P_S time added. Different engines/transport are explicit. Concrete SQL hashes are checked against catalogs. Category medians are not additive; only means reconcile.','source_coverage':coverage,'cells':results,'unavailable':unavailable}
  (out/'attribution.json').write_text(json.dumps(result,indent=2)+'\n')
  lines=['# Measured compact database-call RTT attribution','',result['scope'],'','|Case|Arm|Delay ms|n|Median RTT ms|Mean RTT ms|Largest category by mean|','|---|---|---:|---:|---:|---:|---|']
  for x in results:
   c=x['cell'];dominant=max(x['categories'],key=lambda k:x['categories'][k]['mean_ms']);label=c['workload']+str(c.get('tweets_per_user',''))+' w'+str(c.get('write_percent',c.get('write_pct','')))
   lines.append(f"|{label}|{c['arm']}|{c['delay_ms']}|{x['n']}|{x['median_total_ms']:.3f}|{x['mean_total_ms']:.3f}|{dominant}: {x['categories'][dominant]['mean_ms']:.3f} ms|")
  lines+=['','Each row is independently gated against the normalized primary median and request count. Per-request category sums and aggregate category means reconcile exactly. Raw SQL and their measured exchange costs are in attribution.json. These measurements identify costs; they do not establish an optimizer cause.','',f'Unavailable selected cells: {len(unavailable)}; their stage evidence remains in JSON.']
  (out/'FINDINGS.md').write_text('\n'.join(lines)+'\n');print(len(results),'accepted selected cells')
if __name__=='__main__':main()
