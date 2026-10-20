"""Run original SNB query functions against isolated services and retain raw evidence."""
import argparse,hashlib,json,os,re,statistics,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'benchmark/scripts'))
import httpx,psycopg
from bench_timed import SNB_QUERIES,build_surviving,issue_snb
from snb_validate import SNB,Jac
LOG=ROOT/'dbcache/pg/main/server.log'
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def count_since(offset):
 with LOG.open('rb') as f:f.seek(offset);data=f.read()
 return (sum(b'LOG:  execute' in l or b'LOG:  statement' in l for l in data.splitlines()),len(re.findall(rb'\b(?:CREATE|ALTER|DROP)\s+(?:TABLE|INDEX|TRIGGER|FUNCTION)|INSERT INTO g_n_',data,re.I)))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--queries',default='ic5');ap.add_argument('--warm',type=int,default=1);ap.add_argument('--rounds',type=int,default=1);ap.add_argument('--census',action='store_true');a=ap.parse_args()
 ctx=Jac('jaseci-pg');surviving=build_surviving(ctx,20);queries=a.queries.split(',')
 assert all(len(surviving[SNB_QUERIES[q]['file']])==20 for q in queries),'Missing original parameter rows'
 auth={'Authorization':f"Bearer {json.loads((SNB/'tokens.json').read_text())['svc']}"}
 jc=httpx.Client(base_url='http://127.0.0.1:18109',timeout=900);pc=httpx.Client(base_url='http://127.0.0.1:18111',timeout=900)
 outdir=ROOT/'results'/a.tag;outdir.mkdir(parents=True,exist_ok=True)
 results=[];hashes={};pg_hashes={};failed=0
 for rep in range(-a.warm,a.rounds):
  for q in queries:
   for idx,row in surviving[SNB_QUERIES[q]['file']]:
    # Order alternates between paired rounds; census always isolates Jac before PG.
    def run(arm):return issue_snb(arm,jc if arm=='jaseci-pg' else pc,ctx,{} if arm=='jaseci-pg' else auth,q,row)
    if rep%2 and not a.census:
     pg=run('postgres');jac=run('jaseci-pg');n=None;structural=None
    else:
     offset=LOG.stat().st_size if a.census else 0
     jac=run('jaseci-pg')
     if a.census:time.sleep(.05)
     n,structural=count_since(offset) if a.census else (None,None)
     pg=run('postgres')
    ok=not jac[3] and not pg[3] and jac[2] is not None and pg[2] is not None and canon(jac[2])==canon(pg[2])
    record=dict(query=q,idx=idx,rep=rep,jac_ms=jac[0],jac_server_ms=jac[1],pg_ms=pg[0],pg_server_ms=pg[1],stmts=n,structural_sql=structural,parity=ok,jac_error=jac[3],pg_error=pg[3],input=row)
    if not ok:
     failed+=1;record.update(jac_output=jac[2],pg_output=pg[2])
    if rep>=0:
     results.append(record);hashes[f'{q}:{idx}']=hashlib.sha256(json.dumps(jac[2],sort_keys=True).encode()).hexdigest();pg_hashes[f'{q}:{idx}']=hashlib.sha256(json.dumps(pg[2],sort_keys=True).encode()).hexdigest()
     (outdir/'rows.json').write_text(json.dumps(results,indent=2))
    print(f'{a.tag} rep={rep} {q}[{idx}] jac={jac[0]:.2f}ms pg={pg[0]:.2f}ms stmts={n} parity={ok}',flush=True)
 summary={'tag':a.tag,'failed_including_warm':failed,'queries':{},'app_sha256':hashlib.sha256((ROOT/'benchmark/snb/jaseci-pg/app.jac').read_bytes()).hexdigest()}
 for q in queries:
  rs=[r for r in results if r['query']==q];j=[r['jac_ms'] for r in rs];p=[r['pg_ms'] for r in rs]
  summary['queries'][q]={'n':len(rs),'parity_ok':sum(r['parity'] for r in rs),'jac_median_ms':statistics.median(j),'pg_median_ms':statistics.median(p),'median_ratio':statistics.median(j)/statistics.median(p),'jac_upper_middle_ms':sorted(j)[len(j)//2],'pg_upper_middle_ms':sorted(p)[len(p)//2],'total_statements':sum(r['stmts'] for r in rs) if a.census else None,'structural_sql':sum(r['structural_sql'] for r in rs) if a.census else None}
 historical=json.loads((ROOT.parent/'DBHarness/session0904/run/data/snb/postgres/snb_postgres.hashes.json').read_text())
 summary['historical_hash_matches']=sum(v==historical.get(k) for k,v in hashes.items());summary['historical_hash_keys']=len(hashes)
 (outdir/'pg-hashes.json').write_text(json.dumps(pg_hashes,indent=2))
 (outdir/'summary.json').write_text(json.dumps(summary,indent=2));(outdir/'hashes.json').write_text(json.dumps(hashes,indent=2));print(json.dumps(summary,indent=2),flush=True)
 return bool(failed)
if __name__=='__main__':sys.exit(main())
