CREATE DATABASE IF NOT EXISTS jac_lx_t20_20261020 CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
USE jac_lx_t20_20261020;
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

USE jac_lx_t20_20261020;

CREATE TABLE lx_profiles(id CHAR(36) COLLATE utf8mb4_bin PRIMARY KEY,username VARCHAR(255) COLLATE utf8mb4_bin UNIQUE,bio LONGTEXT,created_at VARCHAR(100));
INSERT INTO lx_profiles SELECT id,JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.username')),JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.bio')),JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.created_at')) FROM anchors WHERE kind='NodeAnchor' AND arch_type='Profile';
CREATE TABLE lx_follows(follower_id CHAR(36) COLLATE utf8mb4_bin,followee_id CHAR(36) COLLATE utf8mb4_bin,PRIMARY KEY(follower_id,followee_id),KEY reverse_follow(followee_id,follower_id));
INSERT INTO lx_follows SELECT src,dst FROM anchors WHERE kind='EdgeAnchor' AND arch_type='Follow';
CREATE TABLE lx_tweets(id CHAR(36) COLLATE utf8mb4_bin PRIMARY KEY,seed_id VARCHAR(255) COLLATE utf8mb4_bin UNIQUE,author_id CHAR(36) COLLATE utf8mb4_bin,content LONGTEXT,created_at VARCHAR(100),likes LONGTEXT,comments LONGTEXT,KEY author_time(author_id,created_at));
INSERT INTO lx_tweets SELECT t.id,JSON_UNQUOTE(JSON_EXTRACT(t.props,'$.archetype.seed_id')),e.src,JSON_UNQUOTE(JSON_EXTRACT(t.props,'$.archetype.content')),JSON_UNQUOTE(JSON_EXTRACT(t.props,'$.archetype.created_at')),JSON_EXTRACT(t.props,'$.archetype.likes'),JSON_EXTRACT(t.props,'$.archetype.comments') FROM anchors t JOIN anchors e ON e.dst=t.id AND e.kind='EdgeAnchor' AND e.arch_type='Post' WHERE t.kind='NodeAnchor' AND t.arch_type='Tweet';
ANALYZE TABLE anchors,lx_profiles,lx_tweets,lx_follows;

-- SAFE IDENTITY BUSINESS PROJECTION
CREATE TABLE identity_users_business(user_id VARCHAR(100) COLLATE utf8mb4_bin PRIMARY KEY,doc LONGTEXT CHARACTER SET utf8mb4 NOT NULL) ENGINE=InnoDB;
CREATE TABLE identity_lookups_business(value_normalized VARCHAR(190) COLLATE utf8mb4_bin PRIMARY KEY,user_id VARCHAR(100) COLLATE utf8mb4_bin NOT NULL) ENGINE=InnoDB;
