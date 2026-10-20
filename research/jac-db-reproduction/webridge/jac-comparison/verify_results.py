"""Independent offline audit of matched-fixture native Jac request samples and SQL windows."""
import collections,gzip,hashlib,json,re,statistics
from pathlib import Path
H=Path(__file__).resolve().parent;input_file=H.parent/'alignment/small-diagnostic/input.json';input_spec=json.loads(input_file.read_text());expected={'forums':[{'forumId':x[0],'title':x[1],'postCount':x[2]} for x in input_spec['expected']]};out={'timing':{},'census':{},'checks':[]}
for arm in ['baseline','final']:
 for mode in ['timing','census']:
  root=H/mode/arm;rows=json.loads((root/'rows.json').read_text());lines=[json.loads(x) for x in (root/'rows.jsonl').read_text().splitlines()];assert rows==lines
  assert all(x['status']==200 and x['parity'] and x['result']==expected for x in rows);assert [x['iteration'] for x in rows]==list(range(len(rows)))
  for x in rows:assert abs(x['server_ms']-x['server_total_header_ms']-x['commit_header_ms'])<1e-9
  assert json.loads((root/'restored.json').read_text())['logging_restored']
  measured=[x for x in rows if not x['warmup']]
  if mode=='timing':
   assert len(rows)==40 and len(measured)==30 and len(rows)-len(measured)==10
   cpu=json.loads((root/'measured-cpu.json').read_text());assert cpu['requests']==30 and abs(cpu['process_cpu_ms']/30-cpu['mean_ms_per_request'])<1e-9
   out['timing'][arm]={'warm':10,'measured':30,'client_median_ms':statistics.median(x['client_ms'] for x in measured),'server_median_ms':statistics.median(x['server_ms'] for x in measured),'client_mean_ms':statistics.mean(x['client_ms'] for x in measured),'server_mean_ms':statistics.mean(x['server_ms'] for x in measured),'process_cpu_interval_ms':cpu['process_cpu_ms'],'process_cpu_mean_ms_per_request':cpu['mean_ms_per_request'],'cpu_scope':cpu['scope'],'raw_sha256':hashlib.sha256((root/'rows.jsonl').read_bytes()).hexdigest(),'source':json.loads((root/'source.json').read_text())}
  else:
   assert len(rows)==3;counts=[]
   for i,row in enumerate(rows):
    raw=gzip.decompress((root/f'request{i}.log.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==row['raw_sha256'];counter=collections.Counter()
    for line in raw.decode().splitlines():
     m=re.search(r'\[(\d+)\].*duration: ([\d.]+) ms\s+(execute [^:]*|statement):',line)
     if m:counter[m[1]]+=1
    assert dict(counter)==row['execution_counts_by_pid'] and sum(counter.values())==row['execution_count'];counts.append(row['execution_count'])
   out['census'][arm]={'requests':3,'execution_counts':counts,'warm_stable':counts[1:],'scope':'Separate logged windows; top-level execute/statement events, parse/bind excluded; first request includes initialization and background setup PIDs.'}
  out['checks'].append({'arm':arm,'mode':mode,'passed':True})
assert out['timing']['baseline']['source']['source_files_sha256']==out['timing']['final']['source']['source_files_sha256']
out['comparison']={'server_median_speedup':out['timing']['baseline']['server_median_ms']/out['timing']['final']['server_median_ms'],'client_median_speedup':out['timing']['baseline']['client_median_ms']/out['timing']['final']['client_median_ms'],'data_scope':'Matched 460984-anchor PostgreSQL closure, same application-source hashes; independently selected small diagnostic derived from original idx1 with raised min_date. Separate from native capture idx1 and MySQL Java/SP experiments.','boundary':'Jac client time is HTTP; server header total+commit is separately reported. Compare Java CLI timing only with its declared boundary and database engine.'};out['input']={'original_idx':input_spec['idx'],'person_jid':input_spec['person_jid'],'min_date':input_spec['min_date'],'expected':expected,'file_sha256':hashlib.sha256(input_file.read_bytes()).hexdigest()};out['passed']=True
(H/'independent-results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='timing'},indent=2));print({arm:{k:v for k,v in data.items() if k not in ['source']} for arm,data in out['timing'].items()})
