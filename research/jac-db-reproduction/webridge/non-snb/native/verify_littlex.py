"""Offline native littleX payload, original-plan, source-oracle and full-state verification."""
import argparse,pathlib,json,gzip,hashlib,statistics,collections,datetime,itertools
from jsonl_chunks import rows_lines
from littlex_oracle import Oracle,digest
R=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--input',type=pathlib.Path,default=R/'littlex-timing');p.add_argument('--oracle-fixtures',type=pathlib.Path,default=R/'littlex-oracle-fixtures');p.add_argument('--out',type=pathlib.Path);a=p.parse_args();summary=json.loads((a.input/'summary.json').read_text());verified=[]
for cell in summary:
 directory=R/cell['path']
 if not directory.exists():directory=a.input/pathlib.Path(cell['path']).relative_to(a.input.name)
 scope=json.loads((directory/'scope.json').read_text());planraw=(directory/'plan.json').read_bytes();assert hashlib.sha256(planraw).hexdigest()==scope['original_plan_sha256'];plan=json.loads(planraw)[:scope['selected_requests']];oracle=Oracle(a.oracle_fixtures/(cell['tier']+'.json.gz'));rows=[];stream=map(json.loads,rows_lines(directory))
 for row,original in itertools.zip_longest(stream,plan):
  assert row is not None and original is not None
  x=original['input'];assert row['warmup']==original['warmup']and row['iteration']==original['iteration']and row['username']==x['username']and row['operation']==x['op'];assert row['status']==200;assert row['HTTP_route']=={'feed':'load_feed_chain','feed_page':'load_feed_page','like':'like_tweet','follow':'follow_user','create_tweet':'create_tweet'}[x['op']]
  expected={k:x[k]for k in {'feed':[],'feed_page':[],'like':['tweet_id'],'follow':['target_id'],'create_tweet':['seed_id','content']}[x['op']]};assert row['request_body']==expected
  assert hashlib.sha256(row['response_text'].encode()).hexdigest()==row['response_sha256'];payload=json.loads(row['response_text']);d=payload.get('data',payload);result=d['reports'][0]if isinstance(d,dict)and'reports'in d else d;proof=oracle.apply(x,result);assert proof==row['oracle'];assert row['server_ms']==float(row['headers']['x-server-total-ms'])+float(row['headers']['x-server-commit-ms'])
  if x['op']=='create_tweet':assert row['start_wall_ns']/1e9-1<=datetime.datetime.fromisoformat(result['tweet']['created_at'].replace('Z','+00:00')).timestamp()<=row['end_wall_ns']/1e9+1
  rows.append({k:row[k]for k in ['warmup','server_ms','client_ms','operation']})
 state=json.load(gzip.open(directory/'after-state.json.gz','rt'));assert state==oracle.canonical();manifest=json.loads((directory/'after-state-manifest.json').read_text());assert manifest['exact_business_state_verified'];assert manifest['sha256']=={k:digest(v)for k,v in state.items()};assert manifest['rows']=={k:len(v)for k,v in state.items()};assert json.loads((directory/'settings-restored.json').read_text())['exact_prior_restored'];assert json.loads((directory/'runtime-subtree.json').read_text())['equal']
 measured=[r for r in rows if not r['warmup']];assert len(measured)==cell['n']and len(rows)-len(measured)==cell['warm'];assert statistics.median(r['server_ms']for r in measured)==cell['server_median_ms'];assert statistics.median(r['client_ms']for r in measured)==cell['client_median_ms'];assert dict(collections.Counter(r['operation']for r in measured))==cell['measured_operation_counts'];verified.append({'path':str(directory),'requests':len(rows),'measured':len(measured),'PASS':True})
out=a.out or a.input/'independent-offline-verification.json';out.write_text(json.dumps({'PASS':True,'cells':len(verified),'requests':sum(x['requests']for x in verified),'measured':sum(x['measured']for x in verified),'checks':'Exact response bytes/hash, original frozen plan, route/body, source-fixture field/order/write oracle, new clock interval, complete normalized final business state, header formula, medians, source/runtime and settings restoration','details':verified},indent=2)+'\n');print(len(verified),'cells PASS')
