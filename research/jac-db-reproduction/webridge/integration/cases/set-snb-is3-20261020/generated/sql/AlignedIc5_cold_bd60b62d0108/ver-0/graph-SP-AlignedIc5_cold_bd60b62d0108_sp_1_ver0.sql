DROP PROCEDURE IF EXISTS `AlignedIc5_cold_bd60b62d0108_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE AlignedIc5_cold_bd60b62d0108_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_person_jid VARCHAR(512))
BEGIN

DECLARE q1_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i2 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE M_I_RS_1_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET q1_i2 = M_L_String__REQUEST_PARAM_person_jid;
SET QUERY_ID_0 = 0;
SELECT CAST(JSON_UNQUOTE(JSON_EXTRACT(p.props, '$.archetype.person_id')) AS SIGNED), JSON_UNQUOTE(JSON_EXTRACT(p.props, '$.archetype.firstName')) , JSON_UNQUOTE(JSON_EXTRACT(p.props, '$.archetype.lastName')) FROM ( SELECT e.dst AS id FROM anchors e WHERE e.src = q1_i1 AND e.kind = 'EdgeAnchor' AND e.arch_type = 'Knows' UNION ALL SELECT e.src AS id FROM anchors e WHERE e.dst = q1_i2 AND e.kind = 'EdgeAnchor' AND e.arch_type = 'Knows' ) f JOIN anchors p ON p.id = f.id AND p.kind = 'NodeAnchor' AND p.arch_type = 'Person' ORDER BY CAST(JSON_UNQUOTE(JSON_EXTRACT(p.props, '$.archetype.person_id')) AS SIGNED);
SET M_I_RS_1_size = FOUND_ROWS();
END IF;
SELECT QUERY_ID_0,q1_i1,q1_i2;

END $$
DELIMITER ;