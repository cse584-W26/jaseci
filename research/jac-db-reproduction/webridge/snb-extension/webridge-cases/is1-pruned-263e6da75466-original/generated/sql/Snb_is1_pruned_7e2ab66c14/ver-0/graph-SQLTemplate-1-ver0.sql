SqlNo=1
SQLNode {
    sqlTemplate='SELECT JSON_EXTRACT(props, '$.archetype') FROM anchors WHERE id = ?',
    parameters={M_L_String__REQUEST_PARAM_person_jid:VARCHAR},
    retVals={json_extract(props, '$.archetype'):LONGTEXT}
}
SqlNo=2
SQLNode {
    sqlTemplate='SELECT n.id, e.id, JSON_EXTRACT(n.props, '$.archetype') FROM ( SELECT e.* FROM anchors e WHERE e.src = ? AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.dst_type IS NULL OR e.dst_type = ? OR e.dst_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) UNION ALL SELECT e.* FROM anchors e WHERE e.dst = ? AND e.undirected = 1 AND e.src <> e.dst AND e.kind = 'EdgeAnchor' AND (e.arch_type = ? OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) AND (e.src_type IS NULL OR e.src_type = ? OR e.src_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ) e JOIN anchors n ON n.id = CASE  WHEN e.src = ? THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' AND (n.arch_type = ? OR n.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = ? )) ORDER BY e.seq, e.id',
    parameters={M_L_String__REQUEST_PARAM_person_jid:VARCHAR, "IsLocatedIn":VARCHAR, "IsLocatedIn":VARCHAR, "Place":VARCHAR, "Place":VARCHAR, M_L_String__REQUEST_PARAM_person_jid:VARCHAR, "IsLocatedIn":VARCHAR, "IsLocatedIn":VARCHAR, "Place":VARCHAR, "Place":VARCHAR, M_L_String__REQUEST_PARAM_person_jid:VARCHAR, "Place":VARCHAR, "Place":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR, json_extract(n.props, '$.archetype'):LONGTEXT}
}
