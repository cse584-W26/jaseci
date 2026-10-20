"""Pause/restore autovacuum only in the isolated SNB DB during schema setup."""
import argparse,json
from pathlib import Path
import psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[1];STATE=ROOT/'logs/autovacuum-state.json'
ap=argparse.ArgumentParser();ap.add_argument('action',choices=['pause','restore','vacuum']);a=ap.parse_args()
with psycopg.connect('host=/tmp/jacpg-d6275e76eb user=jac dbname=jac_snb_bench_pg_fbdb3a2c',autocommit=True) as c:
 c.execute("SET lock_timeout='10s'")
 if a.action=='pause':
  if STATE.exists():raise RuntimeError('Autovacuum state already recorded; restore first')
  tables=list(c.execute("SELECT relname,reloptions FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r'"))
  STATE.write_text(json.dumps([{'table':name,'options':opts} for name,opts in tables],indent=2))
  for (pid,) in c.execute("SELECT pid FROM pg_stat_activity WHERE datname=current_database() AND backend_type='autovacuum worker'"):
   c.execute('SELECT pg_cancel_backend(%s)',(pid,))
  for name,_ in tables:c.execute(sql.SQL('ALTER TABLE {} SET (autovacuum_enabled=false)').format(sql.Identifier(name)))
  print('Paused table autovacuum:',len(tables))
 elif a.action=='restore':
  for row in json.loads(STATE.read_text()):
   original=next((v.split('=',1)[1] for v in row['options'] or [] if v.startswith('autovacuum_enabled=')),None)
   c.execute(sql.SQL('ALTER TABLE {} RESET (autovacuum_enabled)').format(sql.Identifier(row['table'])) if original is None else sql.SQL('ALTER TABLE {} SET (autovacuum_enabled={})').format(sql.Identifier(row['table']),sql.SQL(original)))
  STATE.rename(ROOT/'logs/autovacuum-state-restored.json');print('Autovacuum options restored')
 else:
  c.execute('VACUUM (ANALYZE)');print('Vacuum/analyze complete')
