DROP PROCEDURE IF EXISTS `LittleX_dd26f11d80bf_sp_1_ver0`;
DELIMITER $$
CREATE PROCEDURE LittleX_dd26f11d80bf_sp_1_ver0 (IN M_L_String__REQUEST_PARAM_actor_id VARCHAR(512))
BEGIN

DECLARE QUERY_ID_0_TXN INT DEFAULT NULL;
DECLARE q2_i1 VARCHAR(512) DEFAULT NULL;
DECLARE q2_i2 VARCHAR(512) DEFAULT NULL;
DECLARE QUERY_ID_1 INT DEFAULT NULL;
DECLARE M_I_RS_2_size INT DEFAULT NULL;
DECLARE cursor_cnt_1 INT DEFAULT NULL;
DECLARE QUERY_ID_2_TXN INT DEFAULT NULL;

IF TRUE THEN
SET QUERY_ID_0_TXN = 0;
set autocommit=0;
END IF;
IF TRUE THEN
SET q2_i1 = M_L_String__REQUEST_PARAM_actor_id;
SET q2_i2 = M_L_String__REQUEST_PARAM_actor_id;
SET QUERY_ID_1 = 1;
SELECT t.seed_id, t.content, p.username, t.created_at, t.likes , t.comments FROM lx_tweets t JOIN lx_profiles p ON p.id = t.author_id WHERE t.author_id = q2_i1 OR t.author_id IN ( SELECT followee_id FROM lx_follows WHERE follower_id = q2_i2 ) ORDER BY t.created_at DESC LIMIT 20;
SET M_I_RS_2_size = FOUND_ROWS();
END IF;
IF TRUE THEN
SET QUERY_ID_2_TXN = 2;
set autocommit=1;
END IF;
SELECT QUERY_ID_0_TXN,QUERY_ID_1,q2_i1,q2_i2,QUERY_ID_2_TXN;

END $$
DELIMITER ;