#!/usr/bin/env python3
"""Build read-only fixture equivalents of the measured top-K endpoint/root columns."""
import datetime,hashlib,json,pathlib,subprocess
H=pathlib.Path(__file__).resolve().parent;out=H/'relations';out.mkdir(exist_ok=True)
def run(sql):
 cmd=['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-N','-uroot','jac_snb_six_20261020'];p=subprocess.run(cmd,input=sql,capture_output=True,text=True);rows.append({'sql':sql,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});
 if p.returncode:raise RuntimeError(p.stderr)
 return p.stdout
rows=[];start=datetime.datetime.now(datetime.timezone.utc).isoformat()
try:
 sql='''CREATE TABLE IF NOT EXISTS jac_snb_message_mirror(id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,arch_type VARCHAR(20) NOT NULL,props LONGTEXT CHARACTER SET utf8mb4 NOT NULL,creator_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,creation_date BIGINT,tie_id BIGINT,parent_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,root_of_replyof CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,PRIMARY KEY(id),KEY creator_topk(creator_id,arch_type,creation_date,tie_id)) ENGINE=InnoDB;
INSERT IGNORE INTO jac_snb_message_mirror SELECT n.id,n.arch_type,n.props,hc.dst,CAST(JSON_UNQUOTE(JSON_EXTRACT(n.props,'$.archetype.creationDate')) AS SIGNED),CAST(JSON_UNQUOTE(JSON_EXTRACT(n.props,IF(n.arch_type='Post','$.archetype.post_id','$.archetype.comment_id'))) AS SIGNED),NULL,IF(n.arch_type='Post',n.id,NULL) FROM anchors n LEFT JOIN anchors hc ON hc.src=n.id AND hc.kind='EdgeAnchor' AND hc.arch_type='HasCreator' WHERE n.kind='NodeAnchor' AND n.arch_type IN('Post','Comment');
UPDATE jac_snb_message_mirror m JOIN anchors e ON e.src=m.id AND e.kind='EdgeAnchor' AND e.arch_type='ReplyOf' SET m.parent_id=e.dst WHERE m.arch_type='Comment';
SELECT 'creator_cardinality_violations',COUNT(*) FROM (SELECT hc.src FROM anchors hc WHERE hc.kind='EdgeAnchor' AND hc.arch_type='HasCreator' GROUP BY hc.src HAVING COUNT(*)>1) v;
SELECT 'reply_cardinality_violations',COUNT(*) FROM (SELECT e.src FROM anchors e WHERE e.kind='EdgeAnchor' AND e.arch_type='ReplyOf' GROUP BY e.src HAVING COUNT(*)>1) v;
''';(out/'prepare-message.sql').write_text(sql);answer=run(sql)
 for line in answer.strip().splitlines():
  if line.startswith(('creator_cardinality_violations\t','reply_cardinality_violations\t')):assert int(line.split('\t')[1])==0,line
 for depth in range(1025):
  answer=run("UPDATE jac_snb_message_mirror c JOIN jac_snb_message_mirror p ON p.id=c.parent_id SET c.root_of_replyof=p.root_of_replyof WHERE c.root_of_replyof IS NULL AND p.root_of_replyof IS NOT NULL; SELECT ROW_COUNT();")
  changed=int(answer.strip().splitlines()[-1]);
  if changed==0:break
 else:raise RuntimeError('ReplyOf root propagation did not converge')
 run("ANALYZE TABLE jac_snb_message_mirror; SELECT arch_type,COUNT(*),SUM(root_of_replyof IS NOT NULL),SUM(creator_id IS NOT NULL) FROM jac_snb_message_mirror GROUP BY arch_type;")
finally:(out/'message-receipt.json').write_text(json.dumps({'utc':start,'calls':rows,'read_only_fixture_equivalent':'Stored endpoint and reply-root columns; build excluded from request timing','canonical_data_retained':True},indent=2))
print(rows[-1]['stdout'])
