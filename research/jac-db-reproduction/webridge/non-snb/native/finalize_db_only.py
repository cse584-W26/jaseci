"""Verify source oracles and PostgreSQL phase totals for a direct-transport case pair."""
import pathlib,sys,json,subprocess,statistics,collections,gzip,hashlib
R=pathlib.Path(__file__).resolve().parent;sys.path[:0]=[str(R/'db-time-analysis'),str(R.parent)];from analyze import parse,bucket
from measurement_lease import lease
name=sys.argv[1];O=R/name;D=R/'db-time-analysis/direct-zero';D.mkdir(exist_ok=True)
with lease('Verify native direct DB-time case '+name,O/'verification-lease.json'):
 subprocess.run([sys.executable,str(R/'verify_littlex.py'),'--input',str(O)],check=True)
 result=[];summary=[]
 for cell in json.loads((O/'summary.json').read_text()):
  folder=R/cell['path'];rows=[json.loads(x)for x in(folder/'db-times.jsonl').read_text().splitlines()];assert len(rows)==cell['n']
  for row in rows:
   iteration=int(row['request_tag'].rsplit('-',1)[1])-cell['warm']
   # Raw plan iteration resets at the measured phase; request tag uses total sequence.
   path=folder/('profile-'+str(iteration)+'.sql.log.gz');raw=path.read_bytes();events=parse(gzip.decompress(raw).decode());assert events==row['phase_events'];assert all(e['pid']in row['owned_backend_pids']for e in events)
   assert row['db_server_ms']==sum(e['ms']for e in events);assert row['SQL_count']==sum(e['phase']in('execute','statement')for e in events)
   assert all(e['category']!='unclassified'for e in events)
   phase=collections.defaultdict(float);cats=collections.defaultdict(float);b=collections.defaultdict(float)
   for e in events:phase[e['phase']]+=e['ms'];cats[e['category']]+=e['ms'];b[bucket(e['category'])]+=e['ms']
   result.append({'request_tag':row['request_tag'],'variant':cell['variant'],'tier':cell['tier'],'workload':cell['workload'],'operation':cell['operation'],'db_server_ms':row['db_server_ms'],'SQL_count':row['SQL_count'],'phase_ms':dict(phase),'category_ms':dict(cats),'bucket_ms':dict(b),'phase_events':events,'owned_backend_pids':row['owned_backend_pids'],'raw_log':str(path.relative_to(R)),'raw_compressed_sha256':hashlib.sha256(raw).hexdigest()})
  local=result[-len(rows):];key=('littlex-mixed-t200-w'+cell['operation']if cell['workload']=='W3'else'littlex-'+cell['operation']+'-'+cell['tier'])
  summary.append({'case_id':key,'arm':'jac_original'if cell['variant']=='baseline'else'jac_final','n':len(rows),'median_db_server_ms':statistics.median(r['db_server_ms']for r in local),'sql_count_distribution':dict(collections.Counter(str(r['SQL_count'])for r in local)),'median_phase_ms':{p:statistics.median(r['phase_ms'].get(p,0)for r in local)for p in ['parse','bind','execute','statement']},'median_bucket_ms':{b:statistics.median(r['bucket_ms'].get(b,0)for r in local)for b in ['transaction','read','write','identity']},'transport':'direct Unix socket','byte_proxy_used':False,'packet_logger_used':False,'all_source_response_and_full_state_oracles_verified':True,'artifact':name+'/independent-offline-verification.json'})
 (O/'db-server-times-verified.json').write_text(json.dumps({'arms':summary,'requests':result},indent=2)+'\n')
 sp=D/'selections.json';selected=json.loads(sp.read_text())if sp.exists()else[];assert name not in selected;selected.append(name);sp.write_text(json.dumps(selected,indent=2)+'\n')
 allarms=[];allrequests=[]
 for selection in selected:
  v=json.loads((R/selection/'db-server-times-verified.json').read_text());allarms+=v['arms'];allrequests+=v['requests']
 assert len({(x['case_id'],x['arm'])for x in allarms})==len(allarms)
 (D/'summary.json').write_text(json.dumps({'scope':'Direct Unix socket PostgreSQL logged server parse/bind/execute/simple-statement elapsed phases; no byte proxy or packet logger; server result production and waits included, not CPU-only.','arms':allarms,'accepted_arms':len(allarms),'required_arms':40,'measured_requests':len(allrequests)},indent=2)+'\n');(D/'requests.json').write_text(json.dumps(allrequests,indent=2)+'\n')
 print(len(allarms),'direct native DB-time arms accepted')
