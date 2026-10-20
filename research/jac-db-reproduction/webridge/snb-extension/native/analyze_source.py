import pathlib,json,gzip,re,collections
R=pathlib.Path(__file__).resolve().parent;D=R/'source-census';events=[]
eventpath=D/'trace/events.jsonl';eventtext=eventpath.read_text()if eventpath.exists()else gzip.open(str(eventpath)+'.gz','rt').read()
for s in eventtext.splitlines():
 try:events.append(json.loads(s))
 except json.JSONDecodeError:pass

def sql_records(text,pids):
 out=[]
 for entry in re.split(r'(?=^\d{4}-\d\d-\d\d )',text,flags=re.M):
  m=re.search(r'\[(\d+)\] LOG:  duration: ([\d.]+) ms\s+(execute ([^:]+)|statement):\s*(.*)',entry,re.S)
  if m and int(m[1])in pids:out.append({'pid':int(m[1]),'execute_ms':float(m[2]),'statement':m[4],'sql':m[5].strip()})
 return out

def cat(sql):
 s=' '.join(sql.split());l=s.lower()
 if 'to_regclass(v.n)'in l:return'schema.ttl_guard'
 if l.startswith('begin'):return'transaction.begin'
 if l.startswith('set local'):return'transaction.setting'
 if l=='commit':return'transaction.commit'
 if 'select a.id, a.kind'in l:return'hydration.full_anchor'
 if l.startswith('select type_name from graph_types'):return'type_registry'
 if l.startswith('with recursive'):return'closure.recursive'
 if 'root_of_'in l:return'reply_root.promoted_column'
 if 'lateral'in l and'limit'in l:return'topk.lateral'
 if 'order by'in l and'limit'in l and('g_n_post'in l or'g_n_comment'in l):return'topk.mirror'
 if l.startswith('select n1.id, e1.id'):return'traversal.generic'
 if 'select distinct nb.dst from adj_knows'in l:return'closure.frontier_adjacency'
 if 'identity_users'in l:return'identity.guest_resolution'
 if "a.arch_type = 'root'"in l and"a.props->'access'"in l:return'acl.root_permissions'
 if 'select m.id from g_n_person'in l:return'closure.endpoint_filter'
 if l.startswith('select id, root_id, acl_all'):return'projection.person_fields_acl'
 if 'g_n_'in l:return'projection.graph_hop_acl'
 if 'pg_'in l or'information_schema'in l:return'catalog.check'
 return'other'
summary={}
for query in ['is1','is3','ic1','ic13','is2','ic2']:
 d=D/query;path=d/'rows.jsonl'
 if not path.exists():continue
 rows=[json.loads(s)for s in path.read_text().splitlines()];profiles=[x for x in rows if not x['warmup']]
 if len(profiles)!=3:continue
 analyzed=[]
 for row in profiles:
  es=[x for x in events if x['request_tag']==row['request_tag']];pids={x['backend_pid']for x in es if x['event']=='frame'and x.get('backend_pid')};records=sql_records(gzip.open(d/f'profile-{row["iteration"]-10}.log.gz','rt').read(),pids);front=[x for x in es if x['event']=='frame'and x['direction']=='frontend'];back=[x for x in es if x['event']=='frame'and x['direction']=='backend'];ops=[]
  for i,x in enumerate(records):ops.append(x|{'sequence':i+1,'category':cat(x['sql'])})
  analyzed.append({'query':query,'request_tag':row['request_tag'],'sql_count':len(ops),'frontend_types':dict(collections.Counter(x['type']for x in front)),'backend_ready':sum(x['type']=='Z'for x in back),'backend_pids':sorted(pids),'categories':dict(collections.Counter(x['category']for x in ops)),'operations':ops})
 (d/'sql-census.json').write_text(json.dumps({'profiles':analyzed,'all_outputs_historical_hash_match':all(x['parity']for x in profiles)},indent=2));summary[query]={'counts':[x['sql_count']for x in analyzed],'categories':analyzed[0]['categories'],'oracle':str(d/'oracle.json')}
(D/'census-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
