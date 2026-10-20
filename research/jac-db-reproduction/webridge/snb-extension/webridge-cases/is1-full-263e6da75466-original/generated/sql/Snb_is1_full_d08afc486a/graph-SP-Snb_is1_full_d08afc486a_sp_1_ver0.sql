DROP PROCEDURE IF EXISTS `Snb_is1_full_d08afc486a_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE Snb_is1_full_d08afc486a_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_person_jid VARCHAR(512))
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
DECLARE q3_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i6 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i7 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i8 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i9 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i10 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i11 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i12 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i13 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_2 INT DEFAULT NULL;
DECLARE RS_q3_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_3_size INT DEFAULT NULL;
DECLARE cursor_cnt_2 INT DEFAULT NULL;
DECLARE cursor_2 int DEFAULT NULL;
DECLARE indicator_2 int DEFAULT NULL;
DECLARE q4_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_3 INT DEFAULT NULL;
DECLARE M_I_RS_4_size INT DEFAULT NULL;
DECLARE cursor_cnt_3 INT DEFAULT NULL;

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
IF cursor_cnt_1 > 0 THEN
SET q3_i1 = RS_q2_r1_col1;
SET q3_i2 = 'IsLocatedIn';
SET q3_i3 = 'IsLocatedIn';
SET q3_i4 = 'Place';
SET q3_i5 = 'Place';
SET q3_i6 = RS_q2_r1_col1;
SET q3_i7 = 'IsLocatedIn';
SET q3_i8 = 'IsLocatedIn';
SET q3_i9 = 'Place';
SET q3_i10 = 'Place';
SET q3_i11 = RS_q2_r1_col1;
SET q3_i12 = 'Place';
SET q3_i13 = 'Place';
SET QUERY_ID_2 = 2;
SET indicator_2 = 0;
SET cursor_cnt_2 = 0;
BEGIN
DECLARE cursor_2 CURSOR FOR SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = q3_i1 AND e.kind = 'EdgeAnchor' AND (e.arch_type = q3_i2 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q3_i3 )) AND (e.dst_type IS NULL OR e.dst_type = q3_i4 OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q3_i5 )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = q3_i6 AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = q3_i7 OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q3_i8 )) AND (e.src_type IS NULL OR e.src_type = q3_i9 OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q3_i10 )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = q3_i11 THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = q3_i12 OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q3_i13 )) ORDER BY e.seq, e.id;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_2 = 1;
OPEN cursor_2;
loop_2: LOOP
IF cursor_cnt_2=0 THEN
FETCH cursor_2 INTO RS_q3_r1_col1, RS_q3_r1_col2;
END IF;
IF cursor_cnt_2>=1 THEN
CLOSE cursor_2; LEAVE loop_2;END IF;
IF indicator_2=1 THEN CLOSE cursor_2; LEAVE loop_2; END IF;
SET cursor_cnt_2 = cursor_cnt_2 + 1;
END LOOP loop_2;
END;
SET cursor_cnt_2 = FOUND_ROWS();
SELECT cursor_cnt_2,RS_q3_r1_col1,RS_q3_r1_col2;
SET M_I_RS_3_size = cursor_cnt_2;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_2 > 0 THEN
SET q4_i1 = RS_q3_r1_col1;
SET QUERY_ID_3 = 3;
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (q4_i1);
SET M_I_RS_4_size = FOUND_ROWS();
END IF;
END IF;
SELECT QUERY_ID_0,q1_i1,QUERY_ID_1,q2_i1,QUERY_ID_2,q3_i1,q3_i2,q3_i3,q3_i4,q3_i5,q3_i6,q3_i7,q3_i8,q3_i9,q3_i10,q3_i11,q3_i12,q3_i13,QUERY_ID_3,q4_i1;

END $$
DELIMITER ;