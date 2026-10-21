#!/usr/bin/env python3
"""Independently check every full returned value against the immutable source fixture."""
import pathlib,json,gzip,sys,argparse,hashlib
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent/'native'));from littlex_oracle import Oracle,digest
from result_chunks import lines,sha
from business_state import expected,expected_rows
p=argparse.ArgumentParser();p.add_argument('--tier',required=True);p.add_argument('--fixture',type=pathlib.Path);p.add_argument('--expected-rows',type=pathlib.Path);p.add_argument('--plan',required=True,type=pathlib.Path);p.add_argument('--results',required=True,type=pathlib.Path);p.add_argument('--out',required=True,type=pathlib.Path);a=p.parse_args();plan=json.loads(a.plan.read_text());fixture=a.fixture or H/'fixtures'/a.tier/'anchors.tsv';fixture=fixture if fixture.exists()else H.parent/'native/littlex-oracle-fixtures'/(a.tier+'.json.gz');oracle=Oracle(fixture);initial_expected=expected(oracle);counts={};n=0
if True:
 for line in lines(a.results):
  r=json.loads(line);assert r['plan_ordinal']==n,(r['plan_ordinal'],n);x=plan[n]['input'];result=r['result']
  if x['op']=='create_tweet':
   # Java preallocates the exact generated ID before the measured region.
   result=json.loads(json.dumps(result));result['tweet']['_jac_id']=x['new_id'].replace('-','');assert result['tweet']['created_at']==x['created_at']
  proof=oracle.apply(x,result);assert proof['verified'];counts[x['op']]=counts.get(x['op'],0)+1;n+=1
assert n==len(plan),(n,len(plan));canonical=oracle.canonical();receipt={'status':'PASS','checked_requests':n,'per_operation_counts':counts,'scope':'every returned field and feed order against independent immutable source-fixture state, evolved after every operation','source_fixture':str(fixture),'source_fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256(a.plan.read_bytes()).hexdigest(),'full_results':str(a.results),'full_results_sha256':sha(a.results),'final_expected_state':{k:{'rows':len(v),'sha256':digest(v)}for k,v in canonical.items()},'UUID_policy':'Only native metadata _jac_id is supplied from the exact preallocated Java request ID for the shared oracle; business fields are checked as returned'};
receipt['initial_expected_common_state']=initial_expected;receipt['final_expected_common_state']=expected(oracle);receipt['common_state_scope']='Profiles(id,username), Follow rows with multiplicity, Tweets(id,seed_id,content,author,created_at,likes,comments)'
if a.results.suffix=='.gz':
 receipt['full_results_logical_monolith']=str(a.results);receipt['public_chunk_index']=str(a.results.with_name('full-results-public-chunks')/'index.json')if a.results.stat().st_size>80*1024**2 else None
else:
 chunkmeta=json.loads(a.results.read_text());receipt['full_results_logical_monolith']=chunkmeta['source'];receipt['full_results_logical_monolith_sha256']=chunkmeta['source_sha256'];receipt['public_chunk_index']=str(a.results)
if a.expected_rows:
 with gzip.open(a.expected_rows,'wt',encoding='utf-8')as f:json.dump(expected_rows(oracle),f,ensure_ascii=False,separators=(',',':'))
 receipt['expected_common_state_rows']=str(a.expected_rows)
a.out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'status':'PASS','requests':n,'counts':counts}))
