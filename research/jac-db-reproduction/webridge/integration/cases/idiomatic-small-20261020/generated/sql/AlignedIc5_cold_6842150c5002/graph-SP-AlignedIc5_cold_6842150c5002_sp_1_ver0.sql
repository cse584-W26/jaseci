DROP PROCEDURE IF EXISTS `AlignedIc5_cold_6842150c5002_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE AlignedIc5_cold_6842150c5002_sp_1_ver0 (IN M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value BIGINT, IN M_L_String__REQUEST_PARAM_person_jid VARCHAR(512))
BEGIN

DECLARE q1_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i3 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE M_I_RS_1_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET q1_i2 = M_L_String__REQUEST_PARAM_person_jid;
SET q1_i3 = M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value;
SET QUERY_ID_0 = 0;
SELECT CAST(JSON_UNQUOTE(JSON_EXTRACT(f.props, '$.archetype.forum_id')) AS SIGNED) AS external_forum_id, JSON_UNQUOTE(JSON_EXTRACT(f.props, '$.archetype.title')) AS title , COUNT(DISTINCT CASE  WHEN memberships.friend_id = author.id THEN p.id END) AS post_count FROM ( SELECT DISTINCT member.src AS forum_id, member.dst AS friend_id FROM anchors member JOIN ( SELECT k.dst AS id FROM anchors k WHERE k.src = q1_i1 AND k.kind = 'EdgeAnchor' AND k.arch_type = 'Knows' AND (k.dst_type IS NULL OR k.dst_type = 'Person') UNION SELECT k.src AS id FROM anchors k WHERE k.dst = q1_i2 AND k.kind = 'EdgeAnchor' AND k.arch_type = 'Knows' AND (k.src_type IS NULL OR k.src_type = 'Person') ) friends ON friends.id = member.dst JOIN anchors friend ON friend.id = friends.id AND friend.kind = 'NodeAnchor' AND friend.arch_type = 'Person' WHERE member.kind = 'EdgeAnchor' AND member.arch_type = 'HasMember' AND (member.src_type IS NULL OR member.src_type = 'Forum') AND CAST(JSON_UNQUOTE(JSON_EXTRACT(member.props, '$.archetype.joinDate')) AS SIGNED) > q1_i3 ) memberships JOIN anchors f ON f.id = memberships.forum_id AND f.kind = 'NodeAnchor' AND f.arch_type = 'Forum' LEFT JOIN anchors co ON co.src = f.id AND co.kind = 'EdgeAnchor' AND co.arch_type = 'ContainerOf' AND (co.dst_type IS NULL OR co.dst_type = 'Post') LEFT JOIN anchors p ON p.id = co.dst AND p.kind = 'NodeAnchor' AND p.arch_type = 'Post' LEFT JOIN anchors hc ON hc.src = p.id AND hc.kind = 'EdgeAnchor' AND hc.arch_type = 'HasCreator' AND (hc.dst_type IS NULL OR hc.dst_type = 'Person') LEFT JOIN anchors author ON author.id = hc.dst AND author.kind = 'NodeAnchor' AND author.arch_type = 'Person' GROUP BY f.id, external_forum_id, title ORDER BY post_count DESC, external_forum_id ASC LIMIT 20;
SET M_I_RS_1_size = FOUND_ROWS();
END IF;
SELECT QUERY_ID_0,q1_i1,q1_i2,q1_i3;

END $$
DELIMITER ;