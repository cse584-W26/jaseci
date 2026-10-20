DROP PROCEDURE IF EXISTS `Snb_is3_full_b0b2a6869e_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE Snb_is3_full_b0b2a6869e_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_person_jid VARCHAR(512))
BEGIN

DECLARE q1_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE M_I_RS_1_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;
DECLARE q2_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_1 INT DEFAULT NULL;
DECLARE RS_q2_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col3 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col4 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col5 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col6 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col7 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col8 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col9 BOOLEAN DEFAULT NULL;
DECLARE RS_q2_r1_col10 LONGTEXT DEFAULT NULL;
DECLARE RS_q2_r1_col11 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_2_size INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;
DECLARE cursor_1 int DEFAULT NULL;
DECLARE indicator_1 int DEFAULT NULL;
DECLARE q3_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_2 INT DEFAULT NULL;
DECLARE M_I_RS_3_size INT DEFAULT NULL;
DECLARE cursor_cnt_2 INT DEFAULT NULL;
DECLARE q4_i1 LONGTEXT DEFAULT NULL;
DECLARE q4_i2 LONGTEXT DEFAULT NULL;
DECLARE q4_i3 LONGTEXT DEFAULT NULL;
DECLARE QUERY_ID_3 INT DEFAULT NULL;
DECLARE M_I_RS_4_size INT DEFAULT NULL;
DECLARE cursor_cnt_3 INT DEFAULT NULL;
DECLARE q5_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_4 INT DEFAULT NULL;
DECLARE M_I_RS_5_size INT DEFAULT NULL;
DECLARE cursor_cnt_4 INT DEFAULT NULL;
DECLARE q6_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_5 INT DEFAULT NULL;
DECLARE M_I_RS_6_size INT DEFAULT NULL;
DECLARE cursor_cnt_5 INT DEFAULT NULL;
DECLARE q7_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i6 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i7 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i8 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i9 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i10 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i11 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i12 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i13 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_6 INT DEFAULT NULL;
DECLARE M_I_RS_7_size INT DEFAULT NULL;
DECLARE cursor_cnt_6 INT DEFAULT NULL;
DECLARE q8_i1 LONGTEXT DEFAULT NULL;
DECLARE q8_i2 LONGTEXT DEFAULT NULL;
DECLARE q8_i3 LONGTEXT DEFAULT NULL;
DECLARE QUERY_ID_7 INT DEFAULT NULL;
DECLARE M_I_RS_8_size INT DEFAULT NULL;
DECLARE cursor_cnt_7 INT DEFAULT NULL;
DECLARE q9_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i6 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i7 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i8 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i9 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i10 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i11 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i12 VARCHAR(512) DEFAULT NULL;
DECLARE q9_i13 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_8 INT DEFAULT NULL;
DECLARE M_I_RS_9_size INT DEFAULT NULL;
DECLARE cursor_cnt_8 INT DEFAULT NULL;

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
DECLARE cursor_1 CURSOR FOR SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q2_i1);
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_1 = 1;
OPEN cursor_1;
loop_1: LOOP
IF cursor_cnt_1=0 THEN
FETCH cursor_1 INTO RS_q2_r1_col1, RS_q2_r1_col2, RS_q2_r1_col3, RS_q2_r1_col4, RS_q2_r1_col5, RS_q2_r1_col6, RS_q2_r1_col7, RS_q2_r1_col8, RS_q2_r1_col9, RS_q2_r1_col10, RS_q2_r1_col11;
END IF;
IF cursor_cnt_1>=1 THEN
CLOSE cursor_1; LEAVE loop_1;END IF;
IF indicator_1=1 THEN CLOSE cursor_1; LEAVE loop_1; END IF;
SET cursor_cnt_1 = cursor_cnt_1 + 1;
END LOOP loop_1;
END;
SET cursor_cnt_1 = FOUND_ROWS();
SELECT cursor_cnt_1,RS_q2_r1_col1,RS_q2_r1_col2,RS_q2_r1_col3,RS_q2_r1_col4,RS_q2_r1_col5,RS_q2_r1_col6,RS_q2_r1_col7,RS_q2_r1_col8,RS_q2_r1_col9,RS_q2_r1_col10,RS_q2_r1_col11;
SET M_I_RS_2_size = cursor_cnt_1;
END IF;
IF TRUE THEN
SET q3_i1 = 'Person';
SET QUERY_ID_2 = 2;
SELECT type_name FROM graph_types WHERE ancestor = q3_i1;
SET M_I_RS_3_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q4_i1 = '4bc418b3-c394-41ee-93fd-4a13a6c852a8';
SET q4_i2 = '4bc418b3-c394-41ee-93fd-4a13a6c852a8';
SET q4_i3 = '4bc418b3-c394-41ee-93fd-4a13a6c852a8';
SET QUERY_ID_3 = 3;
SELECT a.id , CASE  WHEN JSON_TYPE(JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', q4_i1, '"'))) IN ('INTEGER', 'DOUBLE') THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', q4_i2, '"'))) AS SIGNED) END AS root_grant , CASE  WHEN JSON_TYPE(JSON_EXTRACT(a.props, '$.access.all')) IN ('INTEGER', 'DOUBLE') THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props, '$.access.all')) AS SIGNED) ELSE -1 END AS global_grant FROM anchors a WHERE a.kind = 'NodeAnchor' AND a.arch_type = 'Root' AND (JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', q4_i3, '"')) IS NOT NULL OR JSON_TYPE(JSON_EXTRACT(a.props, '$.access.all')) IN ('INTEGER', 'DOUBLE'));
SET M_I_RS_4_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q5_i1 = '__guest__';
SET QUERY_ID_4 = 4;
SELECT doc FROM identity_users WHERE user_id = q5_i1;
SET M_I_RS_5_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q6_i1 = '__guest__';
SET QUERY_ID_5 = 5;
SELECT t.doc FROM identity_users t JOIN identity_lookups lk ON t.user_id = lk.user_id WHERE lk.value_normalized = q6_i1 AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(t.doc, '$.status')), 'active') <> 'disabled';
SET M_I_RS_6_size = FOUND_ROWS();
END IF;
IF TRUE THEN
IF cursor_cnt_1 > 0 THEN
SET q7_i1 = RS_q2_r1_col1;
SET q7_i2 = 'Knows';
SET q7_i3 = 'Knows';
SET q7_i4 = 'Person';
SET q7_i5 = 'Person';
SET q7_i6 = RS_q2_r1_col1;
SET q7_i7 = 'Knows';
SET q7_i8 = 'Knows';
SET q7_i9 = 'Person';
SET q7_i10 = 'Person';
SET q7_i11 = RS_q2_r1_col1;
SET q7_i12 = 'Person';
SET q7_i13 = 'Person';
SET QUERY_ID_6 = 6;
SELECT n.id, e.id, n.props, n.root_id FROM ( SELECT e.* FROM anchors e WHERE e.src = q7_i1 AND e.kind = 'EdgeAnchor' AND (e.arch_type = q7_i2 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q7_i3 )) AND (e.dst_type IS NULL OR e.dst_type = q7_i4 OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q7_i5 )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = q7_i6 AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = q7_i7 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q7_i8 )) AND (e.src_type IS NULL OR e.src_type = q7_i9 OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q7_i10 )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = q7_i11 THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = q7_i12 OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q7_i13 )) ORDER BY e.seq, e.id;
SET M_I_RS_7_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
SET q8_i1 = '4bc418b3-c394-41ee-93fd-4a13a6c852a8';
SET q8_i2 = '4bc418b3-c394-41ee-93fd-4a13a6c852a8';
SET q8_i3 = '4bc418b3-c394-41ee-93fd-4a13a6c852a8';
SET QUERY_ID_7 = 7;
SELECT a.id , CASE  WHEN JSON_TYPE(JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', q8_i1, '"'))) IN ('INTEGER', 'DOUBLE') THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', q8_i2, '"'))) AS SIGNED) END AS root_grant , CASE  WHEN JSON_TYPE(JSON_EXTRACT(a.props, '$.access.all')) IN ('INTEGER', 'DOUBLE') THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props, '$.access.all')) AS SIGNED) ELSE -1 END AS global_grant FROM anchors a WHERE a.kind = 'NodeAnchor' AND a.arch_type = 'Root' AND (JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', q8_i3, '"')) IS NOT NULL OR JSON_TYPE(JSON_EXTRACT(a.props, '$.access.all')) IN ('INTEGER', 'DOUBLE'));
SET M_I_RS_8_size = FOUND_ROWS();
END IF;
IF TRUE THEN
IF cursor_cnt_1 > 0 THEN
SET q9_i1 = RS_q2_r1_col1;
SET q9_i2 = 'Knows';
SET q9_i3 = 'Knows';
SET q9_i4 = 'Person';
SET q9_i5 = 'Person';
SET q9_i6 = RS_q2_r1_col1;
SET q9_i7 = 'Knows';
SET q9_i8 = 'Knows';
SET q9_i9 = 'Person';
SET q9_i10 = 'Person';
SET q9_i11 = RS_q2_r1_col1;
SET q9_i12 = 'Person';
SET q9_i13 = 'Person';
SET QUERY_ID_8 = 8;
SELECT n.id, e.id, n.props, n.root_id FROM ( SELECT e.* FROM anchors e WHERE e.dst = q9_i1 AND e.kind = 'EdgeAnchor' AND (e.arch_type = q9_i2 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q9_i3 )) AND (e.src_type IS NULL OR e.src_type = q9_i4 OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q9_i5 )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = q9_i6 AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = q9_i7 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q9_i8 )) AND (e.dst_type IS NULL OR e.dst_type = q9_i9 OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q9_i10 )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = q9_i11 THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = q9_i12 OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q9_i13 )) ORDER BY e.seq, e.id;
SET M_I_RS_9_size = FOUND_ROWS();
END IF;
END IF;
SELECT QUERY_ID_0,q1_i1,QUERY_ID_1,q2_i1,QUERY_ID_2,q3_i1,QUERY_ID_3,q4_i1,q4_i2,q4_i3,QUERY_ID_4,q5_i1,QUERY_ID_5,q6_i1,QUERY_ID_6,q7_i1,q7_i2,q7_i3,q7_i4,q7_i5,q7_i6,q7_i7,q7_i8,q7_i9,q7_i10,q7_i11,q7_i12,q7_i13,QUERY_ID_7,q8_i1,q8_i2,q8_i3,QUERY_ID_8,q9_i1,q9_i2,q9_i3,q9_i4,q9_i5,q9_i6,q9_i7,q9_i8,q9_i9,q9_i10,q9_i11,q9_i12,q9_i13;

END $$
DELIMITER ;