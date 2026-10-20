#!/usr/bin/env python3
"""Retain actual database syntax capability checks for native Jac constructs."""
import datetime,json,pathlib,subprocess
R=pathlib.Path(__file__).resolve().parent/'capability';R.mkdir(exist_ok=True)
queries={'version':'SELECT VERSION()','recursive-cte':'WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x WHERE n<2) SELECT * FROM x','lateral':'SELECT t.n,u.m FROM (SELECT 1 AS n) t CROSS JOIN LATERAL (SELECT t.n AS m) u'}
rows=[]
for name,sql in queries.items():
 cmd=['docker','exec','jac-webridge-mysql57','mysql','-N','-uroot','-e',sql];start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(cmd,capture_output=True,text=True)
 row={'name':name,'sql':sql,'command':cmd,'utc':start,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr};rows.append(row)
(R/'mysql57.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
