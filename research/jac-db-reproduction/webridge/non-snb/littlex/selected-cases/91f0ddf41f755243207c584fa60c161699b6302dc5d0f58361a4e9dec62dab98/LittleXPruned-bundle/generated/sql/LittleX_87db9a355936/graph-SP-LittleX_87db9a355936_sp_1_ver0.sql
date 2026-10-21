DROP PROCEDURE IF EXISTS `LittleX_87db9a355936_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE LittleX_87db9a355936_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_actor_id VARCHAR(512), IN M_L_String__REQUEST_PARAM_new_id VARCHAR(512), IN M_L_String__REQUEST_PARAM_new_seq VARCHAR(512), IN M_L_String__REQUEST_PARAM_actor_root_id VARCHAR(512), IN M_L_String__REQUEST_PARAM_new_edge_id VARCHAR(512), IN M_L_String__REQUEST_PARAM_new_edge_seq VARCHAR(512))
BEGIN

DECLARE QUERY_ID_0_TXN INT DEFAULT NULL;
DECLARE q2_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i6 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i7 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_1 INT DEFAULT NULL;
DECLARE M_I_RS_2_size INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;
DECLARE q3_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i4 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i6 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i7 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i8 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i9 BOOLEAN DEFAULT NULL;
DECLARE q3_i10 LONGTEXT DEFAULT NULL;
DECLARE q3_i11 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i12 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i13 BIGINT DEFAULT NULL;
DECLARE q3_i14 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i15 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i16 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i17 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i18 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i19 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i20 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i21 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i22 BOOLEAN DEFAULT NULL;
DECLARE q3_i23 LONGTEXT DEFAULT NULL;
DECLARE q3_i24 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i25 VARCHAR(512) DEFAULT NULL;
DECLARE q3_i26 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_2 INT DEFAULT NULL;
DECLARE M_I_RS_35_rowCount INT DEFAULT NULL;
DECLARE cursor_cnt_2 INT DEFAULT NULL;
DECLARE QUERY_ID_3_TXN INT DEFAULT NULL;

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
SET q2_i6 = 'Profile';
SET q2_i7 = 'Profile';
SET QUERY_ID_1 = 1;
SELECT n1.id, e1.id, n1.props FROM ( SELECT q2_i1 AS id, 1 AS ord ) f0 LEFT JOIN anchors s1 ON s1.id = f0.id JOIN anchors e1 ON e1.kind = 'EdgeAnchor' AND ((e1.src = f0.id AND (e1.dst_type IS NULL OR (e1.dst_type = q2_i2 OR e1.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i3 )))) OR (e1.undirected AND (e1.dst = f0.id AND (e1.src_type IS NULL OR (e1.src_type = q2_i4 OR e1.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i5 )))))) JOIN anchors n1 ON n1.id = CASE  WHEN e1.src = f0.id THEN e1.dst ELSE e1.src END AND n1.kind = 'NodeAnchor' AND (n1.arch_type = q2_i6 OR n1.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = q2_i7 )) ORDER BY f0.ord, e1.seq, e1.id;
SET M_I_RS_2_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET q3_i1 = M_L_String__REQUEST_PARAM_new_edge_id;
SET q3_i2 = 'EdgeAnchor';
SET q3_i3 = 'Post';
SET q3_i4 = 'app';
SET q3_i5 = '0257ab8108739b8f';
SET q3_i6 = M_L_String__REQUEST_PARAM_actor_root_id;
SET q3_i7 = M_L_String__REQUEST_PARAM_actor_id;
SET q3_i8 = M_L_String__REQUEST_PARAM_new_id;
SET q3_i9 = '0';
SET q3_i10 = '{\"id\":\"173b653c-85d5-5292-9bef-8327e7d94f92\",\"root\":\"a6aa67a9-a09f-4b90-87d2-b404400d176d\",\"access\":{\"all\":-1,\"roots\":{\"anchors\":{}}},\"source\":\"be88871d-b7c9-4cef-b134-df8946207f84\",\"target\":\"31608e37-3266-5b36-bb93-4b408d02c300\",\"__type__\":\"EdgeAnchor\",\"archetype\":{\"__type__\":\"Post\",\"__module__\":\"app\"},\"__module__\":\"jaclang.jac0core.archetype\",\"persistent\":true,\"is_undirected\":false}';
SET q3_i11 = 'Profile';
SET q3_i12 = 'Tweet';
SET q3_i13 = M_L_String__REQUEST_PARAM_new_edge_seq;
SET q3_i14 = M_L_String__REQUEST_PARAM_new_id;
SET q3_i15 = 'NodeAnchor';
SET q3_i16 = 'Tweet';
SET q3_i17 = 'app';
SET q3_i18 = '552e15e3e79578ff';
SET q3_i19 = M_L_String__REQUEST_PARAM_actor_root_id;
SET q3_i20 = NULL;
SET q3_i21 = NULL;
SET q3_i22 = '0';
SET q3_i23 = '{\"id\":\"31608e37-3266-5b36-bb93-4b408d02c300\",\"root\":\"a6aa67a9-a09f-4b90-87d2-b404400d176d\",\"access\":{\"all\":2,\"roots\":{\"anchors\":{}}},\"version\":0,\"__type__\":\"NodeAnchor\",\"archetype\":{\"likes\":[],\"content\":\"write bench tweet -1 #bench\",\"seed_id\":\"w2_-1\",\"__type__\":\"Tweet\",\"comments\":[],\"__module__\":\"app\",\"created_at\":\"2026-10-20T23:00:00.000000Z\",\"author_username\":\"t20_sim_user_0\"},\"__module__\":\"jaclang.jac0core.archetype\",\"persistent\":true}';
SET q3_i24 = NULL;
SET q3_i25 = NULL;
SET q3_i26 = M_L_String__REQUEST_PARAM_new_seq;
SET QUERY_ID_2 = 2;
SAVEPOINT trace0_p1;
INSERT INTO anchors (id, kind, arch_type, arch_module, fingerprint , root_id, src, dst, undirected, props , src_type, dst_type, seq) VALUES (q3_i1, q3_i2, q3_i3, q3_i4, q3_i5 , q3_i6, q3_i7, q3_i8, q3_i9, q3_i10 , q3_i11, q3_i12, q3_i13), (q3_i14, q3_i15, q3_i16, q3_i17, q3_i18 , q3_i19, q3_i20, q3_i21, q3_i22, q3_i23 , q3_i24, q3_i25, q3_i26) ON DUPLICATE KEY UPDATE kind = VALUES(kind), arch_type = VALUES(arch_type), arch_module = VALUES(arch_module), fingerprint = VALUES(fingerprint), root_id = VALUES(root_id) , src = VALUES(src), dst = VALUES(dst), undirected = VALUES(undirected), props = VALUES(props), src_type = COALESCE(VALUES(src_type), src_type) , dst_type = COALESCE(VALUES(dst_type), dst_type);
SET M_I_RS_35_rowCount = ROW_COUNT();
SELECT M_I_RS_35_rowCount;
END IF;
IF TRUE THEN
SET QUERY_ID_3_TXN = 3;
set autocommit=1;
END IF;
SELECT QUERY_ID_0_TXN,QUERY_ID_1,q2_i1,q2_i2,q2_i3,q2_i4,q2_i5,q2_i6,q2_i7,QUERY_ID_2,q3_i1,q3_i2,q3_i3,q3_i4,q3_i5,q3_i6,q3_i7,q3_i8,q3_i9,q3_i10,q3_i11,q3_i12,q3_i13,q3_i14,q3_i15,q3_i16,q3_i17,q3_i18,q3_i19,q3_i20,q3_i21,q3_i22,q3_i23,q3_i24,q3_i25,q3_i26,QUERY_ID_3_TXN;

END $$
DELIMITER ;