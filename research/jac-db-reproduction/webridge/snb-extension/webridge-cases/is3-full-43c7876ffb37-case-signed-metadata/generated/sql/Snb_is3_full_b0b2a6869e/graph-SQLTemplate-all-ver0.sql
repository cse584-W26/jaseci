SqlNo=1
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={"4bc418b3-c394-41ee-93fd-4a13a6c852a8":VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=2
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={M_L_String__REQUEST_PARAM_person_jid:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=3
SQLNode {
    sqlTemplate='SELECT type_name FROM graph_types WHERE ancestor = ?',
    parameters={"Person":VARCHAR},
    retVals={type_name:VARCHAR}
}
SqlNo=4
SQLNode {
    sqlTemplate='SELECT a.id , CASE  WHEN JSON_TYPE(JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', ?, '"'))) IN ('INTEGER', 'DOUBLE') THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', ?, '"'))) AS SIGNED) END AS root_grant , CASE  WHEN JSON_TYPE(JSON_EXTRACT(a.props, '$.access.all')) IN ('INTEGER', 'DOUBLE') THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props, '$.access.all')) AS SIGNED) ELSE -1 END AS global_grant FROM anchors a WHERE a.kind = 'NodeAnchor' AND a.arch_type = 'Root' AND (JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', ?, '"')) IS NOT NULL OR JSON_TYPE(JSON_EXTRACT(a.props, '$.access.all')) IN ('INTEGER', 'DOUBLE'))',
    parameters={"4bc418b3-c394-41ee-93fd-4a13a6c852a8":LONGTEXT, "4bc418b3-c394-41ee-93fd-4a13a6c852a8":LONGTEXT, "4bc418b3-c394-41ee-93fd-4a13a6c852a8":LONGTEXT},
    retVals={a.id:VARCHAR, root_grant:BIGINT, global_grant:BIGINT}
}
SqlNo=5
SQLNode {
    sqlTemplate='SELECT doc FROM identity_users WHERE user_id = ?',
    parameters={"__guest__":VARCHAR},
    retVals={doc:LONGTEXT}
}
SqlNo=6
SQLNode {
    sqlTemplate='SELECT t.doc FROM identity_users t JOIN identity_lookups lk ON t.user_id = lk.user_id WHERE lk.value_normalized = ? AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(t.doc, '$.status')), 'active') <> 'disabled'',
    parameters={"__guest__":VARCHAR},
    retVals={t.doc:LONGTEXT}
}
SqlNo=7
SQLNode {
    sqlTemplate='SELECT n.id, e.id, n.props, n.root_id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR, n.props:LONGTEXT, n.root_id:VARCHAR}
}
SqlNo=8
SQLNode {
    sqlTemplate='SELECT a.id , CASE  WHEN JSON_TYPE(JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', ?, '"'))) IN ('INTEGER', 'DOUBLE') THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', ?, '"'))) AS SIGNED) END AS root_grant , CASE  WHEN JSON_TYPE(JSON_EXTRACT(a.props, '$.access.all')) IN ('INTEGER', 'DOUBLE') THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props, '$.access.all')) AS SIGNED) ELSE -1 END AS global_grant FROM anchors a WHERE a.kind = 'NodeAnchor' AND a.arch_type = 'Root' AND (JSON_EXTRACT(a.props, CONCAT('$.access.roots.anchors."', ?, '"')) IS NOT NULL OR JSON_TYPE(JSON_EXTRACT(a.props, '$.access.all')) IN ('INTEGER', 'DOUBLE'))',
    parameters={"4bc418b3-c394-41ee-93fd-4a13a6c852a8":LONGTEXT, "4bc418b3-c394-41ee-93fd-4a13a6c852a8":LONGTEXT, "4bc418b3-c394-41ee-93fd-4a13a6c852a8":LONGTEXT},
    retVals={a.id:VARCHAR, root_grant:BIGINT, global_grant:BIGINT}
}
SqlNo=9
SQLNode {
    sqlTemplate='SELECT n.id, e.id, n.props, n.root_id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR, n.props:LONGTEXT, n.root_id:VARCHAR}
}

======================================================
