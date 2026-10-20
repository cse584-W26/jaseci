#!/usr/bin/env python3
"""Owned PG16 create_tweet profiling with original frozen SQL app/driver."""
from datetime import datetime,timezone
import json
import psycopg
from psycopg import sql
import run as lx

def main():
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=lx.HERE/'sql-write-diagnostic'/stamp;out.mkdir(parents=True)
 env=lx.environment();env['PROF_TIMERS']='1';tokens=out/'tokens';tokens.mkdir();p=None
 with psycopg.connect(lx.SQL_ADMIN_DSN,autocommit=True) as admin:
  cfg=admin.execute('SELECT setconfig FROM pg_db_role_setting WHERE setrole=0 AND setdatabase=(SELECT oid FROM pg_database WHERE datname=%s)',(lx.SQL_DB,)).fetchone()
  previous=next((s.split('=',1)[1] for s in (cfg[0] if cfg else []) if s.startswith('log_min_duration_statement=')),None)
  admin.execute(sql.SQL('ALTER DATABASE {} SET log_min_duration_statement=0').format(sql.Identifier(lx.SQL_DB)))
  try:
   lx.command([lx.SQL_PYTHON,lx.HERE/'postgres/loader.py',lx.HERE/'dataset/t20_seed.json'],env,log=out/'seed.log')
   for script,target in [('mint_tokens.py','tokens.postgres.json'),('export_targets.py','targets.postgres.json')]:lx.command([lx.DRIVER_PYTHON,lx.HERE/'harness'/script,'--engine','postgres','--output',tokens/target],env,log=out/(script+'.log'))
   p=lx.launch(['taskset','-c','6-13',lx.SQL_PYTHON,'-m','uvicorn','app:app','--host','127.0.0.1','--port','18121','--no-access-log'],lx.HERE/'postgres',env,out/'server.log',18121,'/docs')
   lx.command([lx.DRIVER_PYTHON,lx.ROOT/'scripts/littlex_sql_write_profile.py','--tag','littlex-sql-write/'+stamp,'--tier','t20','--tokens-dir',tokens,'--pid',str(p.pid),'--seed',lx.HERE/'dataset/t20_seed.json'],env,log=out/'profile.log')
   (out/'complete.json').write_text(json.dumps(dict(tag='littlex-sql-write/'+stamp,sql_python=str(lx.SQL_PYTHON),driver_python=str(lx.DRIVER_PYTHON),target_database=lx.SQL_DB,affinity='6-13'),indent=2));print('Complete',out,flush=True)
  finally:
   lx.stop(p)
   if previous is None:admin.execute(sql.SQL('ALTER DATABASE {} RESET log_min_duration_statement').format(sql.Identifier(lx.SQL_DB)))
   else:admin.execute(sql.SQL('ALTER DATABASE {} SET log_min_duration_statement TO {}').format(sql.Identifier(lx.SQL_DB),sql.Literal(previous)))
if __name__=='__main__':main()
