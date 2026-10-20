DROP PROCEDURE IF EXISTS `Snb_ic2_pruned_fbf5b8e7ed_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE Snb_ic2_pruned_fbf5b8e7ed_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_person_jid VARCHAR(512), IN M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value BIGINT)
BEGIN

DECLARE q1_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i6 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i7 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i8 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i9 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i10 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i11 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i12 VARCHAR(512) DEFAULT NULL;
DECLARE q1_i13 VARCHAR(512) DEFAULT NULL;
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
DECLARE M_I_RS_2_size INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;
DECLARE cursor_1 int DEFAULT NULL;
DECLARE indicator_1 int DEFAULT NULL;
DECLARE q3_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i3 BIGINT DEFAULT NULL;
DECLARE q3_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i6 BIGINT DEFAULT NULL;
DECLARE q3_i7 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i8 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i9 BIGINT DEFAULT NULL;
DECLARE q3_i10 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i11 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i12 BIGINT DEFAULT NULL;
DECLARE q3_i13 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i14 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i15 BIGINT DEFAULT NULL;
DECLARE q3_i16 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i17 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i18 BIGINT DEFAULT NULL;
DECLARE q3_i19 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i20 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i21 BIGINT DEFAULT NULL;
DECLARE q3_i22 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i23 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i24 BIGINT DEFAULT NULL;
DECLARE q3_i25 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i26 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i27 BIGINT DEFAULT NULL;
DECLARE q3_i28 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i29 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i30 BIGINT DEFAULT NULL;
DECLARE q3_i31 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i32 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i33 BIGINT DEFAULT NULL;
DECLARE q3_i34 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i35 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i36 BIGINT DEFAULT NULL;
DECLARE q3_i37 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i38 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i39 BIGINT DEFAULT NULL;
DECLARE q3_i40 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i41 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i42 BIGINT DEFAULT NULL;
DECLARE q3_i43 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i44 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i45 BIGINT DEFAULT NULL;
DECLARE q3_i46 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i47 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i48 BIGINT DEFAULT NULL;
DECLARE q3_i49 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i50 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i51 BIGINT DEFAULT NULL;
DECLARE q3_i52 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i53 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i54 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_2 INT DEFAULT NULL;
DECLARE RS_q3_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r1_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r2_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r2_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r2_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r3_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r3_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r3_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r4_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r4_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r4_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r5_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r5_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r5_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r6_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r6_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r6_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r7_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r7_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r7_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r8_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r8_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r8_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r9_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r9_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r9_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r10_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r10_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r10_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r11_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r11_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r11_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r12_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r12_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r12_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r13_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r13_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r13_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r14_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r14_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r14_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r15_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r15_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r15_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r16_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r16_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r16_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r17_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r17_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r17_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r18_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r18_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r18_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r19_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r19_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r19_col3 LONGTEXT DEFAULT NULL;
DECLARE RS_q3_r20_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r20_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r20_col3 LONGTEXT DEFAULT NULL;
DECLARE M_I_RS_3_size INT DEFAULT NULL;
DECLARE cursor_cnt_2 INT DEFAULT NULL;
DECLARE cursor_2 int DEFAULT NULL;
DECLARE indicator_2 int DEFAULT NULL;
DECLARE q4_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i6 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i7 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i8 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i9 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i10 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i11 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i12 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i13 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i14 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i15 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i16 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i17 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i18 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i19 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i20 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_3 INT DEFAULT NULL;
DECLARE M_I_RS_4_size INT DEFAULT NULL;
DECLARE cursor_cnt_3 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET q1_i2 = 'Knows';
SET q1_i3 = 'Knows';
SET q1_i4 = 'Person';
SET q1_i5 = 'Person';
SET q1_i6 = M_L_String__REQUEST_PARAM_person_jid;
SET q1_i7 = 'Knows';
SET q1_i8 = 'Knows';
SET q1_i9 = 'Person';
SET q1_i10 = 'Person';
SET q1_i11 = M_L_String__REQUEST_PARAM_person_jid;
SET q1_i12 = 'Person';
SET q1_i13 = 'Person';
SET QUERY_ID_0 = 0;
SELECT n.id, e.id, JSON_EXTRACT(n.props, '$.archetype') FROM ( SELECT e.* FROM anchors e WHERE e.src = q1_i1 AND e.kind = 'EdgeAnchor' AND (e.arch_type = q1_i2 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q1_i3 )) AND (e.dst_type IS NULL OR e.dst_type = q1_i4 OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q1_i5 )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = q1_i6 AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = q1_i7 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q1_i8 )) AND (e.src_type IS NULL OR e.src_type = q1_i9 OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q1_i10 )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = q1_i11 THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = q1_i12 OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q1_i13 )) ORDER BY e.seq, e.id;
SET M_I_RS_1_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q2_i1 = M_L_String__REQUEST_PARAM_person_jid;
SET q2_i2 = 'Knows';
SET q2_i3 = 'Knows';
SET q2_i4 = 'Person';
SET q2_i5 = 'Person';
SET q2_i6 = M_L_String__REQUEST_PARAM_person_jid;
SET q2_i7 = 'Knows';
SET q2_i8 = 'Knows';
SET q2_i9 = 'Person';
SET q2_i10 = 'Person';
SET q2_i11 = M_L_String__REQUEST_PARAM_person_jid;
SET q2_i12 = 'Person';
SET q2_i13 = 'Person';
SET QUERY_ID_1 = 1;
SET indicator_1 = 0;
SET cursor_cnt_1 = 0;
BEGIN
DECLARE cursor_1 CURSOR FOR SELECT n.id, e.id, JSON_EXTRACT(n.props, '$.archetype') FROM ( SELECT e.* FROM anchors e WHERE e.dst = q2_i1 AND e.kind = 'EdgeAnchor' AND (e.arch_type = q2_i2 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i3 )) AND (e.src_type IS NULL OR e.src_type = q2_i4 OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i5 )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = q2_i6 AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = q2_i7 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i8 )) AND (e.dst_type IS NULL OR e.dst_type = q2_i9 OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i10 )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = q2_i11 THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = q2_i12 OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i13 )) ORDER BY e.seq, e.id;
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
IF cursor_cnt_1>=9 THEN
CLOSE cursor_1; LEAVE loop_1;END IF;
IF indicator_1=1 THEN CLOSE cursor_1; LEAVE loop_1; END IF;
SET cursor_cnt_1 = cursor_cnt_1 + 1;
END LOOP loop_1;
END;
SET cursor_cnt_1 = FOUND_ROWS();
SELECT cursor_cnt_1,RS_q2_r1_col1,RS_q2_r1_col2,RS_q2_r1_col3,RS_q2_r2_col1,RS_q2_r2_col2,RS_q2_r2_col3,RS_q2_r3_col1,RS_q2_r3_col2,RS_q2_r3_col3,RS_q2_r4_col1,RS_q2_r4_col2,RS_q2_r4_col3,RS_q2_r5_col1,RS_q2_r5_col2,RS_q2_r5_col3,RS_q2_r6_col1,RS_q2_r6_col2,RS_q2_r6_col3,RS_q2_r7_col1,RS_q2_r7_col2,RS_q2_r7_col3,RS_q2_r8_col1,RS_q2_r8_col2,RS_q2_r8_col3,RS_q2_r9_col1,RS_q2_r9_col2,RS_q2_r9_col3;
SET M_I_RS_2_size = cursor_cnt_1;
END IF;
IF TRUE THEN
IF cursor_cnt_1 > 8 THEN
SET q3_i1 = RS_q2_r1_col1;
SET q3_i2 = 'Post';
SET q3_i3 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i4 = RS_q2_r1_col1;
SET q3_i5 = 'Comment';
SET q3_i6 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i7 = RS_q2_r2_col1;
SET q3_i8 = 'Post';
SET q3_i9 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i10 = RS_q2_r2_col1;
SET q3_i11 = 'Comment';
SET q3_i12 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i13 = RS_q2_r3_col1;
SET q3_i14 = 'Post';
SET q3_i15 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i16 = RS_q2_r3_col1;
SET q3_i17 = 'Comment';
SET q3_i18 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i19 = RS_q2_r4_col1;
SET q3_i20 = 'Post';
SET q3_i21 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i22 = RS_q2_r4_col1;
SET q3_i23 = 'Comment';
SET q3_i24 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i25 = RS_q2_r5_col1;
SET q3_i26 = 'Post';
SET q3_i27 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i28 = RS_q2_r5_col1;
SET q3_i29 = 'Comment';
SET q3_i30 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i31 = RS_q2_r6_col1;
SET q3_i32 = 'Post';
SET q3_i33 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i34 = RS_q2_r6_col1;
SET q3_i35 = 'Comment';
SET q3_i36 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i37 = RS_q2_r7_col1;
SET q3_i38 = 'Post';
SET q3_i39 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i40 = RS_q2_r7_col1;
SET q3_i41 = 'Comment';
SET q3_i42 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i43 = RS_q2_r8_col1;
SET q3_i44 = 'Post';
SET q3_i45 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i46 = RS_q2_r8_col1;
SET q3_i47 = 'Comment';
SET q3_i48 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i49 = RS_q2_r9_col1;
SET q3_i50 = 'Post';
SET q3_i51 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET q3_i52 = RS_q2_r9_col1;
SET q3_i53 = 'Comment';
SET q3_i54 = M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value;
SET QUERY_ID_2 = 2;
SET indicator_2 = 0;
SET cursor_cnt_2 = 0;
BEGIN
DECLARE cursor_2 CURSOR FOR SELECT id, arch_type, props FROM ( (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i1 AND m.arch_type = q3_i2 AND m.creation_date <= q3_i3 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i4 AND m.arch_type = q3_i5 AND m.creation_date <= q3_i6 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i7 AND m.arch_type = q3_i8 AND m.creation_date <= q3_i9 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i10 AND m.arch_type = q3_i11 AND m.creation_date <= q3_i12 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i13 AND m.arch_type = q3_i14 AND m.creation_date <= q3_i15 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i16 AND m.arch_type = q3_i17 AND m.creation_date <= q3_i18 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i19 AND m.arch_type = q3_i20 AND m.creation_date <= q3_i21 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i22 AND m.arch_type = q3_i23 AND m.creation_date <= q3_i24 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i25 AND m.arch_type = q3_i26 AND m.creation_date <= q3_i27 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i28 AND m.arch_type = q3_i29 AND m.creation_date <= q3_i30 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i31 AND m.arch_type = q3_i32 AND m.creation_date <= q3_i33 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i34 AND m.arch_type = q3_i35 AND m.creation_date <= q3_i36 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i37 AND m.arch_type = q3_i38 AND m.creation_date <= q3_i39 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i40 AND m.arch_type = q3_i41 AND m.creation_date <= q3_i42 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i43 AND m.arch_type = q3_i44 AND m.creation_date <= q3_i45 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i46 AND m.arch_type = q3_i47 AND m.creation_date <= q3_i48 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i49 AND m.arch_type = q3_i50 AND m.creation_date <= q3_i51 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = q3_i52 AND m.arch_type = q3_i53 AND m.creation_date <= q3_i54 ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) ) u ORDER BY ord DESC, tie ASC LIMIT 20;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_2 = 1;
OPEN cursor_2;
loop_2: LOOP
IF cursor_cnt_2=0 THEN
FETCH cursor_2 INTO RS_q3_r1_col1, RS_q3_r1_col2, RS_q3_r1_col3;
END IF;
IF cursor_cnt_2=1 THEN
FETCH cursor_2 INTO RS_q3_r2_col1, RS_q3_r2_col2, RS_q3_r2_col3;
END IF;
IF cursor_cnt_2=2 THEN
FETCH cursor_2 INTO RS_q3_r3_col1, RS_q3_r3_col2, RS_q3_r3_col3;
END IF;
IF cursor_cnt_2=3 THEN
FETCH cursor_2 INTO RS_q3_r4_col1, RS_q3_r4_col2, RS_q3_r4_col3;
END IF;
IF cursor_cnt_2=4 THEN
FETCH cursor_2 INTO RS_q3_r5_col1, RS_q3_r5_col2, RS_q3_r5_col3;
END IF;
IF cursor_cnt_2=5 THEN
FETCH cursor_2 INTO RS_q3_r6_col1, RS_q3_r6_col2, RS_q3_r6_col3;
END IF;
IF cursor_cnt_2=6 THEN
FETCH cursor_2 INTO RS_q3_r7_col1, RS_q3_r7_col2, RS_q3_r7_col3;
END IF;
IF cursor_cnt_2=7 THEN
FETCH cursor_2 INTO RS_q3_r8_col1, RS_q3_r8_col2, RS_q3_r8_col3;
END IF;
IF cursor_cnt_2=8 THEN
FETCH cursor_2 INTO RS_q3_r9_col1, RS_q3_r9_col2, RS_q3_r9_col3;
END IF;
IF cursor_cnt_2=9 THEN
FETCH cursor_2 INTO RS_q3_r10_col1, RS_q3_r10_col2, RS_q3_r10_col3;
END IF;
IF cursor_cnt_2=10 THEN
FETCH cursor_2 INTO RS_q3_r11_col1, RS_q3_r11_col2, RS_q3_r11_col3;
END IF;
IF cursor_cnt_2=11 THEN
FETCH cursor_2 INTO RS_q3_r12_col1, RS_q3_r12_col2, RS_q3_r12_col3;
END IF;
IF cursor_cnt_2=12 THEN
FETCH cursor_2 INTO RS_q3_r13_col1, RS_q3_r13_col2, RS_q3_r13_col3;
END IF;
IF cursor_cnt_2=13 THEN
FETCH cursor_2 INTO RS_q3_r14_col1, RS_q3_r14_col2, RS_q3_r14_col3;
END IF;
IF cursor_cnt_2=14 THEN
FETCH cursor_2 INTO RS_q3_r15_col1, RS_q3_r15_col2, RS_q3_r15_col3;
END IF;
IF cursor_cnt_2=15 THEN
FETCH cursor_2 INTO RS_q3_r16_col1, RS_q3_r16_col2, RS_q3_r16_col3;
END IF;
IF cursor_cnt_2=16 THEN
FETCH cursor_2 INTO RS_q3_r17_col1, RS_q3_r17_col2, RS_q3_r17_col3;
END IF;
IF cursor_cnt_2=17 THEN
FETCH cursor_2 INTO RS_q3_r18_col1, RS_q3_r18_col2, RS_q3_r18_col3;
END IF;
IF cursor_cnt_2=18 THEN
FETCH cursor_2 INTO RS_q3_r19_col1, RS_q3_r19_col2, RS_q3_r19_col3;
END IF;
IF cursor_cnt_2=19 THEN
FETCH cursor_2 INTO RS_q3_r20_col1, RS_q3_r20_col2, RS_q3_r20_col3;
END IF;
IF cursor_cnt_2>=20 THEN
CLOSE cursor_2; LEAVE loop_2;END IF;
IF indicator_2=1 THEN CLOSE cursor_2; LEAVE loop_2; END IF;
SET cursor_cnt_2 = cursor_cnt_2 + 1;
END LOOP loop_2;
END;
SET cursor_cnt_2 = FOUND_ROWS();
SELECT cursor_cnt_2,RS_q3_r1_col1,RS_q3_r1_col2,RS_q3_r1_col3,RS_q3_r2_col1,RS_q3_r2_col2,RS_q3_r2_col3,RS_q3_r3_col1,RS_q3_r3_col2,RS_q3_r3_col3,RS_q3_r4_col1,RS_q3_r4_col2,RS_q3_r4_col3,RS_q3_r5_col1,RS_q3_r5_col2,RS_q3_r5_col3,RS_q3_r6_col1,RS_q3_r6_col2,RS_q3_r6_col3,RS_q3_r7_col1,RS_q3_r7_col2,RS_q3_r7_col3,RS_q3_r8_col1,RS_q3_r8_col2,RS_q3_r8_col3,RS_q3_r9_col1,RS_q3_r9_col2,RS_q3_r9_col3,RS_q3_r10_col1,RS_q3_r10_col2,RS_q3_r10_col3,RS_q3_r11_col1,RS_q3_r11_col2,RS_q3_r11_col3,RS_q3_r12_col1,RS_q3_r12_col2,RS_q3_r12_col3,RS_q3_r13_col1,RS_q3_r13_col2,RS_q3_r13_col3,RS_q3_r14_col1,RS_q3_r14_col2,RS_q3_r14_col3,RS_q3_r15_col1,RS_q3_r15_col2,RS_q3_r15_col3,RS_q3_r16_col1,RS_q3_r16_col2,RS_q3_r16_col3,RS_q3_r17_col1,RS_q3_r17_col2,RS_q3_r17_col3,RS_q3_r18_col1,RS_q3_r18_col2,RS_q3_r18_col3,RS_q3_r19_col1,RS_q3_r19_col2,RS_q3_r19_col3,RS_q3_r20_col1,RS_q3_r20_col2,RS_q3_r20_col3;
SET M_I_RS_3_size = cursor_cnt_2;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_2 > 19 THEN
SET q4_i1 = RS_q3_r1_col1;
SET q4_i2 = RS_q3_r2_col1;
SET q4_i3 = RS_q3_r3_col1;
SET q4_i4 = RS_q3_r4_col1;
SET q4_i5 = RS_q3_r5_col1;
SET q4_i6 = RS_q3_r6_col1;
SET q4_i7 = RS_q3_r7_col1;
SET q4_i8 = RS_q3_r8_col1;
SET q4_i9 = RS_q3_r9_col1;
SET q4_i10 = RS_q3_r10_col1;
SET q4_i11 = RS_q3_r11_col1;
SET q4_i12 = RS_q3_r12_col1;
SET q4_i13 = RS_q3_r13_col1;
SET q4_i14 = RS_q3_r14_col1;
SET q4_i15 = RS_q3_r15_col1;
SET q4_i16 = RS_q3_r16_col1;
SET q4_i17 = RS_q3_r17_col1;
SET q4_i18 = RS_q3_r18_col1;
SET q4_i19 = RS_q3_r19_col1;
SET q4_i20 = RS_q3_r20_col1;
SET QUERY_ID_3 = 3;
SELECT e.src, n.props FROM anchors e JOIN anchors n ON n.id = e.dst AND n.kind = 'NodeAnchor' WHERE e.kind = 'EdgeAnchor' AND e.arch_type = 'HasCreator' AND e.src IN (q4_i1, q4_i2, q4_i3, q4_i4, q4_i5, q4_i6, q4_i7, q4_i8, q4_i9, q4_i10, q4_i11, q4_i12, q4_i13, q4_i14, q4_i15, q4_i16, q4_i17, q4_i18, q4_i19, q4_i20) ORDER BY e.seq, e.id;
SET M_I_RS_4_size = FOUND_ROWS();
END IF;
END IF;
SELECT QUERY_ID_0,q1_i1,q1_i2,q1_i3,q1_i4,q1_i5,q1_i6,q1_i7,q1_i8,q1_i9,q1_i10,q1_i11,q1_i12,q1_i13,QUERY_ID_1,q2_i1,q2_i2,q2_i3,q2_i4,q2_i5,q2_i6,q2_i7,q2_i8,q2_i9,q2_i10,q2_i11,q2_i12,q2_i13,QUERY_ID_2,q3_i1,q3_i2,q3_i3,q3_i4,q3_i5,q3_i6,q3_i7,q3_i8,q3_i9,q3_i10,q3_i11,q3_i12,q3_i13,q3_i14,q3_i15,q3_i16,q3_i17,q3_i18,q3_i19,q3_i20,q3_i21,q3_i22,q3_i23,q3_i24,q3_i25,q3_i26,q3_i27,q3_i28,q3_i29,q3_i30,q3_i31,q3_i32,q3_i33,q3_i34,q3_i35,q3_i36,q3_i37,q3_i38,q3_i39,q3_i40,q3_i41,q3_i42,q3_i43,q3_i44,q3_i45,q3_i46,q3_i47,q3_i48,q3_i49,q3_i50,q3_i51,q3_i52,q3_i53,q3_i54,QUERY_ID_3,q4_i1,q4_i2,q4_i3,q4_i4,q4_i5,q4_i6,q4_i7,q4_i8,q4_i9,q4_i10,q4_i11,q4_i12,q4_i13,q4_i14,q4_i15,q4_i16,q4_i17,q4_i18,q4_i19,q4_i20;

END $$
DELIMITER ;