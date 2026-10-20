#!/usr/bin/env python3
"""Replay recorded SELECT with captured literals in read-only EXPLAIN controls."""
import json,re,sys
from pathlib import Path
from datetime import datetime,timezone
import psycopg
from psycopg import sql
import run as lx

def capture(folder):
 lines=(folder/'postgres-00.log').read_text().splitlines();candidates=[]
 for i,line in enumerate(lines):
  m=re.search(r'duration: ([0-9.]+) ms\s+execute [^:]*: (SELECT .+)',line)
  if m and i+1<len(lines) and 'Parameters:' in lines[i+1]:
   pars=dict(re.findall(r"\$(\d+) = ('(?:[^']|'')*'|NULL)",lines[i+1].split('Parameters:',1)[1]));query=m.group(2)
   if all(n in pars for n in re.findall(r'\$(\d+)',query)):candidates.append((float(m.group(1)),query,pars))
 assert candidates
 return max(candidates,key=lambda x:x[0])
def main():
 out=lx.HERE/'explain'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True)
 base=lx.ROOT/'results/littlex-diagnostics'
 pairs=[('t20-final-fresh',next(base.glob('20261019T195729Z/t20-final-fixture-duration-on')),lx.HERE/'fixtures/t20/5eb056bf874f/fixture.json'),('t20-final-old',next(base.glob('*/t20-historical-fixture-final1-rr')),lx.HERE/'fixtures/t20/9144848be024/fixture.json'),('t200-page-old',base/'20261019T195241Z/t200-feed_page-ad469-control',lx.HERE/'fixtures/t200/fc1ffda7943f/fixture.json')]
 if '--analyzed-only' in sys.argv:pairs=[('t20-final-fresh-analyzed',pairs[0][1],pairs[0][2])]
 for name,profile,fixture in pairs:
  cell=out/name;cell.mkdir();ms,query,params=capture(profile);db=json.loads(fixture.read_text())['database'];(cell/'captured.json').write_text(json.dumps(dict(profile=str(profile),database=db,original_execute_ms=ms,query=query,params=params),indent=2))
  with psycopg.connect(host=lx.SOCK,user='jac',dbname=db,autocommit=True) as conn:
   conn.execute('SET default_transaction_read_only=on');conn.execute("SET statement_timeout='120s'")
   stats=conn.execute("SELECT c.relname,c.reltuples,c.relpages,c.relallvisible,pg_relation_size(c.oid),s.n_live_tup,s.n_dead_tup,s.last_analyze::text,s.last_autoanalyze::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_stat_user_tables s ON s.relid=c.oid WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.relname").fetchall()
   indexes=conn.execute("SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname").fetchall()
   column_stats=conn.execute("SELECT tablename,attname,null_frac,n_distinct,correlation,most_common_freqs::text FROM pg_stats WHERE schemaname='public' ORDER BY tablename,attname").fetchall()
   relation_sizes=conn.execute("SELECT c.relname,c.relkind,c.reltuples,c.relpages,pg_relation_size(c.oid) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','i') ORDER BY c.relname").fetchall()
   settings=conn.execute("SELECT name,setting FROM pg_settings WHERE name IN ('jit','plan_cache_mode','random_page_cost','seq_page_cost','shared_buffers','work_mem','effective_cache_size','max_parallel_workers_per_gather') ORDER BY name").fetchall()
   (cell/'layout.json').write_text(json.dumps(dict(tables=stats,indexes=indexes,settings=settings,column_stats=column_stats,relation_sizes=relation_sizes),indent=2,default=str))
   conn.execute('PREPARE lx_explain AS '+query)
   args=', '.join(params[str(i)] for i in range(1,len(params)+1))
   for mode in ('force_custom_plan','force_generic_plan'):
    conn.execute('SET plan_cache_mode='+mode)
    for repeat in range(3):
     plan=conn.execute('EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT JSON) EXECUTE lx_explain('+args+')').fetchone()[0]
     (cell/(mode+'-'+str(repeat)+'.json')).write_text(json.dumps(plan,indent=2))
   conn.execute('DEALLOCATE lx_explain')
  print('EXPLAIN complete',name,flush=True)
 print('Complete',out,flush=True)
if __name__=='__main__':main()
