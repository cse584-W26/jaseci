DROP PROCEDURE IF EXISTS `AlignedIc5_cold_391a3023a9ea_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE AlignedIc5_cold_391a3023a9ea_sp_1_ver0 (IN M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value BIGINT, IN M_L_String__REQUEST_PARAM_person_jid VARCHAR(512))
BEGIN

DECLARE q1_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE RS_q1_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q1_r2_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q1_r3_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q1_r4_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q1_r5_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q1_r6_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q1_r7_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q1_r8_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q1_r9_col1 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_1_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;
DECLARE cursor_0 int DEFAULT NULL;
DECLARE indicator_0 int DEFAULT NULL;
DECLARE q2_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i2 BIGINT DEFAULT NULL;
DECLARE q2_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i4 BIGINT DEFAULT NULL;
DECLARE q2_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i6 BIGINT DEFAULT NULL;
DECLARE q2_i7 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i8 BIGINT DEFAULT NULL;
DECLARE q2_i9 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i10 BIGINT DEFAULT NULL;
DECLARE q2_i11 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i12 BIGINT DEFAULT NULL;
DECLARE q2_i13 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i14 BIGINT DEFAULT NULL;
DECLARE q2_i15 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i16 BIGINT DEFAULT NULL;
DECLARE q2_i17 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i18 BIGINT DEFAULT NULL;
DECLARE q2_i19 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i20 BIGINT DEFAULT NULL;
DECLARE q2_i21 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i22 BIGINT DEFAULT NULL;
DECLARE q2_i23 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i24 BIGINT DEFAULT NULL;
DECLARE q2_i25 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i26 BIGINT DEFAULT NULL;
DECLARE q2_i27 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i28 BIGINT DEFAULT NULL;
DECLARE q2_i29 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i30 BIGINT DEFAULT NULL;
DECLARE q2_i31 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i32 BIGINT DEFAULT NULL;
DECLARE q2_i33 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i34 BIGINT DEFAULT NULL;
DECLARE q2_i35 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i36 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_1 INT DEFAULT NULL;
DECLARE M_I_RS_2_size INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET QUERY_ID_0 = 0;
SET indicator_0 = 0;
SET cursor_cnt_0 = 0;
BEGIN
DECLARE cursor_0 CURSOR FOR SELECT DISTINCT dst FROM adj_knows WHERE src IN (q1_i1);
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_0 = 1;
OPEN cursor_0;
loop_0: LOOP
IF cursor_cnt_0=0 THEN
FETCH cursor_0 INTO RS_q1_r1_col1;
END IF;
IF cursor_cnt_0=1 THEN
FETCH cursor_0 INTO RS_q1_r2_col1;
END IF;
IF cursor_cnt_0=2 THEN
FETCH cursor_0 INTO RS_q1_r3_col1;
END IF;
IF cursor_cnt_0=3 THEN
FETCH cursor_0 INTO RS_q1_r4_col1;
END IF;
IF cursor_cnt_0=4 THEN
FETCH cursor_0 INTO RS_q1_r5_col1;
END IF;
IF cursor_cnt_0=5 THEN
FETCH cursor_0 INTO RS_q1_r6_col1;
END IF;
IF cursor_cnt_0=6 THEN
FETCH cursor_0 INTO RS_q1_r7_col1;
END IF;
IF cursor_cnt_0=7 THEN
FETCH cursor_0 INTO RS_q1_r8_col1;
END IF;
IF cursor_cnt_0=8 THEN
FETCH cursor_0 INTO RS_q1_r9_col1;
END IF;
IF cursor_cnt_0>=9 THEN
CLOSE cursor_0; LEAVE loop_0;END IF;
IF indicator_0=1 THEN CLOSE cursor_0; LEAVE loop_0; END IF;
SET cursor_cnt_0 = cursor_cnt_0 + 1;
END LOOP loop_0;
END;
SET cursor_cnt_0 = FOUND_ROWS();
SELECT cursor_cnt_0,RS_q1_r1_col1,RS_q1_r2_col1,RS_q1_r3_col1,RS_q1_r4_col1,RS_q1_r5_col1,RS_q1_r6_col1,RS_q1_r7_col1,RS_q1_r8_col1,RS_q1_r9_col1;
SET M_I_RS_1_size = cursor_cnt_0;
END IF;
IF TRUE THEN
IF cursor_cnt_0 > 8 THEN
SET q2_i1 = RS_q1_r1_col1;
SET q2_i2 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i3 = RS_q1_r1_col1;
SET q2_i4 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i5 = RS_q1_r2_col1;
SET q2_i6 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i7 = RS_q1_r2_col1;
SET q2_i8 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i9 = RS_q1_r3_col1;
SET q2_i10 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i11 = RS_q1_r3_col1;
SET q2_i12 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i13 = RS_q1_r4_col1;
SET q2_i14 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i15 = RS_q1_r4_col1;
SET q2_i16 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i17 = RS_q1_r5_col1;
SET q2_i18 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i19 = RS_q1_r5_col1;
SET q2_i20 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i21 = RS_q1_r6_col1;
SET q2_i22 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i23 = RS_q1_r6_col1;
SET q2_i24 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i25 = RS_q1_r7_col1;
SET q2_i26 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i27 = RS_q1_r7_col1;
SET q2_i28 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i29 = RS_q1_r8_col1;
SET q2_i30 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i31 = RS_q1_r8_col1;
SET q2_i32 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i33 = RS_q1_r9_col1;
SET q2_i34 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q2_i35 = RS_q1_r9_col1;
SET q2_i36 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET QUERY_ID_1 = 1;
SELECT m.id, m.arch_type, m.props, a.props FROM ( SELECT id, creation_date, tie_id FROM ( (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i1 AND arch_type = 'Post' AND creation_date <= q2_i2 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i3 AND arch_type = 'Comment' AND creation_date <= q2_i4 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i5 AND arch_type = 'Post' AND creation_date <= q2_i6 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i7 AND arch_type = 'Comment' AND creation_date <= q2_i8 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i9 AND arch_type = 'Post' AND creation_date <= q2_i10 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i11 AND arch_type = 'Comment' AND creation_date <= q2_i12 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i13 AND arch_type = 'Post' AND creation_date <= q2_i14 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i15 AND arch_type = 'Comment' AND creation_date <= q2_i16 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i17 AND arch_type = 'Post' AND creation_date <= q2_i18 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i19 AND arch_type = 'Comment' AND creation_date <= q2_i20 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i21 AND arch_type = 'Post' AND creation_date <= q2_i22 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i23 AND arch_type = 'Comment' AND creation_date <= q2_i24 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i25 AND arch_type = 'Post' AND creation_date <= q2_i26 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i27 AND arch_type = 'Comment' AND creation_date <= q2_i28 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i29 AND arch_type = 'Post' AND creation_date <= q2_i30 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i31 AND arch_type = 'Comment' AND creation_date <= q2_i32 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i33 AND arch_type = 'Post' AND creation_date <= q2_i34 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) UNION ALL (SELECT id, creation_date, tie_id FROM jac_snb_message_mirror WHERE creator_id = q2_i35 AND arch_type = 'Comment' AND creation_date <= q2_i36 ORDER BY creation_date DESC, tie_id ASC LIMIT 20) ) candidates ORDER BY creation_date DESC, tie_id ASC LIMIT 20 ) best JOIN jac_snb_message_mirror m ON m.id = best.id JOIN jac_snb_person_mirror a ON a.id = m.creator_id ORDER BY best.creation_date DESC, best.tie_id ASC;
SET M_I_RS_2_size = FOUND_ROWS();
END IF;
END IF;
SELECT QUERY_ID_0,q1_i1,QUERY_ID_1,q2_i1,q2_i2,q2_i3,q2_i4,q2_i5,q2_i6,q2_i7,q2_i8,q2_i9,q2_i10,q2_i11,q2_i12,q2_i13,q2_i14,q2_i15,q2_i16,q2_i17,q2_i18,q2_i19,q2_i20,q2_i21,q2_i22,q2_i23,q2_i24,q2_i25,q2_i26,q2_i27,q2_i28,q2_i29,q2_i30,q2_i31,q2_i32,q2_i33,q2_i34,q2_i35,q2_i36;

END $$
DELIMITER ;