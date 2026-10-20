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
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=4
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?, ?, ?, ?, ?, ?)',
    parameters={RS_q3_r1_col1:VARCHAR, RS_q3_r2_col1:VARCHAR, RS_q3_r3_col1:VARCHAR, RS_q3_r4_col1:VARCHAR, RS_q3_r5_col1:VARCHAR, RS_q3_r6_col1:VARCHAR, RS_q3_r7_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=5
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Knows":VARCHAR, "Knows":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q2_r1_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=6
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?, ?)',
    parameters={RS_q5_r1_col1:VARCHAR, RS_q5_r2_col1:VARCHAR, RS_q5_r3_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=7
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) WHERE CAST(JSON_UNQUOTE(JSON_EXTRACT(e.props, '$.archetype.joinDate')) AS SIGNED) > ? ORDER BY e.seq, e.id',
    parameters={RS_q4_r5_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r5_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r5_col1:VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value:BIGINT},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=8
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) WHERE CAST(JSON_UNQUOTE(JSON_EXTRACT(e.props, '$.archetype.joinDate')) AS SIGNED) > ? ORDER BY e.seq, e.id',
    parameters={RS_q4_r1_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r1_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r1_col1:VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value:BIGINT},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=9
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) WHERE CAST(JSON_UNQUOTE(JSON_EXTRACT(e.props, '$.archetype.joinDate')) AS SIGNED) > ? ORDER BY e.seq, e.id',
    parameters={RS_q4_r2_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r2_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r2_col1:VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value:BIGINT},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=10
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) WHERE CAST(JSON_UNQUOTE(JSON_EXTRACT(e.props, '$.archetype.joinDate')) AS SIGNED) > ? ORDER BY e.seq, e.id',
    parameters={RS_q4_r6_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r6_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r6_col1:VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value:BIGINT},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=11
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q10_r1_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=12
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) WHERE CAST(JSON_UNQUOTE(JSON_EXTRACT(e.props, '$.archetype.joinDate')) AS SIGNED) > ? ORDER BY e.seq, e.id',
    parameters={RS_q4_r3_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r3_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r3_col1:VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value:BIGINT},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=13
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) WHERE CAST(JSON_UNQUOTE(JSON_EXTRACT(e.props, '$.archetype.joinDate')) AS SIGNED) > ? ORDER BY e.seq, e.id',
    parameters={RS_q4_r7_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r7_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r7_col1:VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value:BIGINT},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=14
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) WHERE CAST(JSON_UNQUOTE(JSON_EXTRACT(e.props, '$.archetype.joinDate')) AS SIGNED) > ? ORDER BY e.seq, e.id',
    parameters={RS_q4_r4_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r4_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q4_r4_col1:VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value:BIGINT},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=15
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) WHERE CAST(JSON_UNQUOTE(JSON_EXTRACT(e.props, '$.archetype.joinDate')) AS SIGNED) > ? ORDER BY e.seq, e.id',
    parameters={RS_q6_r1_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q6_r1_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q6_r1_col1:VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value:BIGINT},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=16
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) WHERE CAST(JSON_UNQUOTE(JSON_EXTRACT(e.props, '$.archetype.joinDate')) AS SIGNED) > ? ORDER BY e.seq, e.id',
    parameters={RS_q6_r3_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q6_r3_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q6_r3_col1:VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value:BIGINT},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=17
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.src = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) WHERE CAST(JSON_UNQUOTE(JSON_EXTRACT(e.props, '$.archetype.joinDate')) AS SIGNED) > ? ORDER BY e.seq, e.id',
    parameters={RS_q6_r2_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q6_r2_col1:VARCHAR, "HasMember":VARCHAR, "HasMember":VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, RS_q6_r2_col1:VARCHAR, "Forum":VARCHAR, "Forum":VARCHAR, M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value:BIGINT},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=18
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q11_r1_col1:VARCHAR, "ContainerOf":VARCHAR, "ContainerOf":VARCHAR, "Post":VARCHAR, "Post":VARCHAR, RS_q11_r1_col1:VARCHAR, "ContainerOf":VARCHAR, "ContainerOf":VARCHAR, "Post":VARCHAR, "Post":VARCHAR, RS_q11_r1_col1:VARCHAR, "Post":VARCHAR, "Post":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=19
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    parameters={RS_q18_r1_col1:VARCHAR, RS_q18_r2_col1:VARCHAR, RS_q18_r3_col1:VARCHAR, RS_q18_r4_col1:VARCHAR, RS_q18_r5_col1:VARCHAR, RS_q18_r6_col1:VARCHAR, RS_q18_r7_col1:VARCHAR, RS_q18_r8_col1:VARCHAR, RS_q18_r9_col1:VARCHAR, RS_q18_r10_col1:VARCHAR, RS_q18_r11_col1:VARCHAR, RS_q18_r12_col1:VARCHAR, RS_q18_r13_col1:VARCHAR, RS_q18_r14_col1:VARCHAR, RS_q18_r15_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=20
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r5_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r5_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r5_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=21
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q20_r1_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
SqlNo=22
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r11_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r11_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r11_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=23
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r4_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r4_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r4_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=24
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r1_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r1_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r1_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=25
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r13_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r13_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r13_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=26
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r10_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r10_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r10_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=27
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r15_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r15_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r15_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=28
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r14_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r14_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r14_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=29
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r2_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r2_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r2_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=30
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r12_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r12_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r12_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=31
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r9_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r9_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r9_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=32
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r7_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r7_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r7_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=33
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r3_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r3_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r3_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=34
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r6_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r6_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r6_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=35
SQLNode {
    sqlTemplate='SELECT n.id, e.id FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={RS_q19_r8_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r8_col1:VARCHAR, "HasCreator":VARCHAR, "HasCreator":VARCHAR, "Person":VARCHAR, "Person":VARCHAR, RS_q19_r8_col1:VARCHAR, "Person":VARCHAR, "Person":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
