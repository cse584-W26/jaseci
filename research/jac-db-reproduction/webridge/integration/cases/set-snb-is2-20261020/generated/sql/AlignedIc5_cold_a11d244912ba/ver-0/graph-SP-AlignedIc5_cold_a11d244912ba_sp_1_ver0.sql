DROP PROCEDURE IF EXISTS `AlignedIc5_cold_a11d244912ba_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE AlignedIc5_cold_a11d244912ba_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_person_jid VARCHAR(512))
BEGIN

DECLARE q1_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE M_I_RS_1_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET QUERY_ID_0 = 0;
SELECT m.id, m.arch_type, m.props, a.props, r.props , ra.props FROM jac_snb_message_mirror m LEFT JOIN jac_snb_person_mirror a ON a.id = m.creator_id LEFT JOIN jac_snb_message_mirror r ON r.id = m.root_of_replyof LEFT JOIN jac_snb_person_mirror ra ON ra.id = r.creator_id WHERE m.creator_id = q1_i1 ORDER BY m.creation_date DESC, m.tie_id DESC LIMIT 10;
SET M_I_RS_1_size = FOUND_ROWS();
END IF;
SELECT QUERY_ID_0,q1_i1;

END $$
DELIMITER ;