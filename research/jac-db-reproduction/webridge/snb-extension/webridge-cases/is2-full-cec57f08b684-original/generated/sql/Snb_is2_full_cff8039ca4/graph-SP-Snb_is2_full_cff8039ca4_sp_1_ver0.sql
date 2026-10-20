DROP PROCEDURE IF EXISTS `Snb_is2_full_cff8039ca4_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE Snb_is2_full_cff8039ca4_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_person_jid VARCHAR(512))
BEGIN

DECLARE q1_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE M_I_RS_1_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;
DECLARE q2_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_1 INT DEFAULT NULL;
DECLARE RS_q2_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col2 LONGTEXT DEFAULT NULL;
DECLARE RS_q2_r1_col3 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_2_size INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;
DECLARE cursor_1 int DEFAULT NULL;
DECLARE indicator_1 int DEFAULT NULL;
DECLARE q3_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_2 INT DEFAULT NULL;
DECLARE M_I_RS_3_size INT DEFAULT NULL;
DECLARE cursor_cnt_2 INT DEFAULT NULL;
DECLARE q4_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_3 INT DEFAULT NULL;
DECLARE M_I_RS_4_size INT DEFAULT NULL;
DECLARE cursor_cnt_3 INT DEFAULT NULL;
DECLARE q5_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_4 INT DEFAULT NULL;
DECLARE M_I_RS_5_size INT DEFAULT NULL;
DECLARE cursor_cnt_4 INT DEFAULT NULL;
DECLARE q6_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q6_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q6_i3 BIGINT DEFAULT NULL;
DECLARE q6_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q6_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q6_i6 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_5 INT DEFAULT NULL;
DECLARE RS_q6_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q6_r2_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q6_r3_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q6_r4_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q6_r5_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q6_r6_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q6_r7_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q6_r8_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q6_r9_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q6_r10_col1 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_6_size INT DEFAULT NULL;
DECLARE cursor_cnt_5 INT DEFAULT NULL;
DECLARE cursor_5 int DEFAULT NULL;
DECLARE indicator_5 int DEFAULT NULL;
DECLARE q7_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_6 INT DEFAULT NULL;
DECLARE M_I_RS_7_size INT DEFAULT NULL;
DECLARE cursor_cnt_6 INT DEFAULT NULL;
DECLARE q8_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_7 INT DEFAULT NULL;
DECLARE M_I_RS_8_size INT DEFAULT NULL;
DECLARE cursor_cnt_7 INT DEFAULT NULL;
DECLARE q9_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_8 INT DEFAULT NULL;
DECLARE M_I_RS_9_size INT DEFAULT NULL;
DECLARE cursor_cnt_8 INT DEFAULT NULL;
DECLARE q10_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_9 INT DEFAULT NULL;
DECLARE M_I_RS_10_size INT DEFAULT NULL;
DECLARE cursor_cnt_9 INT DEFAULT NULL;
DECLARE q11_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_10 INT DEFAULT NULL;
DECLARE M_I_RS_11_size INT DEFAULT NULL;
DECLARE cursor_cnt_10 INT DEFAULT NULL;
DECLARE q12_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_11 INT DEFAULT NULL;
DECLARE M_I_RS_12_size INT DEFAULT NULL;
DECLARE cursor_cnt_11 INT DEFAULT NULL;
DECLARE q13_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_12 INT DEFAULT NULL;
DECLARE M_I_RS_13_size INT DEFAULT NULL;
DECLARE cursor_cnt_12 INT DEFAULT NULL;
DECLARE q14_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_13 INT DEFAULT NULL;
DECLARE M_I_RS_14_size INT DEFAULT NULL;
DECLARE cursor_cnt_13 INT DEFAULT NULL;
DECLARE q15_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_14 INT DEFAULT NULL;
DECLARE RS_q15_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q15_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q15_r1_col3 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q15_r1_col4 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q15_r1_col5 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q15_r1_col6 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q15_r1_col7 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q15_r1_col8 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q15_r1_col9 BOOLEAN DEFAULT NULL;
DECLARE RS_q15_r1_col10 LONGTEXT DEFAULT NULL;
DECLARE RS_q15_r1_col11 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_15_size INT DEFAULT NULL;
DECLARE cursor_cnt_14 INT DEFAULT NULL;
DECLARE cursor_14 int DEFAULT NULL;
DECLARE indicator_14 int DEFAULT NULL;
DECLARE q16_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_15 INT DEFAULT NULL;
DECLARE RS_q16_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q16_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q16_r1_col3 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q16_r1_col4 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q16_r1_col5 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q16_r1_col6 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q16_r1_col7 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q16_r1_col8 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q16_r1_col9 BOOLEAN DEFAULT NULL;
DECLARE RS_q16_r1_col10 LONGTEXT DEFAULT NULL;
DECLARE RS_q16_r1_col11 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_16_size INT DEFAULT NULL;
DECLARE cursor_cnt_15 INT DEFAULT NULL;
DECLARE cursor_15 int DEFAULT NULL;
DECLARE indicator_15 int DEFAULT NULL;
DECLARE q17_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q17_i2 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_16 INT DEFAULT NULL;
DECLARE RS_q17_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q17_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q17_r2_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q17_r2_col2 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_17_size INT DEFAULT NULL;
DECLARE cursor_cnt_16 INT DEFAULT NULL;
DECLARE cursor_16 int DEFAULT NULL;
DECLARE indicator_16 int DEFAULT NULL;
DECLARE q18_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q18_i2 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_17 INT DEFAULT NULL;
DECLARE RS_q18_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r1_col3 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r1_col4 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r1_col5 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r1_col6 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r1_col7 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r1_col8 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r1_col9 BOOLEAN DEFAULT NULL;
DECLARE RS_q18_r1_col10 LONGTEXT DEFAULT NULL;
DECLARE RS_q18_r1_col11 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r2_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r2_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r2_col3 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r2_col4 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r2_col5 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r2_col6 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r2_col7 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r2_col8 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q18_r2_col9 BOOLEAN DEFAULT NULL;
DECLARE RS_q18_r2_col10 LONGTEXT DEFAULT NULL;
DECLARE RS_q18_r2_col11 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_18_size INT DEFAULT NULL;
DECLARE cursor_cnt_17 INT DEFAULT NULL;
DECLARE cursor_17 int DEFAULT NULL;
DECLARE indicator_17 int DEFAULT NULL;
DECLARE q19_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q19_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q19_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q19_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q19_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q19_i6 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_18 INT DEFAULT NULL;
DECLARE RS_q19_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q19_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q19_r2_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q19_r2_col2 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_19_size INT DEFAULT NULL;
DECLARE cursor_cnt_18 INT DEFAULT NULL;
DECLARE cursor_18 int DEFAULT NULL;
DECLARE indicator_18 int DEFAULT NULL;
DECLARE q20_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q20_i2 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_19 INT DEFAULT NULL;
DECLARE M_I_RS_20_size INT DEFAULT NULL;
DECLARE cursor_cnt_19 INT DEFAULT NULL;
DECLARE q21_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q21_i2 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_20 INT DEFAULT NULL;
DECLARE M_I_RS_21_size INT DEFAULT NULL;
DECLARE cursor_cnt_20 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = '4bc418b3-c394-41ee-93fd-4a13a6c852a8';
SET QUERY_ID_0 = 0;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q1_i1);
SET M_I_RS_1_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q2_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET QUERY_ID_1 = 1;
SET indicator_1 = 0;
SET cursor_cnt_1 = 0;
BEGIN
DECLARE cursor_1 CURSOR FOR SELECT id, props, root_id FROM anchors WHERE id IN (q2_i1);
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_1 = 1;
OPEN cursor_1;
loop_1: LOOP
IF cursor_cnt_1=0 THEN
FETCH cursor_1 INTO RS_q2_r1_col1, RS_q2_r1_col2, RS_q2_r1_col3;
END IF;
IF cursor_cnt_1>=1 THEN
CLOSE cursor_1; LEAVE loop_1;END IF;
IF indicator_1=1 THEN CLOSE cursor_1; LEAVE loop_1; END IF;
SET cursor_cnt_1 = cursor_cnt_1 + 1;
END LOOP loop_1;
END;
SET cursor_cnt_1 = FOUND_ROWS();
SELECT cursor_cnt_1,RS_q2_r1_col1,RS_q2_r1_col2,RS_q2_r1_col3;
SET M_I_RS_2_size = cursor_cnt_1;
END IF;
IF TRUE THEN
SET q3_i1 = '__guest__';
SET QUERY_ID_2 = 2;
SELECT doc FROM identity_users WHERE user_id = q3_i1;
SET M_I_RS_3_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q4_i1 = '__guest__';
SET QUERY_ID_3 = 3;
SELECT t.doc FROM identity_users t JOIN identity_lookups lk ON t.user_id = lk.user_id WHERE lk.value_normalized = q4_i1 AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(t.doc, '$.status')), 'active') <> 'disabled';
SET M_I_RS_4_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q5_i1 = '4bc418b3-c394-41ee-93fd-4a13a6c852a8';
SET QUERY_ID_4 = 4;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q5_i1);
SET M_I_RS_5_size = FOUND_ROWS();
END IF;
IF TRUE THEN
IF cursor_cnt_1 > 0 THEN
SET q6_i1 = RS_q2_r1_col1;
SET q6_i2 = 'Post';
SET q6_i3 = 9223372036854775807;
SET q6_i4 = RS_q2_r1_col1;
SET q6_i5 = 'Comment';
SET q6_i6 = 9223372036854775807;
SET QUERY_ID_5 = 5;
SET indicator_5 = 0;
SET cursor_cnt_5 = 0;
BEGIN
DECLARE cursor_5 CURSOR FOR SELECT id FROM ( (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = q6_i1 AND m.arch_type = q6_i2 AND m.creation_date <= q6_i3 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 10) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = q6_i4 AND m.arch_type = q6_i5 AND m.creation_date <= q6_i6 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 10) ) u ORDER BY ord DESC, tie ASC LIMIT 10;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_5 = 1;
OPEN cursor_5;
loop_5: LOOP
IF cursor_cnt_5=0 THEN
FETCH cursor_5 INTO RS_q6_r1_col1;
END IF;
IF cursor_cnt_5=1 THEN
FETCH cursor_5 INTO RS_q6_r2_col1;
END IF;
IF cursor_cnt_5=2 THEN
FETCH cursor_5 INTO RS_q6_r3_col1;
END IF;
IF cursor_cnt_5=3 THEN
FETCH cursor_5 INTO RS_q6_r4_col1;
END IF;
IF cursor_cnt_5=4 THEN
FETCH cursor_5 INTO RS_q6_r5_col1;
END IF;
IF cursor_cnt_5=5 THEN
FETCH cursor_5 INTO RS_q6_r6_col1;
END IF;
IF cursor_cnt_5=6 THEN
FETCH cursor_5 INTO RS_q6_r7_col1;
END IF;
IF cursor_cnt_5=7 THEN
FETCH cursor_5 INTO RS_q6_r8_col1;
END IF;
IF cursor_cnt_5=8 THEN
FETCH cursor_5 INTO RS_q6_r9_col1;
END IF;
IF cursor_cnt_5=9 THEN
FETCH cursor_5 INTO RS_q6_r10_col1;
END IF;
IF cursor_cnt_5>=10 THEN
CLOSE cursor_5; LEAVE loop_5;END IF;
IF indicator_5=1 THEN CLOSE cursor_5; LEAVE loop_5; END IF;
SET cursor_cnt_5 = cursor_cnt_5 + 1;
END LOOP loop_5;
END;
SET cursor_cnt_5 = FOUND_ROWS();
SELECT cursor_cnt_5,RS_q6_r1_col1,RS_q6_r2_col1,RS_q6_r3_col1,RS_q6_r4_col1,RS_q6_r5_col1,RS_q6_r6_col1,RS_q6_r7_col1,RS_q6_r8_col1,RS_q6_r9_col1,RS_q6_r10_col1;
SET M_I_RS_6_size = cursor_cnt_5;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_5 > 0 THEN
SET q7_i1 = RS_q6_r1_col1;
SET QUERY_ID_6 = 6;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q7_i1);
SET M_I_RS_7_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_5 > 1 THEN
SET q8_i1 = RS_q6_r2_col1;
SET QUERY_ID_7 = 7;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q8_i1);
SET M_I_RS_8_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_5 > 2 THEN
SET q9_i1 = RS_q6_r3_col1;
SET QUERY_ID_8 = 8;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q9_i1);
SET M_I_RS_9_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_5 > 3 THEN
SET q10_i1 = RS_q6_r4_col1;
SET QUERY_ID_9 = 9;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q10_i1);
SET M_I_RS_10_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_5 > 4 THEN
SET q11_i1 = RS_q6_r5_col1;
SET QUERY_ID_10 = 10;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q11_i1);
SET M_I_RS_11_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_5 > 5 THEN
SET q12_i1 = RS_q6_r6_col1;
SET QUERY_ID_11 = 11;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q12_i1);
SET M_I_RS_12_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_5 > 6 THEN
SET q13_i1 = RS_q6_r7_col1;
SET QUERY_ID_12 = 12;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q13_i1);
SET M_I_RS_13_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_5 > 7 THEN
SET q14_i1 = RS_q6_r8_col1;
SET QUERY_ID_13 = 13;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q14_i1);
SET M_I_RS_14_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_5 > 8 THEN
SET q15_i1 = RS_q6_r9_col1;
SET QUERY_ID_14 = 14;
SET indicator_14 = 0;
SET cursor_cnt_14 = 0;
BEGIN
DECLARE cursor_14 CURSOR FOR SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q15_i1);
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_14 = 1;
OPEN cursor_14;
loop_14: LOOP
IF cursor_cnt_14=0 THEN
FETCH cursor_14 INTO RS_q15_r1_col1, RS_q15_r1_col2, RS_q15_r1_col3, RS_q15_r1_col4, RS_q15_r1_col5, RS_q15_r1_col6, RS_q15_r1_col7, RS_q15_r1_col8, RS_q15_r1_col9, RS_q15_r1_col10, RS_q15_r1_col11;
END IF;
IF cursor_cnt_14>=1 THEN
CLOSE cursor_14; LEAVE loop_14;END IF;
IF indicator_14=1 THEN CLOSE cursor_14; LEAVE loop_14; END IF;
SET cursor_cnt_14 = cursor_cnt_14 + 1;
END LOOP loop_14;
END;
SET cursor_cnt_14 = FOUND_ROWS();
SELECT cursor_cnt_14,RS_q15_r1_col1,RS_q15_r1_col2,RS_q15_r1_col3,RS_q15_r1_col4,RS_q15_r1_col5,RS_q15_r1_col6,RS_q15_r1_col7,RS_q15_r1_col8,RS_q15_r1_col9,RS_q15_r1_col10,RS_q15_r1_col11;
SET M_I_RS_15_size = cursor_cnt_14;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_5 > 9 THEN
SET q16_i1 = RS_q6_r10_col1;
SET QUERY_ID_15 = 15;
SET indicator_15 = 0;
SET cursor_cnt_15 = 0;
BEGIN
DECLARE cursor_15 CURSOR FOR SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q16_i1);
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_15 = 1;
OPEN cursor_15;
loop_15: LOOP
IF cursor_cnt_15=0 THEN
FETCH cursor_15 INTO RS_q16_r1_col1, RS_q16_r1_col2, RS_q16_r1_col3, RS_q16_r1_col4, RS_q16_r1_col5, RS_q16_r1_col6, RS_q16_r1_col7, RS_q16_r1_col8, RS_q16_r1_col9, RS_q16_r1_col10, RS_q16_r1_col11;
END IF;
IF cursor_cnt_15>=1 THEN
CLOSE cursor_15; LEAVE loop_15;END IF;
IF indicator_15=1 THEN CLOSE cursor_15; LEAVE loop_15; END IF;
SET cursor_cnt_15 = cursor_cnt_15 + 1;
END LOOP loop_15;
END;
SET cursor_cnt_15 = FOUND_ROWS();
SELECT cursor_cnt_15,RS_q16_r1_col1,RS_q16_r1_col2,RS_q16_r1_col3,RS_q16_r1_col4,RS_q16_r1_col5,RS_q16_r1_col6,RS_q16_r1_col7,RS_q16_r1_col8,RS_q16_r1_col9,RS_q16_r1_col10,RS_q16_r1_col11;
SET M_I_RS_16_size = cursor_cnt_15;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_14 > 0 AND cursor_cnt_15 > 0 THEN
SET q17_i1 = RS_q15_r1_col1;
SET q17_i2 = RS_q16_r1_col1;
SET QUERY_ID_16 = 16;
SET indicator_16 = 0;
SET cursor_cnt_16 = 0;
BEGIN
DECLARE cursor_16 CURSOR FOR SELECT m.id, m.root_of_replyof FROM jac_snb_message_mirror m WHERE m.id IN (q17_i1, q17_i2) AND m.root_of_replyof IS NOT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_16 = 1;
OPEN cursor_16;
loop_16: LOOP
IF cursor_cnt_16=0 THEN
FETCH cursor_16 INTO RS_q17_r1_col1, RS_q17_r1_col2;
END IF;
IF cursor_cnt_16=1 THEN
FETCH cursor_16 INTO RS_q17_r2_col1, RS_q17_r2_col2;
END IF;
IF cursor_cnt_16>=2 THEN
CLOSE cursor_16; LEAVE loop_16;END IF;
IF indicator_16=1 THEN CLOSE cursor_16; LEAVE loop_16; END IF;
SET cursor_cnt_16 = cursor_cnt_16 + 1;
END LOOP loop_16;
END;
SET cursor_cnt_16 = FOUND_ROWS();
SELECT cursor_cnt_16,RS_q17_r1_col1,RS_q17_r1_col2,RS_q17_r2_col1,RS_q17_r2_col2;
SET M_I_RS_17_size = cursor_cnt_16;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_16 > 1 THEN
SET q18_i1 = RS_q17_r1_col2;
SET q18_i2 = RS_q17_r2_col2;
SET QUERY_ID_17 = 17;
SET indicator_17 = 0;
SET cursor_cnt_17 = 0;
BEGIN
DECLARE cursor_17 CURSOR FOR SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q18_i1, q18_i2);
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_17 = 1;
OPEN cursor_17;
loop_17: LOOP
IF cursor_cnt_17=0 THEN
FETCH cursor_17 INTO RS_q18_r1_col1, RS_q18_r1_col2, RS_q18_r1_col3, RS_q18_r1_col4, RS_q18_r1_col5, RS_q18_r1_col6, RS_q18_r1_col7, RS_q18_r1_col8, RS_q18_r1_col9, RS_q18_r1_col10, RS_q18_r1_col11;
END IF;
IF cursor_cnt_17=1 THEN
FETCH cursor_17 INTO RS_q18_r2_col1, RS_q18_r2_col2, RS_q18_r2_col3, RS_q18_r2_col4, RS_q18_r2_col5, RS_q18_r2_col6, RS_q18_r2_col7, RS_q18_r2_col8, RS_q18_r2_col9, RS_q18_r2_col10, RS_q18_r2_col11;
END IF;
IF cursor_cnt_17>=2 THEN
CLOSE cursor_17; LEAVE loop_17;END IF;
IF indicator_17=1 THEN CLOSE cursor_17; LEAVE loop_17; END IF;
SET cursor_cnt_17 = cursor_cnt_17 + 1;
END LOOP loop_17;
END;
SET cursor_cnt_17 = FOUND_ROWS();
SELECT cursor_cnt_17,RS_q18_r1_col1,RS_q18_r1_col2,RS_q18_r1_col3,RS_q18_r1_col4,RS_q18_r1_col5,RS_q18_r1_col6,RS_q18_r1_col7,RS_q18_r1_col8,RS_q18_r1_col9,RS_q18_r1_col10,RS_q18_r1_col11,RS_q18_r2_col1,RS_q18_r2_col2,RS_q18_r2_col3,RS_q18_r2_col4,RS_q18_r2_col5,RS_q18_r2_col6,RS_q18_r2_col7,RS_q18_r2_col8,RS_q18_r2_col9,RS_q18_r2_col10,RS_q18_r2_col11;
SET M_I_RS_18_size = cursor_cnt_17;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_17 > 1 THEN
SET q19_i1 = RS_q18_r2_col1;
SET q19_i2 = RS_q18_r1_col1;
SET q19_i3 = RS_q18_r2_col1;
SET q19_i4 = RS_q18_r1_col1;
SET q19_i5 = RS_q18_r2_col1;
SET q19_i6 = RS_q18_r1_col1;
SET QUERY_ID_18 = 18;
SET indicator_18 = 0;
SET cursor_cnt_18 = 0;
BEGIN
DECLARE cursor_18 CURSOR FOR SELECT n.id, e.id FROM anchors e JOIN anchors n ON n.id = CASE  WHEN e.src IN (q19_i1, q19_i2) THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' WHERE e.kind = 'EdgeAnchor' AND (e.arch_type = 'HasCreator' OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = 'HasCreator' )) AND (e.src IN (q19_i3, q19_i4) OR (e.undirected = 1 AND e.dst IN (q19_i5, q19_i6))) ORDER BY e.seq, e.id;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_18 = 1;
OPEN cursor_18;
loop_18: LOOP
IF cursor_cnt_18=0 THEN
FETCH cursor_18 INTO RS_q19_r1_col1, RS_q19_r1_col2;
END IF;
IF cursor_cnt_18=1 THEN
FETCH cursor_18 INTO RS_q19_r2_col1, RS_q19_r2_col2;
END IF;
IF cursor_cnt_18>=2 THEN
CLOSE cursor_18; LEAVE loop_18;END IF;
IF indicator_18=1 THEN CLOSE cursor_18; LEAVE loop_18; END IF;
SET cursor_cnt_18 = cursor_cnt_18 + 1;
END LOOP loop_18;
END;
SET cursor_cnt_18 = FOUND_ROWS();
SELECT cursor_cnt_18,RS_q19_r1_col1,RS_q19_r1_col2,RS_q19_r2_col1,RS_q19_r2_col2;
SET M_I_RS_19_size = cursor_cnt_18;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_18 > 1 THEN
SET q20_i1 = RS_q19_r1_col2;
SET q20_i2 = RS_q19_r2_col2;
SET QUERY_ID_19 = 19;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q20_i1, q20_i2);
SET M_I_RS_20_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_18 > 1 THEN
SET q21_i1 = RS_q19_r1_col1;
SET q21_i2 = RS_q19_r2_col1;
SET QUERY_ID_20 = 20;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q21_i1, q21_i2);
SET M_I_RS_21_size = FOUND_ROWS();
END IF;
END IF;
SELECT QUERY_ID_0,q1_i1,QUERY_ID_1,q2_i1,QUERY_ID_2,q3_i1,QUERY_ID_3,q4_i1,QUERY_ID_4,q5_i1,QUERY_ID_5,q6_i1,q6_i2,q6_i3,q6_i4,q6_i5,q6_i6,QUERY_ID_6,q7_i1,QUERY_ID_7,q8_i1,QUERY_ID_8,q9_i1,QUERY_ID_9,q10_i1,QUERY_ID_10,q11_i1,QUERY_ID_11,q12_i1,QUERY_ID_12,q13_i1,QUERY_ID_13,q14_i1,QUERY_ID_14,q15_i1,QUERY_ID_15,q16_i1,QUERY_ID_16,q17_i1,q17_i2,QUERY_ID_17,q18_i1,q18_i2,QUERY_ID_18,q19_i1,q19_i2,q19_i3,q19_i4,q19_i5,q19_i6,QUERY_ID_19,q20_i1,q20_i2,QUERY_ID_20,q21_i1,q21_i2;

END $$
DELIMITER ;