SqlNo=1
SQLNode {
    sqlTemplate='set autocommit=0',
    parameters={},
    retVals={}
}
SqlNo=2
SQLNode {
    sqlTemplate='INSERT INTO lx_tweets (id, seed_id, author_id, content, created_at , likes, comments) SELECT ?, ?, p.id, ?, ? , '[]', '[]' FROM lx_profiles p WHERE p.id = ?',
    parameters={M_L_String__REQUEST_PARAM_new_id:LONGTEXT, M_L_String__REQUEST_PARAM_seed_id:LONGTEXT, M_L_String__REQUEST_PARAM_content:LONGTEXT, M_L_String__REQUEST_PARAM_created_at:LONGTEXT, M_L_String__REQUEST_PARAM_actor_id:VARCHAR},
    retVals={}
}
SqlNo=3
SQLNode {
    sqlTemplate='SELECT t.seed_id, t.content, p.username, t.created_at, t.likes , t.comments FROM lx_tweets t JOIN lx_profiles p ON p.id = t.author_id WHERE t.id = ?',
    parameters={M_L_String__REQUEST_PARAM_new_id:VARCHAR},
    retVals={t.seed_id:VARCHAR, t.content:LONGTEXT, p.username:VARCHAR, t.created_at:VARCHAR, t.likes:LONGTEXT, t.comments:LONGTEXT}
}
SqlNo=4
SQLNode {
    sqlTemplate='set autocommit=1',
    parameters={},
    retVals={}
}

======================================================
