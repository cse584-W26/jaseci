"""Capture all20 actual IC5 baseline requests with database-scoped SQL logging.
Restores database settings and restarts the isolated service when finished.
"""
import argparse,gzip,hashlib,json,re,subprocess,sys,time
from pathlib import Path
import httpx,psycopg
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'benchmark/scripts'))
from snb_validate import Jac
from bench_timed import issue_snb

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);ap.add_argument('--rounds',type=int,default=3);a=ap.parse_args();a.out.mkdir(exist_ok=False,parents=True)
 db='jac_snb_bench_pg_fbdb3a2c';settings=['log_min_duration_statement','log_statement','log_duration']
 ctl=psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname='postgres',autocommit=True)
 prior=ctl.execute('SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=%s) AND setrole=0',(db,)).fetchone()
 original={} if not prior else dict(x.split('=',1) for x in prior[0]);(a.out/'database-settings-before.json').write_text(json.dumps(original,indent=2))
 def manage():subprocess.run([sys.executable,str(ROOT/'scripts/manage.py'),'start','jac','--variant','baseline'],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 inputs=[json.loads((HERE/'input.json').read_text())];ctx=Jac('jaseci-pg');log=ROOT/'dbcache/pg/main/server.log';rows=[]
 try:
  for key,value in [('log_min_duration_statement','0'),('log_statement','none'),('log_duration','off')]:ctl.execute(psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(db),psycopg.sql.Identifier(key),psycopg.sql.Literal(value)))
  manage()
  with httpx.Client(base_url='http://127.0.0.1:18109',timeout=900) as client,(a.out/'rows.jsonl').open('w') as sink:
   for rnd in range(a.rounds):
    for x in inputs:
     offset=log.stat().st_size;start=time.time();ms,server,result,error=issue_snb('jaseci-pg',client,ctx,{},'ic5',{'personId':str(x['pid']),'minDate':str(x['min_date'])});time.sleep(.1)
     with log.open('rb') as f:f.seek(offset);raw=f.read()
     name=f'round{rnd}-input{x["idx"]:02d}.log.gz';gzip.open(a.out/name,'wb').write(raw)
     execution_lines=[line for line in raw.decode().splitlines() if re.search(r'duration: .* ms\s+(execute [^:]*|statement):',line)]
     expected=[{'forumId':r[0],'title':r[1],'postCount':r[2]} for r in x['expected']]
     parity=not error and result.get('forums')==expected
     row={'round':rnd,'idx':x['idx'],'start_unix':start,'client_ms':ms,'server_ms':server,'statements':len(execution_lines),'parity':parity,'error':error,'result':result,'log':name,'raw_sha256':hashlib.sha256(raw).hexdigest()};rows.append(row);sink.write(json.dumps(row)+'\n');sink.flush();print(json.dumps({k:row[k] for k in ['round','idx','statements','parity','client_ms']}),flush=True)
     if error or not parity:raise RuntimeError('Baseline parity failed')
 finally:
  for key in settings:
   if key in original:ctl.execute(psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(db),psycopg.sql.Identifier(key),psycopg.sql.Literal(original[key])))
   else:ctl.execute(psycopg.sql.SQL('ALTER DATABASE {} RESET {}').format(psycopg.sql.Identifier(db),psycopg.sql.Identifier(key)))
  ctl.close();manage()
  (a.out/'rows.json').write_text(json.dumps(rows,indent=2))
  (a.out/'restored.json').write_text(json.dumps({'database':db,'restored_settings':settings,'baseline_service_restarted':True}))
if __name__=='__main__':main()
