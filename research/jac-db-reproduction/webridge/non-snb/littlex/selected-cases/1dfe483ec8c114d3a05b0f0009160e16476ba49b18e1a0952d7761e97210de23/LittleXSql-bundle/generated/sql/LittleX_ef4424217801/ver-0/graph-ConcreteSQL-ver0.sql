set autocommit=0
INSERT IGNORE INTO lx_follows (follower_id, followee_id) SELECT p.id, t.id FROM lx_profiles p JOIN lx_profiles t ON t.id = ? WHERE p.id = ?
set autocommit=1
