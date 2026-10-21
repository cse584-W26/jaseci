"""Categories distinguish actual graph/ACL/projection work in emitted littleX SQL."""
def category(sql):
 s=' '.join(sql.lower().split())
 if s.startswith('begin'):return'transaction.begin'
 if s.startswith('set local'):return'transaction.setting'
 if s in ('commit','rollback'):return'transaction.'+s
 if s.startswith('deallocate'):return'driver.prepared_cache_cleanup'
 if 'identity_users'in s or'identity_lookups'in s:return'identity.lookup'
 if s.startswith('select a.id, a.kind'):return'hydration.full_anchor'
 if s.startswith('insert into anchors'):return'write.anchor_batch_upsert'
 if s.startswith('update anchors'):return'write.anchor_update'
 if s.startswith('insert into graph_types'):return'write.type_registry'
 if "a.arch_type = 'root'"in s and"props->'access'"in s:return'acl.root_permissions'
 if s.startswith('select 1 from anchors')and'not exists'in s and'g_n_'in s:return'mirror.ensure_endpoint'if'src_endpoint'in s else'mirror.ensure_projection'
 if 'jsonb_agg'in s or'jsonb_build_object'in s:return'traversal.feed_JSON_projection'
 if s.startswith('select type_name from graph_types'):return'type_registry.ancestry'
 if 'kv_state'in s or'to_regclass'in s:return'schema.guard'
 if 'g_n_'in s:
  depth='2hop'if'join anchors e2'in s or'select n2.id'in s else'1hop'
  if 'join lateral'in s:return'traversal.'+depth+'.endpoint_lateral_topk_projection_acl'
  if 'src_endpoint'in s:return'traversal.'+depth+'.endpoint_projection_acl'+('.topk'if'limit'in s else'')
  return'traversal.'+depth+'.projection_acl'+('.topk'if'limit'in s else'')
 if s.startswith('select n1.id, e1.id'):return'traversal.generic_1hop'
 if s.startswith('select n2.id, e2.id'):return'traversal.generic_2hop'
 if 'kv_state'in s or'to_regclass'in s:return'schema.guard'
 if 'pg_'in s or'information_schema'in s:return'schema.catalog'
 return'unclassified'
