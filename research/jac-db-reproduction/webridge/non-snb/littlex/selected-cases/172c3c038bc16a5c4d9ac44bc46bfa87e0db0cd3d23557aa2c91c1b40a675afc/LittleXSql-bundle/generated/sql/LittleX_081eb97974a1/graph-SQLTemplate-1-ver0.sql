SqlNo=1
SQLNode {
    sqlTemplate='set autocommit=0',
    parameters={},
    retVals={}
}
SqlNo=2
SQLNode {
    sqlTemplate='UPDATE lx_tweets t JOIN lx_profiles p ON p.id = ? SET t.likes = JSON_ARRAY_APPEND(t.likes, '$', p.username) WHERE t.id = ? AND NOT JSON_CONTAINS(t.likes, JSON_QUOTE(p.username))',
    parameters={M_L_String__REQUEST_PARAM_actor_id:VARCHAR, M_L_String__REQUEST_PARAM_tweet_id:VARCHAR},
    retVals={}
}
SqlNo=3
SQLNode {
    sqlTemplate='SELECT JSON_LENGTH(likes) AS likes_count FROM lx_tweets WHERE id = ?',
    parameters={M_L_String__REQUEST_PARAM_tweet_id:VARCHAR},
    retVals={likes_count:INT}
}
SqlNo=4
SQLNode {
    sqlTemplate='set autocommit=1',
    parameters={},
    retVals={}
}
