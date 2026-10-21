SqlNo=1
SQLNode {
    sqlTemplate='set autocommit=0',
    parameters={},
    retVals={}
}
SqlNo=2
SQLNode {
    sqlTemplate='SELECT t.seed_id, t.content, p.username, t.created_at, t.likes , t.comments FROM lx_tweets t JOIN lx_profiles p ON p.id = t.author_id WHERE t.author_id = ? OR t.author_id IN ( SELECT followee_id FROM lx_follows WHERE follower_id = ? ) ORDER BY t.created_at DESC',
    parameters={M_L_String__REQUEST_PARAM_actor_id:VARCHAR, M_L_String__REQUEST_PARAM_actor_id:VARCHAR},
    retVals={t.seed_id:VARCHAR, t.content:LONGTEXT, p.username:VARCHAR, t.created_at:VARCHAR, t.likes:LONGTEXT, t.comments:LONGTEXT}
}
SqlNo=3
SQLNode {
    sqlTemplate='set autocommit=1',
    parameters={},
    retVals={}
}

======================================================
