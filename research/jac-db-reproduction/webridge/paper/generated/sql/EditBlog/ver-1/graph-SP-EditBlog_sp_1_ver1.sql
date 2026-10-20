DROP PROCEDURE IF EXISTS `EditBlog_sp_1_ver1`;
DELIMITER $$
CREATE PROCEDURE EditBlog_sp_1_ver1 (IN M_J_field_blogId_java_lang_Long_value INT, IN M_L_String__blogContent VARCHAR(512), IN M_L_String__blogCoverImage VARCHAR(512), IN M_I_field_blogCategoryId_java_lang_Integer_value INT, IN M_B_field_blogStatus_java_lang_Byte_value INT, IN M_L_String__blogTags VARCHAR(512), IN M_B_field_enableComment_java_lang_Byte_value INT, IN M_L_String__blogTitle VARCHAR(512))
BEGIN

DECLARE QUERY_ID_0_TXN INT DEFAULT NULL;
DECLARE q2_i1 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_1 INT DEFAULT NULL;
DECLARE RS_q3_r1_col1 BIGINT DEFAULT NULL;
DECLARE RS_q3_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r1_col3 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r1_col4 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r1_col5 INT DEFAULT NULL;
DECLARE RS_q3_r1_col6 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r1_col7 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q3_r1_col8 TINYINT DEFAULT NULL;
DECLARE RS_q3_r1_col9 BIGINT DEFAULT NULL;
DECLARE RS_q3_r1_col10 TINYINT DEFAULT NULL;
DECLARE RS_q3_r1_col11 TINYINT DEFAULT NULL;
DECLARE RS_q3_r1_col12 DATETIME DEFAULT NULL;
DECLARE RS_q3_r1_col13 DATETIME DEFAULT NULL;
DECLARE RS_q3_r1_col14 MEDIUMTEXT DEFAULT NULL;
DECLARE M_I_RS_3_size INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;
DECLARE cursor_1 int DEFAULT NULL;
DECLARE indicator_1 int DEFAULT NULL;
DECLARE q3_i1 INT DEFAULT NULL;
DECLARE QUERY_ID_2 INT DEFAULT NULL;
DECLARE RS_q4_r1_col1 INT DEFAULT NULL;
DECLARE RS_q4_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q4_r1_col3 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q4_r1_col4 INT DEFAULT NULL;
DECLARE RS_q4_r1_col5 TINYINT DEFAULT NULL;
DECLARE RS_q4_r1_col6 DATETIME DEFAULT NULL;
DECLARE M_I_RS_4_size INT DEFAULT NULL;
DECLARE cursor_cnt_2 INT DEFAULT NULL;
DECLARE cursor_2 int DEFAULT NULL;
DECLARE indicator_2 int DEFAULT NULL;
DECLARE q4_i1 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_3 INT DEFAULT NULL;
DECLARE RS_q5_r1_col1 INT DEFAULT NULL;
DECLARE RS_q5_r1_col2 VARCHAR(512) DEFAULT NULL;
DECLARE RS_q5_r1_col3 TINYINT DEFAULT NULL;
DECLARE RS_q5_r1_col4 DATETIME DEFAULT NULL;
DECLARE M_I_RS_5_size INT DEFAULT NULL;
DECLARE cursor_cnt_3 INT DEFAULT NULL;
DECLARE cursor_3 int DEFAULT NULL;
DECLARE indicator_3 int DEFAULT NULL;
DECLARE q5_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q5_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q5_i3 INT DEFAULT NULL;
DECLARE q5_i4 TINYINT DEFAULT NULL;
DECLARE q5_i5 DATETIME DEFAULT NULL;
DECLARE q5_i6 INT DEFAULT NULL;
DECLARE QUERY_ID_4 INT DEFAULT NULL;
DECLARE M_I_RS_48_rowCount INT DEFAULT NULL;
DECLARE cursor_cnt_4 INT DEFAULT NULL;
DECLARE q6_i1 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_5 INT DEFAULT NULL;
DECLARE M_I_RS_52_rowCount INT DEFAULT NULL;
DECLARE cursor_cnt_5 INT DEFAULT NULL;
DECLARE q7_i1 BIGINT DEFAULT NULL;
DECLARE q7_i2 INT DEFAULT NULL;
DECLARE QUERY_ID_6 INT DEFAULT NULL;
DECLARE M_I_RS_55_rowCount INT DEFAULT NULL;
DECLARE cursor_cnt_6 INT DEFAULT NULL;
DECLARE q8_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q8_i2 VARCHAR(512) DEFAULT NULL;
DECLARE q8_i3 VARCHAR(512) DEFAULT NULL;
DECLARE q8_i4 MEDIUMTEXT DEFAULT NULL;
DECLARE q8_i5 INT DEFAULT NULL;
DECLARE q8_i6 VARCHAR(512) DEFAULT NULL;
DECLARE q8_i7 VARCHAR(512) DEFAULT NULL;
DECLARE q8_i8 TINYINT DEFAULT NULL;
DECLARE q8_i9 BIGINT DEFAULT NULL;
DECLARE q8_i10 TINYINT DEFAULT NULL;
DECLARE q8_i11 TINYINT DEFAULT NULL;
DECLARE q8_i12 DATETIME DEFAULT NULL;
DECLARE q8_i13 DATETIME DEFAULT NULL;
DECLARE q8_i14 MEDIUMTEXT DEFAULT NULL;
DECLARE q8_i15 BIGINT DEFAULT NULL;
DECLARE QUERY_ID_7 INT DEFAULT NULL;
DECLARE M_I_RS_58_rowCount INT DEFAULT NULL;
DECLARE cursor_cnt_7 INT DEFAULT NULL;

