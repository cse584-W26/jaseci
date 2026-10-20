SqlNo=1
SQLNode {
    sqlTemplate='SELECT blog_id, blog_title, blog_sub_url, blog_cover_image, blog_category_id , blog_category_name, blog_tags, blog_status, blog_views, enable_comment , is_deleted, create_time, update_time FROM tb_blog WHERE is_deleted = 0 AND blog_status = ? ORDER BY blog_id DESC LIMIT ?, ?',
    parameters={1:TINYINT, 0:BIGINT, 8:BIGINT},
    retVals={blog_id:BIGINT, blog_title:VARCHAR, blog_sub_url:VARCHAR, blog_cover_image:VARCHAR, blog_category_id:INT, blog_category_name:VARCHAR, blog_tags:VARCHAR, blog_status:TINYINT, blog_views:BIGINT, enable_comment:TINYINT, is_deleted:TINYINT, create_time:DATETIME, update_time:DATETIME}
}
SqlNo=2
SQLNode {
    sqlTemplate='SELECT category_id, category_name, category_icon, category_rank, is_deleted , create_time FROM tb_blog_category WHERE category_id IN (?, ?, ?, ?, ?, ?, ?, ?) AND is_deleted = 0',
    parameters={RS_q2_r1_col5:INT, RS_q2_r2_col5:INT, RS_q2_r3_col5:INT, RS_q2_r4_col5:INT, RS_q2_r5_col5:INT, RS_q2_r6_col5:INT, RS_q2_r7_col5:INT, RS_q2_r8_col5:INT},
    retVals={category_id:INT, category_name:VARCHAR, category_icon:VARCHAR, category_rank:INT, is_deleted:TINYINT, create_time:DATETIME}
}
SqlNo=3
SQLNode {
    sqlTemplate='SELECT count(*) FROM tb_blog WHERE is_deleted = 0 AND blog_status = ?',
    parameters={1:TINYINT},
    retVals={count_star:BIGINT}
}
SqlNo=4
SQLNode {
    sqlTemplate='SELECT blog_id, blog_title, blog_sub_url, blog_cover_image, blog_category_id , blog_category_name, blog_tags, blog_status, blog_views, enable_comment , is_deleted, create_time, update_time FROM tb_blog WHERE is_deleted = 0 AND blog_status = 1 ORDER BY blog_id DESC LIMIT ?',
    parameters={9:BIGINT},
    retVals={blog_id:BIGINT, blog_title:VARCHAR, blog_sub_url:VARCHAR, blog_cover_image:VARCHAR, blog_category_id:INT, blog_category_name:VARCHAR, blog_tags:VARCHAR, blog_status:TINYINT, blog_views:BIGINT, enable_comment:TINYINT, is_deleted:TINYINT, create_time:DATETIME, update_time:DATETIME}
}
SqlNo=5
SQLNode {
    sqlTemplate='SELECT blog_id, blog_title, blog_sub_url, blog_cover_image, blog_category_id , blog_category_name, blog_tags, blog_status, blog_views, enable_comment , is_deleted, create_time, update_time FROM tb_blog WHERE is_deleted = 0 AND blog_status = 1 ORDER BY blog_views DESC LIMIT ?',
    parameters={9:BIGINT},
    retVals={blog_id:BIGINT, blog_title:VARCHAR, blog_sub_url:VARCHAR, blog_cover_image:VARCHAR, blog_category_id:INT, blog_category_name:VARCHAR, blog_tags:VARCHAR, blog_status:TINYINT, blog_views:BIGINT, enable_comment:TINYINT, is_deleted:TINYINT, create_time:DATETIME, update_time:DATETIME}
}
SqlNo=6
SQLNode {
    sqlTemplate='SELECT t_r.*, t.tag_name FROM ( SELECT r.tag_id, r.tag_count FROM ( SELECT tag_id, COUNT(*) AS tag_count FROM ( SELECT tr.tag_id FROM tb_blog_tag_relation tr LEFT JOIN tb_blog b ON tr.blog_id = b.blog_id WHERE b.is_deleted = 0 ) trb GROUP BY tag_id ) r ORDER BY tag_count DESC LIMIT 20 ) t_r LEFT JOIN tb_blog_tag t ON t_r.tag_id = t.tag_id WHERE t.is_deleted = 0',
    parameters={},
    retVals={tr.tag_id:INT, count(*):INT, t.tag_name:VARCHAR}
}
SqlNo=7
SQLNode {
    sqlTemplate='SELECT config_name, config_value, create_time, update_time FROM tb_config',
    parameters={},
    retVals={config_name:VARCHAR, config_value:VARCHAR, create_time:DATETIME, update_time:DATETIME}
}
