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
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=5
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=6
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?, ?, ?, ?, ?, ?, ?, ?)',
    parameters={RS_q5_r1_col1:VARCHAR, RS_q5_r2_col1:VARCHAR, RS_q5_r3_col1:VARCHAR, RS_q5_r4_col1:VARCHAR, RS_q5_r5_col1:VARCHAR, RS_q5_r6_col1:VARCHAR, RS_q5_r7_col1:VARCHAR, RS_q5_r8_col1:VARCHAR, RS_q5_r9_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=7
SQLNode {
    sqlTemplate='SELECT id FROM ( (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 20) ) u ORDER BY ord DESC, tie ASC LIMIT 20',
    parameters={RS_q5_r1_col1:VARCHAR, "Post":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r1_col1:VARCHAR, "Comment":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r2_col1:VARCHAR, "Post":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r2_col1:VARCHAR, "Comment":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r3_col1:VARCHAR, "Post":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r3_col1:VARCHAR, "Comment":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r4_col1:VARCHAR, "Post":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r4_col1:VARCHAR, "Comment":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r5_col1:VARCHAR, "Post":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r5_col1:VARCHAR, "Comment":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r6_col1:VARCHAR, "Post":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r6_col1:VARCHAR, "Comment":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r7_col1:VARCHAR, "Post":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r7_col1:VARCHAR, "Comment":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r8_col1:VARCHAR, "Post":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r8_col1:VARCHAR, "Comment":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r9_col1:VARCHAR, "Post":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT, RS_q5_r9_col1:VARCHAR, "Comment":VARCHAR, M_J_field_REQUEST_PARAM_max_date_java_lang_Long_value:BIGINT},
    retVals={id:VARCHAR}
}
SqlNo=8
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r1_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=9
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r2_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=10
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r3_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=11
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r4_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=12
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r5_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=13
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r6_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=14
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r7_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=15
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r8_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=16
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r9_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=17
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r10_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=18
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r11_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=19
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r12_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=20
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r13_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=21
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r14_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=22
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r15_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=23
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r16_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=24
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r17_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=25
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r18_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=26
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r19_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=27
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q7_r20_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=28
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM anchors e JOIN anchors n ON n.id = CASE  WHEN e.src IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' WHERE e.kind = 'EdgeAnchor' AND (e.arch_type = 'HasCreator' OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = 'HasCreator' )) AND (e.src IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) OR (e.undirected = 1 AND e.dst IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?))) ORDER BY e.seq, e.id',
    parameters={RS_q8_r1_col1:VARCHAR, RS_q9_r1_col1:VARCHAR, RS_q10_r1_col1:VARCHAR, RS_q11_r1_col1:VARCHAR, RS_q12_r1_col1:VARCHAR, RS_q13_r1_col1:VARCHAR, RS_q14_r1_col1:VARCHAR, RS_q15_r1_col1:VARCHAR, RS_q16_r1_col1:VARCHAR, RS_q17_r1_col1:VARCHAR, RS_q18_r1_col1:VARCHAR, RS_q19_r1_col1:VARCHAR, RS_q20_r1_col1:VARCHAR, RS_q21_r1_col1:VARCHAR, RS_q22_r1_col1:VARCHAR, RS_q23_r1_col1:VARCHAR, RS_q24_r1_col1:VARCHAR, RS_q25_r1_col1:VARCHAR, RS_q26_r1_col1:VARCHAR, RS_q27_r1_col1:VARCHAR, RS_q8_r1_col1:VARCHAR, RS_q9_r1_col1:VARCHAR, RS_q10_r1_col1:VARCHAR, RS_q11_r1_col1:VARCHAR, RS_q12_r1_col1:VARCHAR, RS_q13_r1_col1:VARCHAR, RS_q14_r1_col1:VARCHAR, RS_q15_r1_col1:VARCHAR, RS_q16_r1_col1:VARCHAR, RS_q17_r1_col1:VARCHAR, RS_q18_r1_col1:VARCHAR, RS_q19_r1_col1:VARCHAR, RS_q20_r1_col1:VARCHAR, RS_q21_r1_col1:VARCHAR, RS_q22_r1_col1:VARCHAR, RS_q23_r1_col1:VARCHAR, RS_q24_r1_col1:VARCHAR, RS_q25_r1_col1:VARCHAR, RS_q26_r1_col1:VARCHAR, RS_q27_r1_col1:VARCHAR, RS_q8_r1_col1:VARCHAR, RS_q9_r1_col1:VARCHAR, RS_q10_r1_col1:VARCHAR, RS_q11_r1_col1:VARCHAR, RS_q12_r1_col1:VARCHAR, RS_q13_r1_col1:VARCHAR, RS_q14_r1_col1:VARCHAR, RS_q15_r1_col1:VARCHAR, RS_q16_r1_col1:VARCHAR, RS_q17_r1_col1:VARCHAR, RS_q18_r1_col1:VARCHAR, RS_q19_r1_col1:VARCHAR, RS_q20_r1_col1:VARCHAR, RS_q21_r1_col1:VARCHAR, RS_q22_r1_col1:VARCHAR, RS_q23_r1_col1:VARCHAR, RS_q24_r1_col1:VARCHAR, RS_q25_r1_col1:VARCHAR, RS_q26_r1_col1:VARCHAR, RS_q27_r1_col1:VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=29
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    parameters={RS_q28_r1_col2:VARCHAR, RS_q28_r2_col2:VARCHAR, RS_q28_r3_col2:VARCHAR, RS_q28_r4_col2:VARCHAR, RS_q28_r5_col2:VARCHAR, RS_q28_r6_col2:VARCHAR, RS_q28_r7_col2:VARCHAR, RS_q28_r8_col2:VARCHAR, RS_q28_r9_col2:VARCHAR, RS_q28_r10_col2:VARCHAR, RS_q28_r11_col2:VARCHAR, RS_q28_r12_col2:VARCHAR, RS_q28_r13_col2:VARCHAR, RS_q28_r14_col2:VARCHAR, RS_q28_r15_col2:VARCHAR, RS_q28_r16_col2:VARCHAR, RS_q28_r17_col2:VARCHAR, RS_q28_r18_col2:VARCHAR, RS_q28_r19_col2:VARCHAR, RS_q28_r20_col2:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=30
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    parameters={RS_q28_r1_col1:VARCHAR, RS_q28_r2_col1:VARCHAR, RS_q28_r3_col1:VARCHAR, RS_q28_r4_col1:VARCHAR, RS_q28_r5_col1:VARCHAR, RS_q28_r6_col1:VARCHAR, RS_q28_r7_col1:VARCHAR, RS_q28_r8_col1:VARCHAR, RS_q28_r9_col1:VARCHAR, RS_q28_r10_col1:VARCHAR, RS_q28_r11_col1:VARCHAR, RS_q28_r12_col1:VARCHAR, RS_q28_r13_col1:VARCHAR, RS_q28_r14_col1:VARCHAR, RS_q28_r15_col1:VARCHAR, RS_q28_r16_col1:VARCHAR, RS_q28_r17_col1:VARCHAR, RS_q28_r18_col1:VARCHAR, RS_q28_r19_col1:VARCHAR, RS_q28_r20_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}

======================================================
