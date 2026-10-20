import json,socket
from datetime import datetime,timezone
import psycopg
import run as lx

def main():
 e=lx.environment()
 with lx.fixture_lock():app,tokens,reset=lx.fixture('t20',lx.HERE/'dataset/t20_seed.json',e)
 report=dict(utc=datetime.now(timezone.utc).isoformat(),native_restored=reset,clusters={},http_ports={})
 for label,dsn in [('native',f'host={lx.SOCK} user=jac dbname=postgres'),('pg16',lx.SQL_ADMIN_DSN)]:
  with psycopg.connect(dsn,autocommit=True) as c:
   settings={name:c.execute('SHOW '+name).fetchone()[0] for name in ('server_version','log_statement','log_min_duration_statement','fsync','synchronous_commit')}
   scratch=c.execute("SELECT datname FROM pg_database WHERE datname LIKE 'repro_w2_explain_%'").fetchall();assert not scratch,scratch
   overrides=c.execute("SELECT d.datname,s.setconfig FROM pg_db_role_setting s JOIN pg_database d ON d.oid=s.setdatabase WHERE d.datname LIKE 'jac_lx_repro_%' OR d.datname='littlex_reproduction_sql'").fetchall();assert not overrides,overrides
   assert settings['log_statement']=='none' and settings['log_min_duration_statement']=='-1' and settings['fsync']=='on' and settings['synchronous_commit']=='on',settings
   report['clusters'][label]=dict(settings=settings,scratch_databases=scratch,database_overrides=overrides)
 for port in (18120,18121):
  with socket.socket() as s:opened=s.connect_ex(('127.0.0.1',port))==0
  assert not opened,port
  report['http_ports'][str(port)]='closed'
 (lx.ROOT/'write-investigation/final-state.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
