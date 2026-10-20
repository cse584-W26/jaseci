DROP PROCEDURE IF EXISTS `GetBlog_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE GetBlog_sp_1_ver0 (IN M_J_field_java_lang_Long_value INT)
BEGIN

DECLARE q1_i1 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_0 INT DEFAULT NULL;
DECLARE RS_q2_r1_col1 BIGINT DEFAULT NULL;
DECLARE RS_q2_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col3 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col4 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col5 INT DEFAULT NULL;
DECLARE RS_q2_r1_col6 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col7 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q2_r1_col8 TINYINT DEFAULT NULL;
DECLARE RS_q2_r1_col9 BIGINT DEFAULT NULL;
DECLARE RS_q2_r1_col10 TINYINT DEFAULT NULL;
DECLARE RS_q2_r1_col11 TINYINT DEFAULT NULL;
DECLARE RS_q2_r1_col12 DATETIME DEFAULT NULL;
DECLARE RS_q2_r1_col13 DATETIME DEFAULT NULL;
DECLARE RS_q2_r1_col14 MEDIUMTEXT DEFAULT NULL;
DECLARE M_I_RS_2_size INT DEFAULT NULL;
DECLARE cursor_cnt_0 INT DEFAULT NULL;
DECLARE cursor_0 int DEFAULT NULL;
DECLARE indicator_0 int DEFAULT NULL;
DECLARE q2_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i4 INT DEFAULT NULL;
DECLARE q2_i5 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i6 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i7 TINYINT DEFAULT NULL;
DECLARE q2_i8 BIGINT DEFAULT NULL;
DECLARE q2_i9 TINYINT DEFAULT NULL;
DECLARE q2_i10 TINYINT DEFAULT NULL;
DECLARE q2_i11 DATETIME DEFAULT NULL;
DECLARE q2_i12 DATETIME DEFAULT NULL;
DECLARE q2_i13 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_1 INT DEFAULT NULL;
DECLARE M_I_RS_23_rowCount INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;
DECLARE q3_i1 INT DEFAULT NULL;
DECLARE QUERY_ID_2 INT DEFAULT NULL;
DECLARE M_I_RS_5_size INT DEFAULT NULL;
DECLARE cursor_cnt_2 INT DEFAULT NULL;
DECLARE q4_i1 BIGINT DEFAULT NULL;
DECLARE q4_i2 TINYINT DEFAULT NULL;
DECLARE QUERY_ID_3 INT DEFAULT NULL;
DECLARE M_I_RS_6_size INT DEFAULT NULL;
DECLARE cursor_cnt_3 INT DEFAULT NULL;
DECLARE q5_i1 BIGINT DEFAULT NULL;
DECLARE q5_i2 TINYINT DEFAULT NULL;
DECLARE q5_i3 BIGINT DEFAULT NULL;
DECLARE q5_i4 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_4 INT DEFAULT NULL;
DECLARE M_I_RS_7_size INT DEFAULT NULL;
DECLARE cursor_cnt_4 INT DEFAULT NULL;
DECLARE QUERY_ID_5 INT DEFAULT NULL;
DECLARE M_I_RS_8_size INT DEFAULT NULL;
DECLARE cursor_cnt_5 INT DEFAULT NULL;

IF TRUE THEN
SET q1_i1 = M_J_field_java_lang_Long_value;
SET QUERY_ID_0 = 0;
SET indicator_0 = 0;
SET cursor_cnt_0 = 0;
BEGIN
DECLARE cursor_0 CURSOR FOR SELECT blog_id, blog_title, blog_sub_url, blog_cover_image, blog_category_id , blog_category_name, blog_tags, blog_status, blog_views, enable_comment , is_deleted, create_time, update_time, blog_content FROM tb_blog WHERE blog_id = q1_i1 AND is_deleted = 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_0 = 1;
OPEN cursor_0;
loop_0: LOOP
IF cursor_cnt_0=0 THEN
FETCH cursor_0 INTO RS_q2_r1_col1, RS_q2_r1_col2, RS_q2_r1_col3, RS_q2_r1_col4, RS_q2_r1_col5, RS_q2_r1_col6, RS_q2_r1_col7, RS_q2_r1_col8, RS_q2_r1_col9, RS_q2_r1_col10, RS_q2_r1_col11, RS_q2_r1_col12, RS_q2_r1_col13, RS_q2_r1_col14;
END IF;
IF cursor_cnt_0>=1 THEN
CLOSE cursor_0; LEAVE loop_0;END IF;
IF indicator_0=1 THEN CLOSE cursor_0; LEAVE loop_0; END IF;
SET cursor_cnt_0 = cursor_cnt_0 + 1;
END LOOP loop_0;
END;
SET cursor_cnt_0 = FOUND_ROWS();
SELECT cursor_cnt_0,RS_q2_r1_col1,RS_q2_r1_col2,RS_q2_r1_col3,RS_q2_r1_col4,RS_q2_r1_col5,RS_q2_r1_col6,RS_q2_r1_col7,RS_q2_r1_col8,RS_q2_r1_col9,RS_q2_r1_col10,RS_q2_r1_col11,RS_q2_r1_col12,RS_q2_r1_col13,RS_q2_r1_col14;
SET M_I_RS_2_size = cursor_cnt_0;
END IF;
IF TRUE THEN
IF cursor_cnt_0 > 0 THEN
SET q2_i1 = RS_q2_r1_col2;
SET q2_i2 = '';
SET q2_i3 = RS_q2_r1_col4;
SET q2_i4 = RS_q2_r1_col5;
SET q2_i5 = RS_q2_r1_col6;
SET q2_i6 = RS_q2_r1_col7;
SET q2_i7 = RS_q2_r1_col8;
SET q2_i8 = (RS_q2_r1_col9+1);
SET q2_i9 = RS_q2_r1_col10;
SET q2_i10 = RS_q2_r1_col11;
SET q2_i11 = FROM_UNIXTIME(((((UNIX_TIMESTAMP(RS_q2_r1_col12)*1000+(MICROSECOND(RS_q2_r1_col12)*1000/1000000))/1000)*1000)/1000));
SET q2_i12 = FROM_UNIXTIME(((((UNIX_TIMESTAMP(RS_q2_r1_col13)*1000+(MICROSECOND(RS_q2_r1_col13)*1000/1000000))/1000)*1000)/1000));
SET q2_i13 = RS_q2_r1_col1;
SET QUERY_ID_1 = 1;
UPDATE tb_blog SET blog_title = q2_i1, blog_sub_url = q2_i2, blog_cover_image = q2_i3, blog_category_id = q2_i4, blog_category_name = q2_i5, blog_tags = q2_i6, blog_status = q2_i7, blog_views = q2_i8, enable_comment = q2_i9, is_deleted = q2_i10, create_time = q2_i11, update_time = q2_i12 WHERE blog_id = q2_i13;
SET M_I_RS_23_rowCount = ROW_COUNT();
SELECT M_I_RS_23_rowCount;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_0 > 0 THEN
SET q3_i1 = RS_q2_r1_col5;
SET QUERY_ID_2 = 2;
SELECT category_id, category_name, category_icon, category_rank, is_deleted , create_time FROM tb_blog_category WHERE category_id = q3_i1 AND is_deleted = 0;
SET M_I_RS_5_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_0 > 0 THEN
SET q4_i1 = RS_q2_r1_col1;
SET q4_i2 = 1;
SET QUERY_ID_3 = 3;
SELECT count(*) FROM tb_blog_comment WHERE is_deleted = 0 AND blog_id = q4_i1 AND comment_status = q4_i2;
SET M_I_RS_6_size = FOUND_ROWS();
END IF;
END IF;
IF TRUE THEN
SET q5_i1 = M_J_field_java_lang_Long_value;
SET q5_i2 = 1;
SET q5_i3 = 0;
SET q5_i4 = 8;
SET QUERY_ID_4 = 4;
SELECT comment_id, blog_id, commentator, email, website_url , comment_body, comment_create_time, commentator_ip, reply_body, reply_create_time , comment_status, is_deleted FROM tb_blog_comment WHERE is_deleted = 0 AND blog_id = q5_i1 AND comment_status = q5_i2 ORDER BY comment_id DESC LIMIT q5_i3, q5_i4;
SET M_I_RS_7_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET QUERY_ID_5 = 5;
SELECT config_name, config_value, create_time, update_time FROM tb_config;
SET M_I_RS_8_size = FOUND_ROWS();
END IF;
SELECT QUERY_ID_0,q1_i1,QUERY_ID_1,q2_i1,q2_i2,q2_i3,q2_i4,q2_i5,q2_i6,q2_i7,q2_i8,q2_i9,q2_i10,q2_i11,q2_i12,q2_i13,QUERY_ID_2,q3_i1,QUERY_ID_3,q4_i1,q4_i2,QUERY_ID_4,q5_i1,q5_i2,q5_i3,q5_i4,QUERY_ID_5;

END $$
DELIMITER ;