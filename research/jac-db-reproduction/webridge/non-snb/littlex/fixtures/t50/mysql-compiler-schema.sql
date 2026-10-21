CREATE DATABASE IF NOT EXISTS jac_lx_t50_20261020 CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
USE jac_lx_t50_20261020;
CREATE TABLE anchors (
 id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin PRIMARY KEY,
 kind VARCHAR(32) NOT NULL,arch_type VARCHAR(100) NOT NULL,arch_module VARCHAR(200) NOT NULL,fingerprint VARCHAR(200) NOT NULL,
 root_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,src CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,dst CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
 undirected BOOLEAN NOT NULL,props LONGTEXT CHARACTER SET utf8mb4 NOT NULL,row_version VARCHAR(32),seq BIGINT NOT NULL,
 src_type VARCHAR(100),dst_type VARCHAR(100),KEY source_type(src,arch_type),KEY target_type(dst,arch_type),KEY kind_type(kind,arch_type),KEY owner_root(root_id)
) ENGINE=InnoDB;
CREATE TABLE graph_types(type_name VARCHAR(100) NOT NULL,ancestor VARCHAR(100) NOT NULL,PRIMARY KEY(type_name,ancestor));
CREATE TABLE identity_users(user_id VARCHAR(100) PRIMARY KEY,doc LONGTEXT NOT NULL);
CREATE TABLE kv_state(`key` VARCHAR(200) PRIMARY KEY,`value` LONGTEXT,expires_at DATETIME NULL);

USE jac_lx_t50_20261020;


CREATE TABLE `g_n_profile_d2a57d`(`id` CHAR(36) COLLATE utf8mb4_bin PRIMARY KEY,`root_id` CHAR(36) COLLATE utf8mb4_bin,`acl_all` BIGINT,`acl_spec` TINYINT,`frag` LONGTEXT,`f_username` LONGTEXT,`f_bio` LONGTEXT,`f_created_at` VARCHAR(100),KEY `idx_root_id`(`root_id`),KEY `idx_f_created_at`(`f_created_at`)) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE TABLE `g_n_tweet_d2a57d`(`id` CHAR(36) COLLATE utf8mb4_bin PRIMARY KEY,`root_id` CHAR(36) COLLATE utf8mb4_bin,`acl_all` BIGINT,`acl_spec` TINYINT,`frag` LONGTEXT,`f_seed_id` LONGTEXT,`f_content` LONGTEXT,`f_author_username` LONGTEXT,`f_created_at` VARCHAR(100),`f_likes` LONGTEXT,`f_comments` LONGTEXT,KEY `idx_root_id`(`root_id`),KEY `idx_f_created_at`(`f_created_at`)) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

-- SAFE IDENTITY BUSINESS PROJECTION
CREATE TABLE identity_users_business(user_id VARCHAR(100) COLLATE utf8mb4_bin PRIMARY KEY,doc LONGTEXT CHARACTER SET utf8mb4 NOT NULL) ENGINE=InnoDB;
CREATE TABLE identity_lookups_business(value_normalized VARCHAR(190) COLLATE utf8mb4_bin PRIMARY KEY,user_id VARCHAR(100) COLLATE utf8mb4_bin NOT NULL) ENGINE=InnoDB;
