"""Create only the dedicated matched database, preserving source as read-only."""
import json
from pathlib import Path
import psycopg
from psycopg import sql
H=Path(__file__).resolve().parent;name='jac_webridge_matched_20261020'
with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname='postgres',autocommit=True) as c:
 exists=c.execute('SELECT 1 FROM pg_database WHERE datname=%s',(name,)).fetchone()
 if exists:raise RuntimeError('Dedicated database already exists; refusing overwrite')
 c.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C'").format(sql.Identifier(name)))
(H/'database-created.json').write_text(json.dumps({'database':name,'host':'/tmp/jacpg-d6275e76eb','user':'jac','port':5432,'source_database':'jac_snb_bench_pg_fbdb3a2c','source_write_operations':0},indent=2)+'\n');print(name)