IF TRUE THEN
SET QUERY_ID_0_TXN = 0;
set autocommit=0;
END IF;
IF TRUE THEN
SET q2_i1 = M_J_field_blogId_java_lang_Long_value;
SET QUERY_ID_1 = 1;
SET indicator_1 = 0;
SET cursor_cnt_1 = 0;
BEGIN
DECLARE cursor_1 CURSOR FOR SELECT blog_id, blog_title, blog_sub_url, blog_cover_image, blog_category_id , blog_category_name, blog_tags, blog_status, blog_views, enable_comment , is_deleted, create_time, update_time, blog_content FROM tb_blog WHERE blog_id = q2_i1 AND is_deleted = 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_1 = 1;
OPEN cursor_1;
loop_1: LOOP
IF cursor_cnt_1=0 THEN
FETCH cursor_1 INTO RS_q3_r1_col1, RS_q3_r1_col2, RS_q3_r1_col3, RS_q3_r1_col4, RS_q3_r1_col5, RS_q3_r1_col6, RS_q3_r1_col7, RS_q3_r1_col8, RS_q3_r1_col9, RS_q3_r1_col10, RS_q3_r1_col11, RS_q3_r1_col12, RS_q3_r1_col13, RS_q3_r1_col14;
END IF;
IF cursor_cnt_1>=1 THEN
CLOSE cursor_1; LEAVE loop_1;END IF;
IF indicator_1=1 THEN CLOSE cursor_1; LEAVE loop_1; END IF;
SET cursor_cnt_1 = cursor_cnt_1 + 1;
END LOOP loop_1;
END;
SET cursor_cnt_1 = FOUND_ROWS();
SELECT cursor_cnt_1,RS_q3_r1_col1,RS_q3_r1_col2,RS_q3_r1_col3,RS_q3_r1_col4,RS_q3_r1_col5,RS_q3_r1_col6,RS_q3_r1_col7,RS_q3_r1_col8,RS_q3_r1_col9,RS_q3_r1_col10,RS_q3_r1_col11,RS_q3_r1_col12,RS_q3_r1_col13,RS_q3_r1_col14;
SET M_I_RS_3_size = cursor_cnt_1;
END IF;
IF TRUE THEN
SET q3_i1 = M_I_field_blogCategoryId_java_lang_Integer_value;
SET QUERY_ID_2 = 2;
SET indicator_2 = 0;
SET cursor_cnt_2 = 0;
BEGIN
DECLARE cursor_2 CURSOR FOR SELECT category_id, category_name, category_icon, category_rank, is_deleted , create_time FROM tb_blog_category WHERE category_id = q3_i1 AND is_deleted = 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_2 = 1;
OPEN cursor_2;
loop_2: LOOP
IF cursor_cnt_2=0 THEN
FETCH cursor_2 INTO RS_q4_r1_col1, RS_q4_r1_col2, RS_q4_r1_col3, RS_q4_r1_col4, RS_q4_r1_col5, RS_q4_r1_col6;
END IF;
IF cursor_cnt_2>=1 THEN
CLOSE cursor_2; LEAVE loop_2;END IF;
IF indicator_2=1 THEN CLOSE cursor_2; LEAVE loop_2; END IF;
SET cursor_cnt_2 = cursor_cnt_2 + 1;
END LOOP loop_2;
END;
SET cursor_cnt_2 = FOUND_ROWS();
SELECT cursor_cnt_2,RS_q4_r1_col1,RS_q4_r1_col2,RS_q4_r1_col3,RS_q4_r1_col4,RS_q4_r1_col5,RS_q4_r1_col6;
SET M_I_RS_4_size = cursor_cnt_2;
END IF;
IF TRUE THEN
SET q4_i1 = M_L_String__blogTags;
SET QUERY_ID_3 = 3;
SET indicator_3 = 0;
SET cursor_cnt_3 = 0;
BEGIN
DECLARE cursor_3 CURSOR FOR SELECT tag_id, tag_name, is_deleted, create_time FROM tb_blog_tag WHERE tag_name = q4_i1 AND is_deleted = 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET indicator_3 = 1;
OPEN cursor_3;
loop_3: LOOP
IF cursor_cnt_3=0 THEN
FETCH cursor_3 INTO RS_q5_r1_col1, RS_q5_r1_col2, RS_q5_r1_col3, RS_q5_r1_col4;
END IF;
IF cursor_cnt_3>=1 THEN
CLOSE cursor_3; LEAVE loop_3;END IF;
IF indicator_3=1 THEN CLOSE cursor_3; LEAVE loop_3; END IF;
SET cursor_cnt_3 = cursor_cnt_3 + 1;
END LOOP loop_3;
END;
SET cursor_cnt_3 = FOUND_ROWS();
SELECT cursor_cnt_3,RS_q5_r1_col1,RS_q5_r1_col2,RS_q5_r1_col3,RS_q5_r1_col4;
SET M_I_RS_5_size = cursor_cnt_3;
END IF;
IF TRUE THEN
IF cursor_cnt_2 > 0 THEN
SET q5_i1 = RS_q4_r1_col2;
SET q5_i2 = RS_q4_r1_col3;
SET q5_i3 = (RS_q4_r1_col4+1);
SET q5_i4 = RS_q4_r1_col5;
SET q5_i5 = FROM_UNIXTIME(((((UNIX_TIMESTAMP(RS_q4_r1_col6)*1000+(MICROSECOND(RS_q4_r1_col6)*1000/1000000))/1000)*1000)/1000));
SET q5_i6 = RS_q4_r1_col1;
SET QUERY_ID_4 = 4;
SAVEPOINT trace0_p4;
UPDATE tb_blog_category SET category_name = q5_i1, category_icon = q5_i2, category_rank = q5_i3, is_deleted = q5_i4, create_time = q5_i5 WHERE category_id = q5_i6;
SET M_I_RS_48_rowCount = ROW_COUNT();
SELECT M_I_RS_48_rowCount;
END IF;
END IF;
IF TRUE THEN
SET q6_i1 = M_J_field_blogId_java_lang_Long_value;
SET QUERY_ID_5 = 5;
SAVEPOINT trace0_p3;
DELETE FROM tb_blog_tag_relation WHERE blog_id = q6_i1;
SET M_I_RS_52_rowCount = ROW_COUNT();
SELECT M_I_RS_52_rowCount;
END IF;
IF TRUE THEN
IF cursor_cnt_3 > 0 THEN
SET q7_i1 = M_J_field_blogId_java_lang_Long_value;
SET q7_i2 = RS_q5_r1_col1;
SET QUERY_ID_6 = 6;
SAVEPOINT trace0_p2;
INSERT INTO tb_blog_tag_relation (blog_id, tag_id) VALUES (q7_i1, q7_i2);
SET M_I_RS_55_rowCount = ROW_COUNT();
SELECT M_I_RS_55_rowCount;
END IF;
END IF;
IF TRUE THEN
IF cursor_cnt_1 > 0 AND cursor_cnt_2 > 0 THEN
SET q8_i1 = M_L_String__blogTitle;
SET q8_i2 = '';
SET q8_i3 = M_L_String__blogCoverImage;
SET q8_i4 = M_L_String__blogContent;
SET q8_i5 = RS_q4_r1_col1;
SET q8_i6 = RS_q4_r1_col2;
SET q8_i7 = M_L_String__blogTags;
SET q8_i8 = M_B_field_blogStatus_java_lang_Byte_value;
SET q8_i9 = RS_q3_r1_col9;
SET q8_i10 = M_B_field_enableComment_java_lang_Byte_value;
SET q8_i11 = RS_q3_r1_col11;
SET q8_i12 = FROM_UNIXTIME(((((UNIX_TIMESTAMP(RS_q3_r1_col12)*1000+(MICROSECOND(RS_q3_r1_col12)*1000/1000000))/1000)*1000)/1000));
SET q8_i13 = FROM_UNIXTIME(((((UNIX_TIMESTAMP(RS_q3_r1_col13)*1000+(MICROSECOND(RS_q3_r1_col13)*1000/1000000))/1000)*1000)/1000));
SET q8_i14 = M_L_String__blogContent;
SET q8_i15 = RS_q3_r1_col1;
SET QUERY_ID_7 = 7;
SAVEPOINT trace0_p1;
UPDATE tb_blog SET blog_title = q8_i1, blog_sub_url = q8_i2, blog_cover_image = q8_i3, blog_content = q8_i4, blog_category_id = q8_i5, blog_category_name = q8_i6, blog_tags = q8_i7, blog_status = q8_i8, blog_views = q8_i9, enable_comment = q8_i10, is_deleted = q8_i11, create_time = q8_i12, update_time = q8_i13, blog_content = q8_i14 WHERE blog_id = q8_i15;
SET M_I_RS_58_rowCount = ROW_COUNT();
SELECT M_I_RS_58_rowCount;
END IF;
END IF;
SELECT QUERY_ID_0_TXN,QUERY_ID_1,q2_i1,QUERY_ID_2,q3_i1,QUERY_ID_3,q4_i1,QUERY_ID_4,q5_i1,q5_i2,q5_i3,q5_i4,q5_i5,q5_i6,QUERY_ID_5,q6_i1,QUERY_ID_6,q7_i1,q7_i2,QUERY_ID_7,q8_i1,q8_i2,q8_i3,q8_i4,q8_i5,q8_i6,q8_i7,q8_i8,q8_i9,q8_i10,q8_i11,q8_i12,q8_i13,q8_i14,q8_i15;

END $$
DELIMITER ;