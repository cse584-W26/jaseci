SqlNo=1
SQLNode {
    sqlTemplate='set autocommit=0',
    parameters={},
    retVals={}
}
SqlNo=2
SQLNode {
    sqlTemplate='SELECT blog_id, blog_title, blog_sub_url, blog_cover_image, blog_category_id , blog_category_name, blog_tags, blog_status, blog_views, enable_comment , is_deleted, create_time, update_time, blog_content FROM tb_blog WHERE blog_id = ? AND is_deleted = 0',
    parameters={M_J_field_blogId_java_lang_Long_value:BIGINT},
    retVals={blog_id:BIGINT, blog_title:VARCHAR, blog_sub_url:VARCHAR, blog_cover_image:VARCHAR, blog_category_id:INT, blog_category_name:VARCHAR, blog_tags:VARCHAR, blog_status:TINYINT, blog_views:BIGINT, enable_comment:TINYINT, is_deleted:TINYINT, create_time:DATETIME, update_time:DATETIME, blog_content:MEDIUMTEXT}
}
SqlNo=3
SQLNode {
    sqlTemplate='SELECT category_id, category_name, category_icon, category_rank, is_deleted , create_time FROM tb_blog_category WHERE category_id = ? AND is_deleted = 0',
    parameters={M_I_field_blogCategoryId_java_lang_Integer_value:INT},
    retVals={category_id:INT, category_name:VARCHAR, category_icon:VARCHAR, category_rank:INT, is_deleted:TINYINT, create_time:DATETIME}
}
SqlNo=4
SQLNode {
    sqlTemplate='SELECT tag_id, tag_name, is_deleted, create_time FROM tb_blog_tag WHERE tag_name = ? AND is_deleted = 0',
    parameters={M_L_String__blogTags:VARCHAR},
    retVals={tag_id:INT, tag_name:VARCHAR, is_deleted:TINYINT, create_time:DATETIME}
}
SqlNo=5
SQLNode {
    sqlTemplate='UPDATE tb_blog_category SET category_name = ?, category_icon = ?, category_rank = ?, is_deleted = ?, create_time = ? WHERE category_id = ?',
    parameters={RS_q4_r1_col2:VARCHAR, RS_q4_r1_col3:VARCHAR, (RS_q4_r1_col4 + 1):INT, RS_q4_r1_col5:TINYINT, FROM_UNIXTIME(((((UNIX_TIMESTAMP(RS_q4_r1_col6)*1000 + (MICROSECOND(RS_q4_r1_col6)*1000 / 1000000)) / 1000) * 1000) / 1000)):DATETIME, RS_q4_r1_col1:INT},
    retVals={}
}
SqlNo=6
SQLNode {
    sqlTemplate='DELETE FROM tb_blog_tag_relation WHERE blog_id = ?',
    parameters={M_J_field_blogId_java_lang_Long_value:BIGINT},
    retVals={}
}
SqlNo=7
SQLNode {
    sqlTemplate='INSERT INTO tb_blog_tag_relation (blog_id, tag_id) VALUES (?, ?)',
    parameters={M_J_field_blogId_java_lang_Long_value:BIGINT, RS_q5_r1_col1:INT},
    retVals={}
}
SqlNo=8
SQLNode {
    sqlTemplate='UPDATE tb_blog SET blog_title = ?, blog_sub_url = ?, blog_cover_image = ?, blog_content = ?, blog_category_id = ?, blog_category_name = ?, blog_tags = ?, blog_status = ?, blog_views = ?, enable_comment = ?, is_deleted = ?, create_time = ?, update_time = ?, blog_content = ? WHERE blog_id = ?',
    parameters={M_L_String__blogTitle:VARCHAR, "":VARCHAR, M_L_String__blogCoverImage:VARCHAR, M_L_String__blogContent:MEDIUMTEXT, RS_q4_r1_col1:INT, RS_q4_r1_col2:VARCHAR, M_L_String__blogTags:VARCHAR, M_B_field_blogStatus_java_lang_Byte_value:TINYINT, RS_q3_r1_col9:BIGINT, M_B_field_enableComment_java_lang_Byte_value:TINYINT, RS_q3_r1_col11:TINYINT, FROM_UNIXTIME(((((UNIX_TIMESTAMP(RS_q3_r1_col12)*1000 + (MICROSECOND(RS_q3_r1_col12)*1000 / 1000000)) / 1000) * 1000) / 1000)):DATETIME, FROM_UNIXTIME(((((UNIX_TIMESTAMP(RS_q3_r1_col13)*1000 + (MICROSECOND(RS_q3_r1_col13)*1000 / 1000000)) / 1000) * 1000) / 1000)):DATETIME, M_L_String__blogContent:MEDIUMTEXT, RS_q3_r1_col1:BIGINT},
    retVals={}
}
