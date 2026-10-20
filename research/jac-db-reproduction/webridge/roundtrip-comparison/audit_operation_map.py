#!/usr/bin/env python3
"""Offline independent request boundaries, response completions and CALL work audit."""
import pathlib,json,collections,hashlib,gzip
R=pathlib.Path(__file__).resolve().parent;B=R.parent
read=lambda p:json.loads(p.read_text())
lines=lambda p:[json.loads(x)for x in (gzip.open(str(p)+'.gz','rt')if not p.exists()else p.open())]
result={'protocol':{},'inside_call':{}}
for folder,variants in [('mysql-results',['full','pruned']),('mysql-idiomatic-results',['idiomatic'])]:
 p=R/folder;e=lines(p/'protocol.jsonl');commands=[x for x in e if x['event']=='command'];ends={(x['connection'],x['command_id'],x['stage']):x for x in e if x['event']=='response_complete'}
 assert not [x for x in e if x['event'] in ['overlapping_command','unexpected_column_terminator','unsupported_local_infile','connection_error']]
 assert len(ends)==2*len(commands)
 for v,cid in zip(variants,sorted({x['connection']for x in commands})):
  q=[x for x in commands if x['connection']==cid];bound=[i for i,x in enumerate(q)if x['sql'].startswith('SHOW SESSION STATUS')];rows=lines(p/v/'requests/rows.jsonl');assert len(bound)==len(rows)*2
  for a,b in zip(q,q[1:]):assert ends[(cid,a['id'],'delivered')]['at']<=b['at']
  for phase in ['baseline','sp']:
   receipts=[]
   for i,row in enumerate(rows):
    if row['warmup'] or row['phase']!=phase:continue
    qq=q[bound[2*i]+1:bound[2*i+1]];expected=4 if phase=='sp' or v=='idiomatic' else 38 if v=='full' else 31;assert len(qq)==expected==row['questions'] and row['oracle_ok']
    rr=[ends[(cid,x['id'],'delivered')]for x in qq]
    assert all(not x['error']for x in rr)
    receipts.append({'commands':len(qq),'frames':sum(x['frames']for x in rr),'result_sets':sum(x['resultsets']for x in rr),'sequence':[x['sql']for x in qq]})
   assert len(receipts)==3
   result['protocol'][v+'-'+phase]=receipts
for v in ['full','pruned','idiomatic']:
 p=(R/'mysql-idiomatic-results/pfs.jsonl') if v=='idiomatic' else B/'integration/census'/('small-'+v+'-utf8')/'pfs.jsonl';a=lines(p);calls=[x for x in a if x['name']=='statement/sql/call_procedure'];call=calls[-1];child=[x for x in a if x['thread']==call['thread']and x['nest']==call['event']];roles=collections.Counter()
 for x in child:
  s=(x['sql']or'').lower();n=x['name']
  if 'cursor_open' in n or n.endswith('/copen'):role='cursor_materialization'
  elif s.startswith(('select n.id','select e.id','select a.id','select cast')):role='direct_table_select'
  elif s.startswith(('select cursor_cnt','select query_id')):role='result_metadata_select'
  elif s:role='other_sql'
  else:role='control_or_variable_event'
  roles[role]+=1
 result['inside_call'][v]={'pfs_path':str(p.relative_to(B)),'call_event':call['event'],'roles':dict(roles),'direct_children':child,'definition':'Direct CALL children; cursor materialization executes an original table SELECT. Nested descendants are excluded to avoid duplicate accounting.'}
case_names={'full':'small-full-webridge-20261020','pruned':'small-pruned-webridge-20261020','idiomatic':'idiomatic-small-20261020'}
for v,n in case_names.items():
 c=B/'integration/cases'/n;api=read(c/'metadata.json')['api'];files=sorted((c/'generated/sql'/api).glob('graph-SP-*_sp_*.sql'));result['inside_call'][v]['generated_body_sha256']={str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files}
result['jac_operation_map']=read(B/'jac-comparison/roundtrip-profile/results/operation-map.json')
# Resolve executed cursor materializations against declared cursor SQL and checked execution order.
import re
for v,n in case_names.items():
 c=B/'integration/cases'/n;api=read(c/'metadata.json')['api'];f=next((c/'generated/sql'/api).glob('graph-SP-*_sp_*.sql'));source=f.read_text()
 literals=dict(re.findall(r"SET (q\d+_i\d+) = '([^']*)';",source));declarations=re.findall(r'DECLARE (cursor_\d+) CURSOR FOR (.*?);',source)
 direct=result['inside_call'][v]['direct_children'];opens=[x for x in direct if x['name'].endswith('/copen')];assert len(opens)==len(declarations)
 def cat(sql):
  if sql.lower().startswith('select a.id'):return 'hydration'
  if 'COUNT(DISTINCT CASE' in sql:return 'set-oriented.aggregate'
  vals=set(re.findall(r"'([^']*)'",sql))|{literals[x]for x in re.findall(r'q\d+_i\d+',sql)if x in literals}
  names=vals & {'Knows','HasMember','ContainerOf','HasCreator'};assert len(names)==1,(v,sql,names);return next(iter(names))
 executed=[]
 for x in direct:
  if x['sql'] and x['sql'].lower().startswith(('select n.id','select e.id','select a.id','select cast')):executed.append({'event':x['event'],'category':cat(x['sql']),'kind':'direct','sql':x['sql']})
 for x,(name,sql) in zip(opens,declarations):
  metadata=next(z for z in direct if z['event']>x['event'] and (z['sql']or'').startswith('SELECT cursor_cnt'))
  assert metadata['sql'].startswith('SELECT cursor_cnt_'+name.split('_')[1]+','),(v,name,metadata)
  executed.append({'event':x['event'],'category':cat(sql),'kind':'cursor','cursor':name,'sql':sql})
 counts=dict(collections.Counter(x['category']for x in executed));expected={'Knows':2,'HasMember':10,'ContainerOf':1,'HasCreator':15}
 if v=='full':expected['hydration']=7
 if v=='idiomatic':expected={'set-oriented.aggregate':1}
 assert counts==expected,(v,counts)
 result['inside_call'][v]['executed_business_categories']=counts;result['inside_call'][v]['executed_business_events']=executed
result['jac_operation_map']=read(B/'jac-comparison/roundtrip-profile/results/operation-map.json')
(R/'webridge-operation-map.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({v:z['executed_business_categories']for v,z in result['inside_call'].items()},indent=2))
