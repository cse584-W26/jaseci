
        SELECT a.id, a.kind, a.arch_type, a.arch_module, a.fingerprint,
               a.root_id, a.src, a.dst, a.undirected, a.props, a.xmin::text
        FROM anchors a WHERE a.id = ANY(CAST($1 AS uuid[]))
        