DROP PROCEDURE IF EXISTS `Snb_is2_pruned_cce8eacb71_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE Snb_is2_pruned_cce8eacb71_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_person_jid VARCHAR(512))
BEGIN

DECLARE q1_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE M_I_RS_1_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;
DECLARE q2_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i3 BIGINT DEFAULT NULL;
DECLARE q2_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i6 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_1 INT DEFAULT NULL;
DECLARE RS_q2_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q2_r2_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r2_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r2_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q2_r3_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r3_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r3_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q2_r4_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r4_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r4_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q2_r5_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r5_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r5_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q2_r6_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r6_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r6_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q2_r7_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r7_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r7_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q2_r8_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r8_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r8_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q2_r9_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r9_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r9_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q2_r10_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r10_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r10_col3 LONGTEXT DEFAULT NULL;
DECLARE M_I_RS_2_size INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;
DECLARE cursor_1 int DEFAULT NULL;
DECLARE indicator_1 int DEFAULT NULL;
DECLARE q3_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i2 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_2 INT DEFAULT NULL;
DECLARE RS_q3_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r1_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r2_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r2_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r2_col3 LONGTEXT DEFAULT NULL;
DECLARE M_I_RS_3_size INT DEFAULT NULL;
DECLARE cursor_cnt_2 INT DEFAULT NULL;
DECLARE cursor_2 int DEFAULT NULL;
DECLARE indicator_2 int DEFAULT NULL;
DECLARE q4_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i2 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_3 INT DEFAULT NULL;
DECLARE M_I_RS_4_size INT DEFAULT NULL;
DECLARE cursor_cnt_3 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET QUERY_ID_0 = 0;
SELECT JSON_EXTRACT(props, '$.archetype') FROM anchors WHERE id = q1_i1;
SET M_I_RS_1_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q2_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET q2_i2 = 'Post';
SET q2_i3 = 9223372036854775807;
SET q2_i4 = M_L_String__REQUEST_PARAM_person_jid;
SET q2_i5 = 'Comment';
SET q2_i6 = 9223372036854775807;
SET QUERY_ID_1 = 1;
SET indicator_1 = 0;
SET cursor_cnt_1 = 0;
BEGIN
DECLARE cursor_1 CURSOR FOR SELECT id, arch_type, props FROM ( (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q2_i1 AND m.arch_type = q2_i2 AND m.creation_date <= q2_i3 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 10) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q2_i4 AND m.arch_type = q2_i5 AND m.creation_date <= q2_i6 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 10) ) u ORDER BY ord DESC, tie ASC LIMIT 10;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_1 = 1;
OPEN cursor_1;
loop_1: LOOP
IF cursor_cnt_1=0 THEN
FETCH cursor_1 INTO RS_q2_r1_col1, RS_q2_r1_col2, RS_q2_r1_col3;
END IF;
IF cursor_cnt_1=1 THEN
FETCH cursor_1 INTO RS_q2_r2_col1, RS_q2_r2_col2, RS_q2_r2_col3;
END IF;
IF cursor_cnt_1=2 THEN
FETCH cursor_1 INTO RS_q2_r3_col1, RS_q2_r3_col2, RS_q2_r3_col3;
END IF;
IF cursor_cnt_1=3 THEN
FETCH cursor_1 INTO RS_q2_r4_col1, RS_q2_r4_col2, RS_q2_r4_col3;
END IF;
IF cursor_cnt_1=4 THEN
FETCH cursor_1 INTO RS_q2_r5_col1, RS_q2_r5_col2, RS_q2_r5_col3;
END IF;
IF cursor_cnt_1=5 THEN
FETCH cursor_1 INTO RS_q2_r6_col1, RS_q2_r6_col2, RS_q2_r6_col3;
END IF;
IF cursor_cnt_1=6 THEN
FETCH cursor_1 INTO RS_q2_r7_col1, RS_q2_r7_col2, RS_q2_r7_col3;
END IF;
IF cursor_cnt_1=7 THEN
FETCH cursor_1 INTO RS_q2_r8_col1, RS_q2_r8_col2, RS_q2_r8_col3;
END IF;
IF cursor_cnt_1=8 THEN
FETCH cursor_1 INTO RS_q2_r9_col1, RS_q2_r9_col2, RS_q2_r9_col3;
END IF;
IF cursor_cnt_1=9 THEN
FETCH cursor_1 INTO RS_q2_r10_col1, RS_q2_r10_col2, RS_q2_r10_col3;
END IF;
IF cursor_cnt_1>=10 THEN
CLOSE cursor_1; LEAVE loop_1;END IF;
IF indicator_1=1 THEN CLOSE cursor_1; LEAVE loop_1; END IF;
SET cursor_cnt_1 = cursor_cnt_1 + 1;
END LOOP loop_1;
END;
SET cursor_cnt_1 = FOUND_ROWS();
SELECT cursor_cnt_1,RS_q2_r1_col1,RS_q2_r1_col2,RS_q2_r1_col3,RS_q2_r2_col1,RS_q2_r2_col2,RS_q2_r2_col3,RS_q2_r3_col1,RS_q2_r3_col2,RS_q2_r3_col3,RS_q2_r4_col1,RS_q2_r4_col2,RS_q2_r4_col3,RS_q2_r5_col1,RS_q2_r5_col2,RS_q2_r5_col3,RS_q2_r6_col1,RS_q2_r6_col2,RS_q2_r6_col3,RS_q2_r7_col1,RS_q2_r7_col2,RS_q2_r7_col3,RS_q2_r8_col1,RS_q2_r8_col2,RS_q2_r8_col3,RS_q2_r9_col1,RS_q2_r9_col2,RS_q2_r9_col3,RS_q2_r10_col1,RS_q2_r10_col2,RS_q2_r10_col3;
SET M_I_RS_2_size = cursor_cnt_1;
END IF;
IF TRUE THEN
IF cursor_cnt_1 > 9 THEN
SET q3_i1 = RS_q2_r9_col1;
SET q3_i2 = RS_q2_r10_col1;
SET QUERY_ID_2 = 2;
SET indicator_2 = 0;
SET cursor_cnt_2 = 0;
BEGIN
DECLARE cursor_2 CURSOR FOR SELECT m.id, m.root_of_replyof, p.props FROM jac_snb_message_mirror m JOIN anchors p ON p.id = m.root_of_replyof WHERE m.id IN (q3_i1, q3_i2) AND m.root_of_replyof IS NOT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_2 = 1;
OPEN cursor_2;
loop_2: LOOP
IF cursor_cnt_2=0 THEN
FETCH cursor_2 INTO RS_q3_r1_col1, RS_q3_r1_col2, RS_q3_r1_col3;
END IF;
IF cursor_cnt_2=1 THEN
FETCH cursor_2 INTO RS_q3_r2_col1, RS_q3_r2_col2, RS_q3_r2_col3;
END IF;
IF cursor_cnt_2>=2 THEN
CLOSE cursor_2; LEAVE loop_2;END IF;
IF indicator_2=1 THEN CLOSE cursor_2; LEAVE loop_2; END IF;
SET cursor_cnt_2 = cursor_cnt_2 + 1;
END LOOP loop_2;
END;
SET cursor_cnt_2 = FOUND_ROWS();
SELECT cursor_cnt_2,RS_q3_r1_col1,RS_q3_r1_col2,RS_q3_r1_col3,RS_q3_r2_col1,RS_q3_r2_col2,RS_q3_r2_col3;
SET M_I_RS_3_size = cursor_cnt_2;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_2 > 1 THEN
SET q4_i1 = RS_q3_r1_col2;
SET q4_i2 = RS_q3_r2_col2;
SET QUERY_ID_3 = 3;
SELECT e.src, n.props FROM anchors e JOIN anchors n ON n.id = e.dst AND n.kind = 'NodeAnchor' WHERE e.kind = 'EdgeAnchor' AND e.arch_type = 'HasCreator' AND e.src IN (q4_i1, q4_i2) ORDER BY e.seq, e.id;
SET M_I_RS_4_size = FOUND_ROWS();
END IF;
END IF;
SELECT QUERY_ID_0,q1_i1,QUERY_ID_1,q2_i1,q2_i2,q2_i3,q2_i4,q2_i5,q2_i6,QUERY_ID_2,q3_i1,q3_i2,QUERY_ID_3,q4_i1,q4_i2;

END $$
DELIMITER ;