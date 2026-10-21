DROP PROCEDURE IF EXISTS `Tpcc_5623db86f6cd_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE Tpcc_5623db86f6cd_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_c_last VARCHAR(512), IN M_L_String__REQUEST_PARAM_timestamp VARCHAR(512), IN M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value BIGINT, IN M_D_field_REQUEST_PARAM_amount_java_lang_Double_value DOUBLE, IN M_J_field_REQUEST_PARAM_c_d_id_java_lang_Long_value BIGINT, IN M_J_field_REQUEST_PARAM_d_id_java_lang_Long_value BIGINT)
BEGIN

DECLARE q1_i1 INTEGER DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE RS_q1_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_1_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;
DECLARE cursor_0 int DEFAULT NULL;
DECLARE indicator_0 int DEFAULT NULL;
DECLARE q2_i1 INTEGER DEFAULT NULL;
DECLARE q2_i2 INTEGER DEFAULT NULL;
DECLARE QUERY_ID_1 INT DEFAULT NULL;
DECLARE RS_q2_r1_col1 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_2_size INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;
DECLARE cursor_1 int DEFAULT NULL;
DECLARE indicator_1 int DEFAULT NULL;
DECLARE q3_i1 INTEGER DEFAULT NULL;
DECLARE q3_i2 INTEGER DEFAULT NULL;
DECLARE q3_i3 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_2 INT DEFAULT NULL;
DECLARE RS_q3_r1_col1 INTEGER DEFAULT NULL;
DECLARE RS_q3_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r1_col3 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r2_col1 INTEGER DEFAULT NULL;
DECLARE RS_q3_r2_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r2_col3 VARCHAR(512) DEFAULT NULL;
DECLARE M_I_RS_3_size INT DEFAULT NULL;
DECLARE cursor_cnt_2 INT DEFAULT NULL;
DECLARE cursor_2 int DEFAULT NULL;
DECLARE indicator_2 int DEFAULT NULL;
DECLARE q4_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q4_i2 INTEGER DEFAULT NULL;
DECLARE QUERY_ID_3 INT DEFAULT NULL;
DECLARE M_I_RS_29_rowCount INT DEFAULT NULL;
DECLARE cursor_cnt_3 INT DEFAULT NULL;
DECLARE q5_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q5_i2 INTEGER DEFAULT NULL;
DECLARE q5_i3 INTEGER DEFAULT NULL;
DECLARE QUERY_ID_4 INT DEFAULT NULL;
DECLARE M_I_RS_33_rowCount INT DEFAULT NULL;
DECLARE cursor_cnt_4 INT DEFAULT NULL;
DECLARE q6_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q6_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q6_i3 INTEGER DEFAULT NULL;
DECLARE q6_i4 INTEGER DEFAULT NULL;
DECLARE q6_i5 INTEGER DEFAULT NULL;
DECLARE QUERY_ID_5 INT DEFAULT NULL;
DECLARE M_I_RS_39_rowCount INT DEFAULT NULL;
DECLARE cursor_cnt_5 INT DEFAULT NULL;
DECLARE q7_i1 INTEGER DEFAULT NULL;
DECLARE q7_i2 INTEGER DEFAULT NULL;
DECLARE q7_i3 INTEGER DEFAULT NULL;
DECLARE q7_i4 INTEGER DEFAULT NULL;
DECLARE q7_i5 INTEGER DEFAULT NULL;
DECLARE q7_i6 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i7 VARCHAR(512) DEFAULT NULL;
DECLARE q7_i8 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_6 INT DEFAULT NULL;
DECLARE M_I_RS_48_rowCount INT DEFAULT NULL;
DECLARE cursor_cnt_6 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value;
SET QUERY_ID_0 = 0;
SET indicator_0 = 0;
SET cursor_cnt_0 = 0;
BEGIN
DECLARE cursor_0 CURSOR FOR SELECT w_name FROM warehouse WHERE w_id = q1_i1 FOR UPDATE;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_0 = 1;
OPEN cursor_0;
loop_0: LOOP
IF cursor_cnt_0=0 THEN
FETCH cursor_0 INTO RS_q1_r1_col1;
END IF;
IF cursor_cnt_0>=1 THEN
CLOSE cursor_0; LEAVE loop_0;END IF;
IF indicator_0=1 THEN CLOSE cursor_0; LEAVE loop_0; END IF;
SET cursor_cnt_0 = cursor_cnt_0 + 1;
END LOOP loop_0;
END;
SET cursor_cnt_0 = FOUND_ROWS();
SELECT cursor_cnt_0,RS_q1_r1_col1;
SET M_I_RS_1_size = cursor_cnt_0;
END IF;
IF TRUE THEN
SET q2_i1 = M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value;
SET q2_i2 = M_J_field_REQUEST_PARAM_d_id_java_lang_Long_value;
SET QUERY_ID_1 = 1;
SET indicator_1 = 0;
SET cursor_cnt_1 = 0;
BEGIN
DECLARE cursor_1 CURSOR FOR SELECT d_name FROM district WHERE d_w_id = q2_i1 AND d_id = q2_i2 FOR UPDATE;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_1 = 1;
OPEN cursor_1;
loop_1: LOOP
IF cursor_cnt_1=0 THEN
FETCH cursor_1 INTO RS_q2_r1_col1;
END IF;
IF cursor_cnt_1>=1 THEN
CLOSE cursor_1; LEAVE loop_1;END IF;
IF indicator_1=1 THEN CLOSE cursor_1; LEAVE loop_1; END IF;
SET cursor_cnt_1 = cursor_cnt_1 + 1;
END LOOP loop_1;
END;
SET cursor_cnt_1 = FOUND_ROWS();
SELECT cursor_cnt_1,RS_q2_r1_col1;
SET M_I_RS_2_size = cursor_cnt_1;
END IF;
IF TRUE THEN
SET q3_i1 = M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value;
SET q3_i2 = M_J_field_REQUEST_PARAM_c_d_id_java_lang_Long_value;
SET q3_i3 = M_L_String__REQUEST_PARAM_c_last;
SET QUERY_ID_2 = 2;
SET indicator_2 = 0;
SET cursor_cnt_2 = 0;
BEGIN
DECLARE cursor_2 CURSOR FOR SELECT c_id, c_credit, c_data FROM customer WHERE c_w_id = q3_i1 AND c_d_id = q3_i2 AND c_last = q3_i3 ORDER BY c_first;
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
IF TRUE THEN
SET q4_i1 = M_D_field_REQUEST_PARAM_amount_java_lang_Double_value;
SET q4_i2 = M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value;
SET QUERY_ID_3 = 3;
UPDATE warehouse SET w_ytd = w_ytd + q4_i1 WHERE w_id = q4_i2;
SET M_I_RS_29_rowCount = ROW_COUNT();
SELECT M_I_RS_29_rowCount;
END IF;
IF TRUE THEN
SET q5_i1 = M_D_field_REQUEST_PARAM_amount_java_lang_Double_value;
SET q5_i2 = M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value;
SET q5_i3 = M_J_field_REQUEST_PARAM_d_id_java_lang_Long_value;
SET QUERY_ID_4 = 4;
UPDATE district SET d_ytd = d_ytd + q5_i1 WHERE d_w_id = q5_i2 AND d_id = q5_i3;
SET M_I_RS_33_rowCount = ROW_COUNT();
SELECT M_I_RS_33_rowCount;
END IF;
IF TRUE THEN
IF cursor_cnt_2 > 1 THEN
SET q6_i1 = M_D_field_REQUEST_PARAM_amount_java_lang_Double_value;
SET q6_i2 = M_D_field_REQUEST_PARAM_amount_java_lang_Double_value;
SET q6_i3 = M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value;
SET q6_i4 = M_J_field_REQUEST_PARAM_c_d_id_java_lang_Long_value;
SET q6_i5 = (0-(((((0-((ASCII(CONVERT(SUBSTRING(RS_q3_r2_col1,0+1,1),CHAR))+16)&31))*10)-((ASCII(CONVERT(SUBSTRING(RS_q3_r2_col1,1+1,1),CHAR))+16)&31))*10)-((ASCII(CONVERT(SUBSTRING(RS_q3_r2_col1,2+1,1),CHAR))+16)&31)));
SET QUERY_ID_5 = 5;
UPDATE customer SET c_balance = c_balance - q6_i1, c_ytd_payment = c_ytd_payment + q6_i2, c_payment_cnt = c_payment_cnt + 1 WHERE c_w_id = q6_i3 AND c_d_id = q6_i4 AND c_id = q6_i5;
SET M_I_RS_39_rowCount = ROW_COUNT();
SELECT M_I_RS_39_rowCount;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_0 > 0 AND cursor_cnt_1 > 0 AND cursor_cnt_2 > 1 THEN
SET q7_i1 = (0-(((((0-((ASCII(CONVERT(SUBSTRING(RS_q3_r2_col1,0+1,1),CHAR))+16)&31))*10)-((ASCII(CONVERT(SUBSTRING(RS_q3_r2_col1,1+1,1),CHAR))+16)&31))*10)-((ASCII(CONVERT(SUBSTRING(RS_q3_r2_col1,2+1,1),CHAR))+16)&31)));
SET q7_i2 = M_J_field_REQUEST_PARAM_c_d_id_java_lang_Long_value;
SET q7_i3 = M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value;
SET q7_i4 = M_J_field_REQUEST_PARAM_d_id_java_lang_Long_value;
SET q7_i5 = M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value;
SET q7_i6 = M_L_String__REQUEST_PARAM_timestamp;
SET q7_i7 = M_D_field_REQUEST_PARAM_amount_java_lang_Double_value;
SET q7_i8 = CONCAT(CONCAT(CONCAT('',RS_q1_r1_col1),'    '),RS_q2_r1_col1);
SET QUERY_ID_6 = 6;
INSERT INTO history (h_c_id, h_c_d_id, h_c_w_id, h_d_id, h_w_id , h_date, h_amount, h_data) VALUES (q7_i1, q7_i2, q7_i3, q7_i4, q7_i5 , q7_i6, q7_i7, q7_i8);
SET M_I_RS_48_rowCount = ROW_COUNT();
SELECT M_I_RS_48_rowCount;
END IF;
END IF;
SELECT QUERY_ID_0,q1_i1,QUERY_ID_1,q2_i1,q2_i2,QUERY_ID_2,q3_i1,q3_i2,q3_i3,QUERY_ID_3,q4_i1,q4_i2,QUERY_ID_4,q5_i1,q5_i2,q5_i3,QUERY_ID_5,q6_i1,q6_i2,q6_i3,q6_i4,q6_i5,QUERY_ID_6,q7_i1,q7_i2,q7_i3,q7_i4,q7_i5,q7_i6,q7_i7,q7_i8;

END $$
DELIMITER ;