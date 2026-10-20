SELECT blog_id, blog_title, blog_sub_url, blog_cover_image, blog_category_id , blog_category_name, blog_tags, blog_status, blog_views, enable_comment , is_deleted, create_time, update_time, blog_content FROM tb_blog WHERE blog_id = ? AND is_deleted = 0
UPDATE tb_blog SET blog_title = ?, blog_sub_url = ?, blog_cover_image = ?, blog_category_id = ?, blog_category_name = ?, blog_tags = ?, blog_status = ?, blog_views = ?, enable_comment = ?, is_deleted = ?, create_time = ?, update_time = ? WHERE blog_id = ?
SELECT category_id, category_name, category_icon, category_rank, is_deleted , create_time FROM tb_blog_category WHERE category_id = ? AND is_deleted = 0
SELECT count(*) FROM tb_blog_comment WHERE is_deleted = 0 AND blog_id = ? AND comment_status = ?
SELECT comment_id, blog_id, commentator, email, website_url , comment_body, comment_create_time, commentator_ip, reply_body, reply_create_time , comment_status, is_deleted FROM tb_blog_comment WHERE is_deleted = 0 AND blog_id = ? AND comment_status = ? ORDER BY comment_id DESC LIMIT ?, ?
SELECT config_name, config_value, create_time, update_time FROM tb_config
