DROP PROCEDURE IF EXISTS `LittleX_2ff90374d126_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE LittleX_2ff90374d126_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_actor_id VARCHAR(512), IN M_L_String__REQUEST_PARAM_actor_root_id VARCHAR(512))
BEGIN

DECLARE QUERY_ID_0_TXN INT DEFAULT NULL;
DECLARE q2_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i6 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_1 INT DEFAULT NULL;
DECLARE M_I_RS_2_size INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;
DECLARE q3_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i6 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_2 INT DEFAULT NULL;
DECLARE M_I_RS_3_size INT DEFAULT NULL;
DECLARE cursor_cnt_2 INT DEFAULT NULL;
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
DECLARE q4_i14 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_3 INT DEFAULT NULL;
DECLARE M_I_RS_4_size INT DEFAULT NULL;
DECLARE cursor_cnt_3 INT DEFAULT NULL;
DECLARE QUERY_ID_4_TXN INT DEFAULT NULL;

IF TRUE THEN
SET QUERY_ID_0_TXN = 0;
set autocommit=0;
END IF;
IF TRUE THEN
SET q2_i1 = M_L_String__REQUEST_PARAM_actor_root_id;
SET q2_i2 = 'Profile';
SET q2_i3 = 'Profile';
SET q2_i4 = 'Profile';
SET q2_i5 = 'Profile';
SET q2_i6 = 28;
SET QUERY_ID_1 = 1;
SELECT * FROM ( SELECT n1.id, n1.root_id, n1.acl_all, n1.acl_spec, n1.frag , n1.f_created_at, f0.ord AS _tk1, e1.seq AS _tk2, e1.id AS _tk3 FROM ( SELECT q2_i1 AS id, 1 AS ord ) f0 LEFT JOIN anchors s1 ON s1.id = f0.id JOIN anchors e1 ON e1.kind = 'EdgeAnchor' AND ((e1.src = f0.id AND (e1.dst_type IS NULL OR (e1.dst_type = q2_i2 OR e1.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i3 )))) OR (e1.undirected AND (e1.dst = f0.id AND (e1.src_type IS NULL OR (e1.src_type = q2_i4 OR e1.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i5 )))))) JOIN g_n_profile_d2a57d n1 ON n1.id = CASE  WHEN e1.src = f0.id THEN e1.dst ELSE e1.src END ORDER BY n1.f_created_at DESC, f0.ord, e1.seq, e1.id LIMIT q2_i6 ) _topk ORDER BY _tk1, _tk2, _tk3;
SET M_I_RS_2_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q3_i1 = M_L_String__REQUEST_PARAM_actor_id;
SET q3_i2 = 'Tweet';
SET q3_i3 = 'Tweet';
SET q3_i4 = 'Tweet';
SET q3_i5 = 'Tweet';
SET q3_i6 = 28;
SET QUERY_ID_2 = 2;
SELECT * FROM ( SELECT n1.id, n1.root_id, n1.acl_all, n1.acl_spec, n1.frag , n1.f_created_at, f0.ord AS _tk1, e1.seq AS _tk2, e1.id AS _tk3 FROM ( SELECT q3_i1 AS id, 1 AS ord ) f0 LEFT JOIN anchors s1 ON s1.id = f0.id JOIN anchors e1 ON e1.kind = 'EdgeAnchor' AND ((e1.src = f0.id AND (e1.dst_type IS NULL OR (e1.dst_type = q3_i2 OR e1.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q3_i3 )))) OR (e1.undirected AND (e1.dst = f0.id AND (e1.src_type IS NULL OR (e1.src_type = q3_i4 OR e1.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q3_i5 )))))) JOIN g_n_tweet_d2a57d n1 ON n1.id = CASE  WHEN e1.src = f0.id THEN e1.dst ELSE e1.src END ORDER BY n1.f_created_at DESC, f0.ord, e1.seq, e1.id LIMIT q3_i6 ) _topk ORDER BY _tk1, _tk2, _tk3;
SET M_I_RS_3_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q4_i1 = M_L_String__REQUEST_PARAM_actor_id;
SET q4_i2 = 'Profile';
SET q4_i3 = 'Profile';
SET q4_i4 = 'Profile';
SET q4_i5 = 'Profile';
SET q4_i6 = 'Follow';
SET q4_i7 = 'Follow';
SET q4_i8 = 'Profile';
SET q4_i9 = 'Profile';
SET q4_i10 = 'Tweet';
SET q4_i11 = 'Tweet';
SET q4_i12 = 'Tweet';
SET q4_i13 = 'Tweet';
SET q4_i14 = 28;
SET QUERY_ID_3 = 3;
SELECT * FROM ( SELECT n2.id, n2.root_id, n2.acl_all, n2.acl_spec, n2.frag , n2.f_created_at, f0.ord AS _tk1, e1.seq AS _tk2, e1.id AS _tk3, e2.seq AS _tk4 , e2.id AS _tk5 FROM ( SELECT q4_i1 AS id, 1 AS ord ) f0 LEFT JOIN anchors s1 ON s1.id = f0.id JOIN anchors e1 ON e1.kind = 'EdgeAnchor' AND ((e1.src = f0.id AND (e1.dst_type IS NULL OR (e1.dst_type = q4_i2 OR e1.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q4_i3 )))) OR (e1.undirected AND (e1.dst = f0.id AND (e1.src_type IS NULL OR (e1.src_type = q4_i4 OR e1.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q4_i5 )))))) AND (e1.arch_type = q4_i6 OR e1.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q4_i7 )) JOIN anchors n1 ON n1.id = CASE  WHEN e1.src = f0.id THEN e1.dst ELSE e1.src END AND n1.kind = 'NodeAnchor' AND (n1.arch_type = q4_i8 OR n1.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q4_i9 )) JOIN anchors e2 ON e2.kind = 'EdgeAnchor' AND ((e2.src = n1.id AND (e2.dst_type IS NULL OR (e2.dst_type = q4_i10 OR e2.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q4_i11 )))) OR (e2.undirected AND (e2.dst = n1.id AND (e2.src_type IS NULL OR (e2.src_type = q4_i12 OR e2.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q4_i13 )))))) JOIN g_n_tweet_d2a57d n2 ON n2.id = CASE  WHEN e2.src = n1.id THEN e2.dst ELSE e2.src END ORDER BY n2.f_created_at DESC, f0.ord, e1.seq, e1.id, e2.seq, e2.id LIMIT q4_i14 ) _topk ORDER BY _tk1, _tk2, _tk3, _tk4, _tk5;
SET M_I_RS_4_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET QUERY_ID_4_TXN = 4;
set autocommit=1;
END IF;
SELECT QUERY_ID_0_TXN,QUERY_ID_1,q2_i1,q2_i2,q2_i3,q2_i4,q2_i5,q2_i6,QUERY_ID_2,q3_i1,q3_i2,q3_i3,q3_i4,q3_i5,q3_i6,QUERY_ID_3,q4_i1,q4_i2,q4_i3,q4_i4,q4_i5,q4_i6,q4_i7,q4_i8,q4_i9,q4_i10,q4_i11,q4_i12,q4_i13,q4_i14,QUERY_ID_4_TXN;

END $$
DELIMITER ;