set autocommit=0
SELECT t.seed_id, t.content, p.username, t.created_at, t.likes , t.comments FROM lx_tweets t JOIN lx_profiles p ON p.id = t.author_id WHERE t.author_id = ? OR t.author_id IN ( SELECT followee_id FROM lx_follows WHERE follower_id = ? ) ORDER BY t.created_at DESC LIMIT 20
set autocommit=1
