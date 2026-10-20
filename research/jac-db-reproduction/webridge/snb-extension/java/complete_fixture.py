#!/usr/bin/env python3
"""Complete measured native metadata and uniform UUID character representation."""
import datetime,hashlib,json,pathlib,subprocess
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];out=H/'relations';out.mkdir(exist_ok=True);rows=[]
def run(sql):
 cmd=['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-N','-uroot','jac_snb_six_20261020'];r=subprocess.run(cmd,input=sql,capture_output=True,text=True);rows.append({'sql':sql,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});
 if r.returncode:raise RuntimeError(r.stderr)
 return r.stdout
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
try:
 run('SHOW CREATE TABLE anchors;')
 run('ALTER TABLE anchors MODIFY id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL, MODIFY root_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin, MODIFY src CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin, MODIFY dst CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;')
 run('CREATE TABLE IF NOT EXISTS identity_lookups(value_normalized VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,user_id VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,PRIMARY KEY(value_normalized),KEY user_id_idx(user_id)) ENGINE=InnoDB;')
 source=B/'jac-comparison/fixture/identity_lookups.tsv';values=[]
 for line in source.read_text().splitlines():
  k,v=line.split('\t');values.append("('"+k.replace("'","''")+"','"+v.replace("'","''")+"')")
 run('INSERT IGNORE INTO identity_lookups VALUES '+','.join(values)+';')
 run('SHOW CREATE TABLE anchors;SELECT * FROM identity_lookups ORDER BY value_normalized;ANALYZE TABLE anchors;')
finally:(out/'fixture-completion.json').write_text(json.dumps({'utc':start,'calls':rows,'lookup_source':str(source),'lookup_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'adaptation':'All clients and SPs share same UTF8 UUID columns; preserves original UUID values'},indent=2))
print('Uniform UTF8 UUIDs and identity lookup relation ready')
