#!/usr/bin/env python3
"""Clone only dedicated seed databases; EXPLAIN captured writes with rollback."""
from datetime import datetime,timezone
import json
import psycopg
from psycopg import sql
import run as lx

def main():
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=lx.ROOT/'write-investigation'/'dml-explain'/stamp;out.mkdir(parents=True)
 duration=sorted((lx.ROOT/'results/littlex-w2').glob('*-duration'))[-1]
 fixture=json.loads((lx.HERE/'fixtures/t20/9144848be024/fixture.json').read_text());e=lx.environment()
 # SQL application is stopped before this loader. Restore its dedicated source
 # database to the same original seed before making the disposable clone.
 lx.command([lx.SQL_PYTHON,lx.HERE/'postgres/loader.py',lx.HERE/'dataset/t20_seed.json'],e,log=out/'sql-seed.log')
 recipes=[('postgres',lx.SQL_ADMIN_DSN,lx.SQL_DB),('jaseci',f'host={lx.SOCK} user=jac dbname=postgres',fixture['snapshot'])]
 for arm,dsn,template in recipes:
  db='repro_w2_explain_'+stamp.lower()+'_'+arm;report=dict(database=db,template=template,arm=arm,source_duration=str(duration))
  with psycopg.connect(dsn,autocommit=True) as admin:
   assert not admin.execute('SELECT 1 FROM pg_database WHERE datname=%s',(db,)).fetchone()
   admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(sql.Identifier(db),sql.Identifier(template)))
   try:
    from psycopg.conninfo import make_conninfo
    for op in ('like','follow','create_tweet'):
     log=sorted((duration/('1-'+arm)/op).glob('postgres-*.log'))[0];target=out/arm/op
     lx.command([lx.DRIVER_PYTHON,lx.ROOT/'write-investigation/explain_dml.py','--log',log,'--out',target,'--execute','--dsn',make_conninfo(dsn,dbname=db),'--repeats','3'],e,log=out/(arm+'-'+op+'.log'))
     print('PASS DML EXPLAIN',arm,op,flush=True)
    report['complete']=True
   finally:
    admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(db)))
    report['scratch_database_dropped']=True;(out/(arm+'-database.json')).write_text(json.dumps(report,indent=2))
 (out/'complete.json').write_text(json.dumps(dict(directory=str(out)),indent=2));print('Complete',out,flush=True)
if __name__=='__main__':main()
