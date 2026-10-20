DROP PROCEDURE IF EXISTS `Snb_is1_pruned_7e2ab66c14_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE Snb_is1_pruned_7e2ab66c14_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_person_jid VARCHAR(512))
BEGIN

DECLARE q1_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE M_I_RS_1_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;
DECLARE q2_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i6 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i7 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i8 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i9 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i10 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i11 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i12 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i13 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_1 INT DEFAULT NULL;
DECLARE M_I_RS_2_size INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET QUERY_ID_0 = 0;
SELECT JSON_EXTRACT(props, '$.archetype') FROM anchors WHERE id = q1_i1;
SET M_I_RS_1_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q2_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET q2_i2 = 'IsLocatedIn';
SET q2_i3 = 'IsLocatedIn';
SET q2_i4 = 'Place';
SET q2_i5 = 'Place';
SET q2_i6 = M_L_String__REQUEST_PARAM_person_jid;
SET q2_i7 = 'IsLocatedIn';
SET q2_i8 = 'IsLocatedIn';
SET q2_i9 = 'Place';
SET q2_i10 = 'Place';
SET q2_i11 = M_L_String__REQUEST_PARAM_person_jid;
SET q2_i12 = 'Place';
SET q2_i13 = 'Place';
SET QUERY_ID_1 = 1;
SELECT n.id, e.id, JSON_EXTRACT(n.props, '$.archetype') FROM ( SELECT e.* FROM anchors e WHERE e.src = q2_i1 AND e.kind = 'EdgeAnchor' AND (e.arch_type = q2_i2 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i3 )) AND (e.dst_type IS NULL OR e.dst_type = q2_i4 OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i5 )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = q2_i6 AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = q2_i7 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i8 )) AND (e.src_type IS NULL OR e.src_type = q2_i9 OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i10 )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = q2_i11 THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = q2_i12 OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i13 )) ORDER BY e.seq, e.id;
SET M_I_RS_2_size = FOUND_ROWS();
END IF;
SELECT QUERY_ID_0,q1_i1,QUERY_ID_1,q2_i1,q2_i2,q2_i3,q2_i4,q2_i5,q2_i6,q2_i7,q2_i8,q2_i9,q2_i10,q2_i11,q2_i12,q2_i13;

END $$
DELIMITER ;