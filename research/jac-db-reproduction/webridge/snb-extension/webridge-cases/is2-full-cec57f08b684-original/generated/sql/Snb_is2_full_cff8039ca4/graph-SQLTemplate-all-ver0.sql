SqlNo=1
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={"4bc418b3-c394-41ee-93fd-4a13a6c852a8":VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=2
SQLNode {
    sqlTemplate='SELECT id, props, root_id FROM anchors WHERE id IN (?)',
    parameters={M_L_String__REQUEST_PARAM_person_jid:VARCHAR},
    retVals={id:VARCHAR, props:LONGTEXT, root_id:VARCHAR}
}
SqlNo=3
SQLNode {
    sqlTemplate='SELECT doc FROM identity_users WHERE user_id = ?',
    parameters={"__guest__":VARCHAR},
    retVals={doc:LONGTEXT}
}
SqlNo=4
SQLNode {
    sqlTemplate='SELECT t.doc FROM identity_users t JOIN identity_lookups lk ON t.user_id = lk.user_id WHERE lk.value_normalized = ? AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(t.doc, '$.status')), 'active') <> 'disabled'',
    parameters={"__guest__":VARCHAR},
    retVals={t.doc:LONGTEXT}
}
SqlNo=5
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={"4bc418b3-c394-41ee-93fd-4a13a6c852a8":VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=6
SQLNode {
    sqlTemplate='SELECT id FROM ( (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 10) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 10) ) u ORDER BY ord DESC, tie ASC LIMIT 10',
    parameters={RS_q2_r1_col1:VARCHAR, "Post":VARCHAR, 9223372036854775807:BIGINT, RS_q2_r1_col1:VARCHAR, "Comment":VARCHAR, 9223372036854775807:BIGINT},
    retVals={id:VARCHAR}
}
SqlNo=7
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q6_r1_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=8
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q6_r2_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=9
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q6_r3_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=10
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q6_r4_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=11
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q6_r5_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=12
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q6_r6_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=13
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q6_r7_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=14
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q6_r8_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=15
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q6_r9_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=16
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q6_r10_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=17
SQLNode {
    sqlTemplate='SELECT m.id, m.root_of_replyof FROM jac_snb_message_mirror m WHERE m.id IN (?, ?) AND m.root_of_replyof IS NOT NULL',
    parameters={RS_q15_r1_col1:VARCHAR, RS_q16_r1_col1:VARCHAR},
    retVals={m.id:VARCHAR, m.root_of_replyof:VARCHAR}
}
SqlNo=18
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?)',
    parameters={RS_q17_r1_col2:VARCHAR, RS_q17_r2_col2:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=19
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM anchors e JOIN anchors n ON n.id = CASE  WHEN e.src IN (?, ?) THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' WHERE e.kind = 'EdgeAnchor' AND (e.arch_type = 'HasCreator' OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = 'HasCreator' )) AND (e.src IN (?, ?) OR (e.undirected = 1 AND e.dst IN (?, ?))) ORDER BY e.seq, e.id',
    parameters={RS_q18_r2_col1:VARCHAR, RS_q18_r1_col1:VARCHAR, RS_q18_r2_col1:VARCHAR, RS_q18_r1_col1:VARCHAR, RS_q18_r2_col1:VARCHAR, RS_q18_r1_col1:VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=20
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?)',
    parameters={RS_q19_r1_col2:VARCHAR, RS_q19_r2_col2:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=21
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?)',
    parameters={RS_q19_r1_col1:VARCHAR, RS_q19_r2_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}

======================================================
