CREATE DATABASE IF NOT EXISTS jac_tpcc_graph_initial CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
USE jac_tpcc_graph_initial;
CREATE TABLE anchors (
 id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin PRIMARY KEY,
 c_last VARCHAR(100),kind VARCHAR(32) NOT NULL,arch_type VARCHAR(100) NOT NULL,arch_module VARCHAR(200) NOT NULL,fingerprint VARCHAR(200) NOT NULL,
 root_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,src CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,dst CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
 undirected BOOLEAN NOT NULL,props LONGTEXT CHARACTER SET utf8mb4 NOT NULL,row_version VARCHAR(32),seq BIGINT NOT NULL,
 src_type VARCHAR(100),dst_type VARCHAR(100),KEY source_type(src,arch_type),KEY target_type(dst,arch_type),KEY kind_type(kind,arch_type),KEY owner_root(root_id)
) ENGINE=InnoDB;
CREATE TABLE graph_types(type_name VARCHAR(100) NOT NULL,ancestor VARCHAR(100) NOT NULL,PRIMARY KEY(type_name,ancestor));
CREATE TABLE identity_users(user_id VARCHAR(100) PRIMARY KEY,doc LONGTEXT NOT NULL);
CREATE TABLE kv_state(`key` VARCHAR(200) PRIMARY KEY,`value` LONGTEXT,expires_at DATETIME NULL);

USE jac_tpcc_graph_initial;CREATE TABLE identity_lookups(value_normalized VARCHAR(200) COLLATE utf8mb4_bin PRIMARY KEY,user_id VARCHAR(200) COLLATE utf8mb4_bin NOT NULL,KEY(user_id));
