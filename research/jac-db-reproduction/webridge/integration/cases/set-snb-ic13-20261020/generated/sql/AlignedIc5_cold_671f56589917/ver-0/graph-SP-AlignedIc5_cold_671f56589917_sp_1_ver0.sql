DROP PROCEDURE IF EXISTS `AlignedIc5_cold_671f56589917_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE AlignedIc5_cold_671f56589917_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_person1_jid VARCHAR(512), IN M_L_String__REQUEST_PARAM_person2_jid VARCHAR(512))
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
DECLARE q1_i14 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE M_I_RS_1_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = M_L_String__REQUEST_PARAM_person1_jid;
SET q1_i2 = M_L_String__REQUEST_PARAM_person2_jid;
SET q1_i3 = M_L_String__REQUEST_PARAM_person1_jid;
SET q1_i4 = M_L_String__REQUEST_PARAM_person2_jid;
SET q1_i5 = M_L_String__REQUEST_PARAM_person1_jid;
SET q1_i6 = M_L_String__REQUEST_PARAM_person2_jid;
SET q1_i7 = M_L_String__REQUEST_PARAM_person1_jid;
SET q1_i8 = M_L_String__REQUEST_PARAM_person2_jid;
SET q1_i9 = M_L_String__REQUEST_PARAM_person1_jid;
SET q1_i10 = M_L_String__REQUEST_PARAM_person2_jid;
SET q1_i11 = M_L_String__REQUEST_PARAM_person1_jid;
SET q1_i12 = M_L_String__REQUEST_PARAM_person2_jid;
SET q1_i13 = M_L_String__REQUEST_PARAM_person1_jid;
SET q1_i14 = M_L_String__REQUEST_PARAM_person2_jid;
SET QUERY_ID_0 = 0;
SELECT CASE  WHEN q1_i1 = q1_i2 THEN 0 WHEN EXISTS ( SELECT 1 FROM adj_knows k1 WHERE k1.src = q1_i3 AND k1.dst = q1_i4 ) THEN 1 WHEN EXISTS ( SELECT 1 FROM adj_knows k1 JOIN adj_knows k2 ON k2.src = k1.dst WHERE k1.src = q1_i5 AND k2.dst = q1_i6 ) THEN 2 WHEN EXISTS ( SELECT 1 FROM adj_knows k1 JOIN adj_knows k2 ON k2.src = k1.dst JOIN adj_knows k3 ON k3.src = k2.dst WHERE k1.src = q1_i7 AND k3.dst = q1_i8 ) THEN 3 WHEN EXISTS ( SELECT 1 FROM adj_knows k1 JOIN adj_knows k2 ON k2.src = k1.dst JOIN adj_knows k3 ON k3.src = k2.dst JOIN adj_knows k4 ON k4.src = k3.dst WHERE k1.src = q1_i9 AND k4.dst = q1_i10 ) THEN 4 WHEN EXISTS ( SELECT 1 FROM adj_knows k1 JOIN adj_knows k2 ON k2.src = k1.dst JOIN adj_knows k3 ON k3.src = k2.dst JOIN adj_knows k4 ON k4.src = k3.dst JOIN adj_knows k5 ON k5.src = k4.dst WHERE k1.src = q1_i11 AND k5.dst = q1_i12 ) THEN 5 WHEN EXISTS ( SELECT 1 FROM adj_knows k1 JOIN adj_knows k2 ON k2.src = k1.dst JOIN adj_knows k3 ON k3.src = k2.dst JOIN adj_knows k4 ON k4.src = k3.dst JOIN adj_knows k5 ON k5.src = k4.dst JOIN adj_knows k6 ON k6.src = k5.dst WHERE k1.src = q1_i13 AND k6.dst = q1_i14 ) THEN 6 ELSE -1 END AS length;
SET M_I_RS_1_size = FOUND_ROWS();
END IF;
SELECT QUERY_ID_0,q1_i1,q1_i2,q1_i3,q1_i4,q1_i5,q1_i6,q1_i7,q1_i8,q1_i9,q1_i10,q1_i11,q1_i12,q1_i13,q1_i14;

END $$
DELIMITER ;