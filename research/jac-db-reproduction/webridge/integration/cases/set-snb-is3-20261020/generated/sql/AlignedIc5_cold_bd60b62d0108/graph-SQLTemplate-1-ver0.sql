SqlNo=1
SQLNode {
    sqlTemplate='SELECT CAST(JSON_UNQUOTE(JSON_EXTRACT(p.props, '$.archetype.person_id')) AS SIGNED), JSON_UNQUOTE(JSON_EXTRACT(p.props, '$.archetype.firstName')) , JSON_UNQUOTE(JSON_EXTRACT(p.props, '$.archetype.lastName')) FROM ( SELECT e.dst AS id FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND e.arch_type = 'Knows' UNION ALL SELECT e.src AS id FROM anchors e WHERE e.dst = ? AND e.kind = 'EdgeAnchor' AND e.arch_type = 'Knows' ) f JOIN anchors p ON p.id = f.id AND p.kind = 'NodeAnchor' AND p.arch_type = 'Person' ORDER BY CAST(JSON_UNQUOTE(JSON_EXTRACT(p.props, '$.archetype.person_id')) AS SIGNED)',
    parameters={M_L_String__REQUEST_PARAM_person_jid:VARCHAR, M_L_String__REQUEST_PARAM_person_jid:VARCHAR},
    retVals={com.alibaba.druid.sql.ast.expr.sqlcastexpr@6f850a7f:BIGINT, json_unquote(json_extract(p.props, '$.archetype.firstname')):LONGTEXT, json_unquote(json_extract(p.props, '$.archetype.lastname')):LONGTEXT}
}
