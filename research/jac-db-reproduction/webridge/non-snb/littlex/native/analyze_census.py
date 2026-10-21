#!/usr/bin/env python3
"""Preserve executed SQL and exact logged Bind parameters from dedicated littleX requests."""
import pathlib,json,re,gzip,hashlib,collections,argparse
H=pathlib.Path(__file__).resolve().parent;p=argparse.ArgumentParser();p.add_argument('directory',type=pathlib.Path);a=p.parse_args();out={}
def category(s):
 q=' '.join(s.lower().split())
 if q.startswith('begin'):return'transaction.begin'
 if q.startswith('set local'):return'transaction.setting'
 if q in ['commit','rollback']:return'transaction.'+q
 if q.startswith('select a.id, a.kind'):return'hydration.full_anchor'
 if q.startswith('select n1.id, e1.id'):return'traversal.generic'
 if q.startswith('insert into anchors'):return'write.anchor_insert'
 if q.startswith('update anchors'):return'write.anchor_update'
 if 'identity_users'in q or'identity_lookups'in q:return'identity.lookup'
 if 'graph_types'in q and'anchors'not in q:return'type_registry'
 if 'jsonb_agg'in q or'jsonb_build_object'in q:return'projection.feed'
 if 'kv_state'in q:return'cache.kv'
 if 'anchors'in q:return'graph.other'
 return'other'
for op in ['feed','feed_page','like','follow','create_tweet']:
 requests=[]
 for f in sorted((a.directory/op).glob('profile-*.log.gz')):
  raw=gzip.open(f,'rt').read();entries=re.split(r'(?=^\d{4}-\d\d-\d\d )',raw,flags=re.M);sql=[];pending=None
  for e in entries:
   m=re.search(r'\[(\d+)\] LOG:  duration: ([\d.]+) ms\s+(execute ([^:]+)|statement):\s*(.*)',e,re.S)
   if m:
    pending=len(sql);text=m[5].strip();sql.append({'pid':int(m[1]),'execute_ms':float(m[2]),'statement':m[4],'sql':text,'sql_sha256':hashlib.sha256(' '.join(text.split()).encode()).hexdigest(),'category':category(text)})
   if ' LOG:'in e and not m:pending=None
   d=re.search(r'\[(\d+)\] DETAIL:  Parameters: (.*)',e,re.S)
   if d and pending is not None and sql[pending]['pid']==int(d[1]):sql[pending]['parameters']=d[2].strip();pending=None
  requestpids={x['pid']for x in sql if x['category']=='transaction.begin'};assert len(requestpids)==1,(op,f,requestpids);sql=[x for x in sql if x['pid']in requestpids];requests.append({'log_path':str(f),'backend_pids':sorted(requestpids),'executed_commands':len(sql),'categories':dict(collections.Counter(x['category']for x in sql)),'operations':sql})
 out[op]={'counts':[r['executed_commands']for r in requests],'requests':requests}
(a.directory/'sql-census.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v['counts']for k,v in out.items()})
