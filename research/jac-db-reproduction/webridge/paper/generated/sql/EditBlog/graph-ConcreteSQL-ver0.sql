set autocommit=0
SELECT blog_id, blog_title, blog_sub_url, blog_cover_image, blog_category_id , blog_category_name, blog_tags, blog_status, blog_views, enable_comment , is_deleted, create_time, update_time, blog_content FROM tb_blog WHERE blog_id = ? AND is_deleted = 0
SELECT category_id, category_name, category_icon, category_rank, is_deleted , create_time FROM tb_blog_category WHERE category_id = ? AND is_deleted = 0
SELECT tag_id, tag_name, is_deleted, create_time FROM tb_blog_tag WHERE tag_name = ? AND is_deleted = 0
UPDATE tb_blog_category SET category_name = ?, category_icon = ?, category_rank = ?, is_deleted = ?, create_time = ? WHERE category_id = ?
DELETE FROM tb_blog_tag_relation WHERE blog_id = ?
INSERT INTO tb_blog_tag_relation (blog_id, tag_id) VALUES (?, ?)
UPDATE tb_blog SET blog_title = ?, blog_sub_url = ?, blog_cover_image = ?, blog_content = ?, blog_category_id = ?, blog_category_name = ?, blog_tags = ?, blog_status = ?, blog_views = ?, enable_comment = ?, is_deleted = ?, create_time = ?, update_time = ?, blog_content = ? WHERE blog_id = ?
set autocommit=1
