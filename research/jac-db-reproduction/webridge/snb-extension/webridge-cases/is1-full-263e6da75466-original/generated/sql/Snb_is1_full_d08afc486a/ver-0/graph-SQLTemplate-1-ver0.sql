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
    parameters={RS_q2_r1_col1:VARCHAR, "IsLocatedIn":VARCHAR, "IsLocatedIn":VARCHAR, "Place":VARCHAR, "Place":VARCHAR, RS_q2_r1_col1:VARCHAR, "IsLocatedIn":VARCHAR, "IsLocatedIn":VARCHAR, "Place":VARCHAR, "Place":VARCHAR, RS_q2_r1_col1:VARCHAR, "Place":VARCHAR, "Place":VARCHAR},
    retVals={n.id:VARCHAR, e.id:VARCHAR}
}
SqlNo=4
SQLNode {
    sqlTemplate='SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)',
    parameters={RS_q3_r1_col1:VARCHAR},
    retVals={a.id:VARCHAR, a.kind:VARCHAR, a.arch_type:VARCHAR, a.arch_module:VARCHAR, a.fingerprint:VARCHAR, a.root_id:VARCHAR, a.src:VARCHAR, a.dst:VARCHAR, a.undirected:BOOLEAN, a.props:LONGTEXT, a.row_version:VARCHAR}
}
