SqlNo=1
SQLNode {
    sqlTemplate='SELECT p.props, CAST(JSON_UNQUOTE(JSON_EXTRACT(n.props, '$.archetype.place_id')) AS SIGNED) FROM anchors p LEFT JOIN anchors e ON e.src = p.id AND e.kind = 'EdgeAnchor' AND e.arch_type = 'IsLocatedIn' LEFT JOIN anchors n ON n.id = e.dst AND n.kind = 'NodeAnchor' AND n.arch_type = 'Place' WHERE p.id = ? ORDER BY e.seq, e.id LIMIT 1',
    parameters={M_L_String__REQUEST_PARAM_person_jid:VARCHAR},
    retVals={p.props:LONGTEXT, com.alibaba.druid.sql.ast.expr.sqlcastexpr@60b2183c:BIGINT}
}

======================================================
