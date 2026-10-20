SqlNo=1
SQLNode {
    sqlTemplate='SELECT JSON_EXTRACT(props, '$.archetype') FROM anchors WHERE id = ?',
    parameters={M_L_String__REQUEST_PARAM_person_jid:VARCHAR},
    retVals={json_extract(props, '$.archetype'):LONGTEXT}
}
SqlNo=2
SQLNode {
    sqlTemplate='SELECT id, arch_type, props FROM ( (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 10) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie, m.arch_type, m.props FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 10) ) u ORDER BY ord DESC, tie ASC LIMIT 10',
    parameters={M_L_String__REQUEST_PARAM_person_jid:VARCHAR, "Post":VARCHAR, 9223372036854775807:BIGINT, M_L_String__REQUEST_PARAM_person_jid:VARCHAR, "Comment":VARCHAR, 9223372036854775807:BIGINT},
    retVals={id:VARCHAR, arch_type:VARCHAR, props:LONGTEXT}
}
SqlNo=3
SQLNode {
    sqlTemplate='SELECT m.id, m.root_of_replyof, p.props FROM jac_snb_message_mirror m JOIN anchors p ON p.id = m.root_of_replyof WHERE m.id IN (?, ?) AND m.root_of_replyof IS NOT NULL',
    parameters={RS_q2_r9_col1:VARCHAR, RS_q2_r10_col1:VARCHAR},
    retVals={m.id:VARCHAR, m.root_of_replyof:VARCHAR, p.props:LONGTEXT}
}
SqlNo=4
SQLNode {
    sqlTemplate='SELECT e.src, n.props FROM anchors e JOIN anchors n ON n.id = e.dst AND n.kind = 'NodeAnchor' WHERE e.kind = 'EdgeAnchor' AND e.arch_type = 'HasCreator' AND e.src IN (?, ?) ORDER BY e.seq, e.id',
    parameters={RS_q3_r1_col2:VARCHAR, RS_q3_r2_col2:VARCHAR},
    retVals={e.src:VARCHAR, n.props:LONGTEXT}
}
