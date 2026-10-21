"""Fresh original TPC-C HTTP loader, isolated database and immutable template."""
import pathlib,sys,subprocess,json,time
import psycopg
R=pathlib.Path(__file__).resolve().parent;N=R.parent;REPRO=R.parents[2]
sys.path.insert(0,str(N));from measurement_lease import lease
DB='jac_non_snb_tpcc_seed_20261020';SNAP='jac_non_snb_tpcc_initial_20261020'
with lease('native TPC-C fresh seed',R/'tpcc-seed-lease.json'):
 with psycopg.connect('host=/tmp/jacpg-d6275e76eb user=jac dbname=postgres',autocommit=True)as c:
  assert not c.execute('SELECT 1 FROM pg_database WHERE datname=ANY(%s)',([DB,SNAP],)).fetchone(),'Preserve existing fixture'
  c.execute(psycopg.sql.SQL('CREATE DATABASE {}').format(psycopg.sql.Identifier(DB)))
 cmd=[sys.executable,str(R/'service.py')]
 try:
  subprocess.run([*cmd,'start','--variant','baseline'],check=True)
  with(R/'tpcc-seed.log').open('w')as log:subprocess.run([sys.executable,str(R/'baseline/app/seed.py'),'--base-url','http://127.0.0.1:18132','--data',str(REPRO/'benchmark/tpcc/data')],stdout=log,stderr=subprocess.STDOUT,check=True)
 finally:subprocess.run([*cmd,'stop','--variant','baseline'],check=True)
 with psycopg.connect('host=/tmp/jacpg-d6275e76eb user=jac dbname=postgres',autocommit=True)as c:
  assert c.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=%s',(DB,)).fetchone()[0]==0
  c.execute(psycopg.sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(psycopg.sql.Identifier(SNAP),psycopg.sql.Identifier(DB)))
  c.execute(psycopg.sql.SQL('ALTER DATABASE {} ALLOW_CONNECTIONS false').format(psycopg.sql.Identifier(SNAP)))
 (R/'tpcc-seed-complete.json').write_text(json.dumps({'database':DB,'snapshot':SNAP,'original_seed':str(REPRO/'benchmark/tpcc/jaseci-pg/seed.py'),'completed_wall_ns':time.time_ns()},indent=2))
