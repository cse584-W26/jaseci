SqlNo=1
SQLNode {
    sqlTemplate='SELECT blog_id, blog_title, blog_sub_url, blog_cover_image, blog_category_id , blog_category_name, blog_tags, blog_status, blog_views, enable_comment , is_deleted, create_time, update_time, blog_content FROM tb_blog WHERE blog_id = ? AND is_deleted = 0',
    parameters={M_J_field_java_lang_Long_value:BIGINT},
    retVals={blog_id:BIGINT, blog_title:VARCHAR, blog_sub_url:VARCHAR, blog_cover_image:VARCHAR, blog_category_id:INT, blog_category_name:VARCHAR, blog_tags:VARCHAR, blog_status:TINYINT, blog_views:BIGINT, enable_comment:TINYINT, is_deleted:TINYINT, create_time:DATETIME, update_time:DATETIME, blog_content:MEDIUMTEXT}
}
SqlNo=2
SQLNode {
    sqlTemplate='UPDATE tb_blog SET blog_title = ?, blog_sub_url = ?, blog_cover_image = ?, blog_category_id = ?, blog_category_name = ?, blog_tags = ?, blog_status = ?, blog_views = ?, enable_comment = ?, is_deleted = ?, create_time = ?, update_time = ? WHERE blog_id = ?',
    parameters={RS_q2_r1_col2:VARCHAR, "":VARCHAR, RS_q2_r1_col4:VARCHAR, RS_q2_r1_col5:INT, RS_q2_r1_col6:VARCHAR, RS_q2_r1_col7:VARCHAR, RS_q2_r1_col8:TINYINT, (RS_q2_r1_col9 + 1):BIGINT, RS_q2_r1_col10:TINYINT, RS_q2_r1_col11:TINYINT, FROM_UNIXTIME(((((UNIX_TIMESTAMP(RS_q2_r1_col12)*1000 + (MICROSECOND(RS_q2_r1_col12)*1000 / 1000000)) / 1000) * 1000) / 1000)):DATETIME, FROM_UNIXTIME(((((UNIX_TIMESTAMP(RS_q2_r1_col13)*1000 + (MICROSECOND(RS_q2_r1_col13)*1000 / 1000000)) / 1000) * 1000) / 1000)):DATETIME, RS_q2_r1_col1:BIGINT},
    retVals={}
}
SqlNo=3
SQLNode {
    sqlTemplate='SELECT category_id, category_name, category_icon, category_rank, is_deleted , create_time FROM tb_blog_category WHERE category_id = ? AND is_deleted = 0',
    parameters={RS_q2_r1_col5:INT},
    retVals={category_id:INT, category_name:VARCHAR, category_icon:VARCHAR, category_rank:INT, is_deleted:TINYINT, create_time:DATETIME}
}
SqlNo=4
SQLNode {
    sqlTemplate='SELECT count(*) FROM tb_blog_comment WHERE is_deleted = 0 AND blog_id = ? AND comment_status = ?',
    parameters={RS_q2_r1_col1:BIGINT, 1:TINYINT},
    retVals={count_star:BIGINT}
}
SqlNo=5
SQLNode {
    sqlTemplate='SELECT comment_id, blog_id, commentator, email, website_url , comment_body, comment_create_time, commentator_ip, reply_body, reply_create_time , comment_status, is_deleted FROM tb_blog_comment WHERE is_deleted = 0 AND blog_id = ? AND comment_status = ? ORDER BY comment_id DESC LIMIT ?, ?',
    parameters={M_J_field_java_lang_Long_value:BIGINT, 1:TINYINT, 0:BIGINT, 8:BIGINT},
    retVals={comment_id:BIGINT, blog_id:BIGINT, commentator:VARCHAR, email:VARCHAR, website_url:VARCHAR, comment_body:VARCHAR, comment_create_time:DATETIME, commentator_ip:VARCHAR, reply_body:VARCHAR, reply_create_time:DATETIME, comment_status:TINYINT, is_deleted:TINYINT}
}
SqlNo=6
SQLNode {
    sqlTemplate='SELECT config_name, config_value, create_time, update_time FROM tb_config',
    parameters={},
    retVals={config_name:VARCHAR, config_value:VARCHAR, create_time:DATETIME, update_time:DATETIME}
}

======================================================
