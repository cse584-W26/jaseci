"""Read-only optional baseline gate using original seven SNB requests and hashes."""
import argparse,hashlib,json,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'benchmark/scripts'))
import httpx
from bench_timed import SNB_QUERIES,issue_snb
from snb_validate import SNB,params
p=argparse.ArgumentParser();p.add_argument('--arm',required=True,choices=['sqlalchemy','neo4j']);p.add_argument('--base-url',required=True);p.add_argument('--out-dir',required=True,type=Path);p.add_argument('--warm',type=int,default=1);p.add_argument('--rounds',type=int,default=1);p.add_argument('--queries',default=','.join(SNB_QUERIES));a=p.parse_args()
historical=json.loads((ROOT.parent/'DBHarness/session0904/run/data/snb/postgres/snb_postgres.hashes.json').read_text())
auth={'Authorization':f"Bearer {json.loads((SNB/'tokens.json').read_text())['svc']}"};records=[];hashes={};failed=0
a.out_dir.mkdir(parents=True,exist_ok=True)
with httpx.Client(base_url=a.base_url,timeout=900) as c:
 for rep in range(-a.warm,a.rounds):
  for q in a.queries.split(','):
   for i,row in enumerate(params(SNB_QUERIES[q]['file'],20)):
    cms,sms,out,error=issue_snb(a.arm,c,None,auth,q,row)
    h=hashlib.sha256(json.dumps(out,sort_keys=True).encode()).hexdigest();ok=not error and h==historical.get(f'{q}:{i}');failed+=not ok
    r={'arm':a.arm,'rep':rep,'query':q,'idx':i,'input':row,'client_ms':cms,'server_ms':sms,'hash':h,'historical_match':ok,'error':error}
    if not ok:r['output']=out
    if rep>=0:records.append(r);hashes[f'{q}:{i}']=h
    print(f'{a.arm} rep={rep} {q}[{i}] {cms:.2f}ms historical_match={ok}',flush=True)
    (a.out_dir/'rows.json').write_text(json.dumps(records,indent=2)+'\n')
summary={'arm':a.arm,'failed_including_warm':failed,'historical_hash_matches':sum(v==historical.get(k) for k,v in hashes.items()),'historical_hash_keys':len(hashes),'queries':{}}
for q in a.queries.split(','):
 rs=[r for r in records if r['query']==q];summary['queries'][q]={'n':len(rs),'client_median_ms':statistics.median(r['client_ms'] for r in rs),'server_median_ms':statistics.median([r['server_ms'] for r in rs if r['server_ms'] is not None]) if any(r['server_ms'] is not None for r in rs) else None,'historical_matches':sum(r['historical_match'] for r in rs)}
(a.out_dir/'hashes.json').write_text(json.dumps(hashes,indent=2)+'\n');(a.out_dir/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));sys.exit(bool(failed))
