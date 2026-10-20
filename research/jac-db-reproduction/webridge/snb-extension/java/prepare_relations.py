#!/usr/bin/env python3
"""Materialize the measured native adjacency and Person lookup relations on MySQL."""
import datetime,hashlib,json,pathlib,subprocess
H=pathlib.Path(__file__).resolve().parent;out=H/'relations';out.mkdir(exist_ok=True)
sql='''CREATE TABLE IF NOT EXISTS adj_knows(src CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,dst CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,PRIMARY KEY(src,dst)) ENGINE=InnoDB;
INSERT IGNORE INTO adj_knows SELECT src,dst FROM anchors WHERE kind='EdgeAnchor' AND arch_type='Knows';
INSERT IGNORE INTO adj_knows SELECT dst,src FROM anchors WHERE kind='EdgeAnchor' AND arch_type='Knows';
CREATE TABLE IF NOT EXISTS jac_snb_person_mirror(id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,root_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,props JSON NOT NULL,person_id BIGINT,first_name VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,last_name VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,PRIMARY KEY(id),KEY first_name_idx(first_name),KEY person_id_idx(person_id)) ENGINE=InnoDB;
INSERT IGNORE INTO jac_snb_person_mirror SELECT id,root_id,props,CAST(JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.person_id')) AS SIGNED),JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.firstName')),JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.lastName')) FROM anchors WHERE kind='NodeAnchor' AND arch_type='Person';
ANALYZE TABLE adj_knows,jac_snb_person_mirror;
SELECT 'anchors',COUNT(*) FROM anchors;
SELECT 'knows',COUNT(*) FROM anchors WHERE kind='EdgeAnchor' AND arch_type='Knows';
SELECT 'adjacency',COUNT(*) FROM adj_knows;
SELECT 'person',COUNT(*) FROM jac_snb_person_mirror;
SELECT 'missing_reverse',COUNT(*) FROM adj_knows a LEFT JOIN adj_knows b ON b.src=a.dst AND b.dst=a.src WHERE b.src IS NULL;
SELECT 'missing_endpoint',COUNT(*) FROM adj_knows a LEFT JOIN jac_snb_person_mirror s ON s.id=a.src LEFT JOIN jac_snb_person_mirror d ON d.id=a.dst WHERE s.id IS NULL OR d.id IS NULL;
'''
(out/'prepare.sql').write_text(sql);cmd=['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-N','-uroot','jac_snb_six_20261020'];start=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run(cmd,input=sql,capture_output=True,text=True);(out/'receipt.json').write_text(json.dumps({'command':cmd,'utc':start,'sql_sha256':hashlib.sha256(sql.encode()).hexdigest(),'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'source_PostgreSQL_adjacency_schema':{'src':'uuid','dst':'uuid','primary_key':['src','dst']},'adaptation':'UUID text representation and equivalent finite Knows adjacency; Person scalar indexes mirror measured endpoint predicate queries'},indent=2));print(r.stdout,r.stderr);raise SystemExit(r.returncode)
