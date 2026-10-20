"""Toggle logging on the reproduction-owned cluster without restarting warm apps."""
import argparse,json,time
from pathlib import Path
import psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[1]
DSN='host=/tmp/jacpg-d6275e76eb user=jac dbname=postgres'
ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['census','duration','off']);args=ap.parse_args()
assert str(ROOT/'dbcache/pg/main') in (ROOT/'dbcache/pg/main/postmaster.opts').read_text()
with psycopg.connect(DSN,autocommit=True) as c:
 for setting,value in [('log_statement','all' if args.mode=='census' else 'none'),('log_min_duration_statement','0' if args.mode=='duration' else '-1')]:
  c.execute(sql.SQL('ALTER SYSTEM SET {} = {}').format(sql.Identifier(setting),sql.Literal(value)))
 c.execute('SELECT pg_reload_conf()')
time.sleep(.2)
print('Dedicated cluster logging:',args.mode,flush=True)
(ROOT/'logs/db-settings.json').write_text(json.dumps({'cluster':str(ROOT/'dbcache/pg/main'),'mode':args.mode},indent=2))
