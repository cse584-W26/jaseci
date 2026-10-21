SqlNo=1
SQLNode {
    sqlTemplate='set autocommit=0',
    parameters={},
    retVals={}
}
SqlNo=2
SQLNode {
    sqlTemplate='SELECT n1.id, e1.id, n1.props FROM ( SELECT ? AS id, 1 AS ord ) f0 LEFT JOIN anchors s1 ON s1.id = f0.id JOIN anchors e1 ON e1.kind = 'EdgeAnchor' AND ((e1.src = f0.id AND (e1.dst_type IS NULL OR (e1.dst_type = ? OR e1.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )))) OR (e1.undirected AND (e1.dst = f0.id AND (e1.src_type IS NULL OR (e1.src_type = ? OR e1.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )))))) JOIN anchors n1 ON n1.id = CASE  WHEN e1.src = f0.id THEN e1.dst ELSE e1.src END AND n1.kind = 'NodeAnchor' AND (n1.arch_type = ? OR n1.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY f0.ord, e1.seq, e1.id',
    parameters={M_L_String__REQUEST_PARAM_actor_root_id:VARCHAR, "Profile":VARCHAR, "Profile":VARCHAR, "Profile":VARCHAR, "Profile":VARCHAR, "Profile":VARCHAR, "Profile":VARCHAR},
    retVals={n1.id:VARCHAR, e1.id:VARCHAR, n1.props:LONGTEXT}
}
SqlNo=3
SQLNode {
    sqlTemplate='INSERT INTO anchors (id, kind, arch_type, arch_module, fingerprint , root_id, src, dst, undirected, props , src_type, dst_type, seq) VALUES (?, ?, ?, ?, ? , ?, ?, ?, ?, ? , ?, ?, ?), (?, ?, ?, ?, ? , ?, ?, ?, ?, ? , ?, ?, ?) ON DUPLICATE KEY UPDATE kind = VALUES(kind), arch_type = VALUES(arch_type), arch_module = VALUES(arch_module), fingerprint = VALUES(fingerprint), root_id = VALUES(root_id) , src = VALUES(src), dst = VALUES(dst), undirected = VALUES(undirected), props = VALUES(props), src_type = COALESCE(VALUES(src_type), src_type) , dst_type = COALESCE(VALUES(dst_type), dst_type)',
    parameters={M_L_String__REQUEST_PARAM_new_edge_id:VARCHAR, "EdgeAnchor":VARCHAR, "Post":VARCHAR, "app":VARCHAR, "0257ab8108739b8f":VARCHAR, M_L_String__REQUEST_PARAM_actor_root_id:VARCHAR, M_L_String__REQUEST_PARAM_actor_id:VARCHAR, M_L_String__REQUEST_PARAM_new_id:VARCHAR, "0":BOOLEAN, "{\"id\":\"173b653c-85d5-5292-9bef-8327e7d94f92\",\"root\":\"a6aa67a9-a09f-4b90-87d2-b404400d176d\",\"access\":{\"all\":-1,\"roots\":{\"anchors\":{}}},\"source\":\"be88871d-b7c9-4cef-b134-df8946207f84\",\"target\":\"31608e37-3266-5b36-bb93-4b408d02c300\",\"__type__\":\"EdgeAnchor\",\"archetype\":{\"__type__\":\"Post\",\"__module__\":\"app\"},\"__module__\":\"jaclang.jac0core.archetype\",\"persistent\":true,\"is_undirected\":false}":LONGTEXT, "Profile":VARCHAR, "Tweet":VARCHAR, M_L_String__REQUEST_PARAM_new_edge_seq:BIGINT, M_L_String__REQUEST_PARAM_new_id:VARCHAR, "NodeAnchor":VARCHAR, "Tweet":VARCHAR, "app":VARCHAR, "552e15e3e79578ff":VARCHAR, M_L_String__REQUEST_PARAM_actor_root_id:VARCHAR, NULL:VARCHAR, NULL:VARCHAR, "0":BOOLEAN, "{\"id\":\"31608e37-3266-5b36-bb93-4b408d02c300\",\"root\":\"a6aa67a9-a09f-4b90-87d2-b404400d176d\",\"access\":{\"all\":2,\"roots\":{\"anchors\":{}}},\"version\":0,\"__type__\":\"NodeAnchor\",\"archetype\":{\"likes\":[],\"content\":\"write bench tweet -1 #bench\",\"seed_id\":\"w2_-1\",\"__type__\":\"Tweet\",\"comments\":[],\"__module__\":\"app\",\"created_at\":\"2026-10-20T23:00:00.000000Z\",\"author_username\":\"t20_sim_user_0\"},\"__module__\":\"jaclang.jac0core.archetype\",\"persistent\":true}":LONGTEXT, NULL:VARCHAR, NULL:VARCHAR, M_L_String__REQUEST_PARAM_new_seq:BIGINT},
    retVals={}
}
SqlNo=4
SQLNode {
    sqlTemplate='set autocommit=1',
    parameters={},
    retVals={}
}

======================================================
