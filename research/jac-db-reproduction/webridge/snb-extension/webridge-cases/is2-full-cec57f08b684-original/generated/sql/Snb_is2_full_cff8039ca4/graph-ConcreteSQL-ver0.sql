SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT id, props, root_id FROM anchors WHERE id IN (?)
SELECT doc FROM identity_users WHERE user_id = ?
SELECT t.doc FROM identity_users t JOIN identity_lookups lk ON t.user_id = lk.user_id WHERE lk.value_normalized = ? AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(t.doc, '$.status')), 'active') <> 'disabled'
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT id FROM ( (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 10) UNION ALL (SELECT m.id, m.creation_date AS ord, m.tie_id AS tie FROM jac_snb_message_mirror m WHERE m.creator_id = ? AND m.arch_type = ? AND m.creation_date <= ? ORDER BY m.creation_date DESC, m.tie_id ASC LIMIT 10) ) u ORDER BY ord DESC, tie ASC LIMIT 10
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?)
SELECT m.id, m.root_of_replyof FROM jac_snb_message_mirror m WHERE m.id IN (?, ?) AND m.root_of_replyof IS NOT NULL
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?)
SELECT n.id, e.id FROM anchors e JOIN anchors n ON n.id = CASE  WHEN e.src IN (?, ?) THEN e.dst ELSE e.src END AND n.kind = 'NodeAnchor' WHERE e.kind = 'EdgeAnchor' AND (e.arch_type = 'HasCreator' OR e.arch_type IN ( SELECT type_name FROM graph_types WHERE ancestor = 'HasCreator' )) AND (e.src IN (?, ?) OR (e.undirected = 1 AND e.dst IN (?, ?))) ORDER BY e.seq, e.id
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?)
SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint , a.root_id, a.src, a.dst, a.undirected, a.props , a.row_version FROM anchors a WHERE a.id IN (?, ?)
