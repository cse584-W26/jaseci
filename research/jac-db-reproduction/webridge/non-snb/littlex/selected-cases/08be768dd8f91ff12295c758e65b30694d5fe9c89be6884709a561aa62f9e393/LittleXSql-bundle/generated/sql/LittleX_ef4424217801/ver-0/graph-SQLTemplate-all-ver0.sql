SqlNo=1
SQLNode {
    sqlTemplate='set autocommit=0',
    parameters={},
    retVals={}
}
SqlNo=2
SQLNode {
    sqlTemplate='INSERT IGNORE INTO lx_follows (follower_id, followee_id) SELECT p.id, t.id FROM lx_profiles p JOIN lx_profiles t ON t.id = ? WHERE p.id = ?',
    parameters={M_L_String__REQUEST_PARAM_target_id:VARCHAR, M_L_String__REQUEST_PARAM_actor_id:VARCHAR},
    retVals={}
}
SqlNo=3
SQLNode {
    sqlTemplate='set autocommit=1',
    parameters={},
    retVals={}
}

======================================================
