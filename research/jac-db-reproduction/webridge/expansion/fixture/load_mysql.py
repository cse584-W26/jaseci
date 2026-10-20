#!/usr/bin/env python3
import pathlib,subprocess,json,time
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];db='jac_snb_six_20261020';container='jac-webridge-mysql57'
def cli(q):
 p=subprocess.run(['docker','exec','-i',container,'mysql','--local-infile=1','--default-character-set=utf8mb4','-uroot','-N','-B'],input=q.encode(),capture_output=True);assert p.returncode==0,p.stderr.decode();return p.stdout.decode()
assert cli("SELECT count(*) FROM information_schema.schemata WHERE schema_name='"+db+"'").strip()=='0','Refuse overwrite'
start=time.time();before=cli('SELECT @@global.local_infile').strip();assert before=='1','Existing dedicated loader must have local_infile enabled; do not alter global settings silently'
q=(B/'alignment/schema.sql').read_text().replace('jac_alignment',db).replace('CHARACTER SET ascii COLLATE ascii_bin','CHARACTER SET utf8mb4 COLLATE utf8mb4_bin').replace('CHARACTER SET ascii','CHARACTER SET utf8mb4 COLLATE utf8mb4_bin');(H/'mysql-schema.sql').write_text(q);cli(q)
for name in ['anchors','graph_types','identity_users','kv_state']:
 subprocess.run(['docker','cp',str((H/'data' if name in ['anchors','graph_types'] else B/'jac-comparison/fixture')/(name+'.tsv')),container+':/tmp/snb-six-'+name+'.tsv'],check=True)
try:
 cli("USE "+db+"; LOAD DATA LOCAL INFILE '/tmp/snb-six-anchors.tsv' INTO TABLE anchors CHARACTER SET utf8mb4 (id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,@undirected,props,row_version,seq,src_type,dst_type) SET undirected=(@undirected='t'); LOAD DATA LOCAL INFILE '/tmp/snb-six-graph_types.tsv' INTO TABLE graph_types CHARACTER SET utf8mb4; LOAD DATA LOCAL INFILE '/tmp/snb-six-identity_users.tsv' INTO TABLE identity_users CHARACTER SET utf8mb4; LOAD DATA LOCAL INFILE '/tmp/snb-six-kv_state.tsv' INTO TABLE kv_state CHARACTER SET utf8mb4; ANALYZE TABLE anchors,graph_types;")
 count=cli("USE "+db+"; SELECT kind,arch_type,count(*) FROM anchors GROUP BY kind,arch_type ORDER BY kind,arch_type;");(H/'mysql-types.tsv').write_text(count)
 check=cli("USE "+db+"; SELECT count(*),sum(NOT JSON_VALID(props)) FROM anchors; SELECT count(*) FROM anchors e LEFT JOIN anchors s ON s.id=e.src LEFT JOIN anchors d ON d.id=e.dst WHERE e.kind='EdgeAnchor' AND(s.id IS NULL OR d.id IS NULL); SELECT count(*) FROM anchors a LEFT JOIN anchors r ON r.id=a.root_id WHERE a.root_id IS NOT NULL AND r.id IS NULL;");assert check.splitlines()==['1475843\t0','0','0'],check
 (H/'mysql-load-receipt.json').write_text(json.dumps({'database':db,'container':container,'started_unix':start,'ended_unix':time.time(),'checks':check,'local_infile_unchanged':before,'export':json.loads((H/'export-receipt.json').read_text())['anchors']},indent=2)+'\n')
finally:subprocess.run(['docker','exec',container,'rm','-f','/tmp/snb-six-anchors.tsv','/tmp/snb-six-graph_types.tsv','/tmp/snb-six-identity_users.tsv','/tmp/snb-six-kv_state.tsv'],check=True)
