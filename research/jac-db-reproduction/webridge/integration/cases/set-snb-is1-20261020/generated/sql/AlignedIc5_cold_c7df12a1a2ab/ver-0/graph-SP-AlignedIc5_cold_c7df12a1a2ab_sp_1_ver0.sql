DROP PROCEDURE IF EXISTS `AlignedIc5_cold_c7df12a1a2ab_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE AlignedIc5_cold_c7df12a1a2ab_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_person_jid VARCHAR(512))
BEGIN

DECLARE q1_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE M_I_RS_1_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET QUERY_ID_0 = 0;
SELECT p.props, CAST(JSON_UNQUOTE(JSON_EXTRACT(n.props, '$.archetype.place_id')) AS SIGNED) FROM anchors p LEFT JOIN anchors e ON e.src = p.id AND e.kind = 'EdgeAnchor' AND e.arch_type = 'IsLocatedIn' LEFT JOIN anchors n ON n.id = e.dst AND n.kind = 'NodeAnchor' AND n.arch_type = 'Place' WHERE p.id = q1_i1 ORDER BY e.seq, e.id LIMIT 1;
SET M_I_RS_1_size = FOUND_ROWS();
END IF;
SELECT QUERY_ID_0,q1_i1;

END $$
DELIMITER ;