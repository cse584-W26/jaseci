"""Match actual PG executions to Bind/Ready cycles across request-owned connections."""
import pathlib,json,gzip,re,collections,hashlib,sys
R=pathlib.Path(__file__).resolve().parent
# Reuse the source census classifier and multiline server-log parser.
ns={'re':re};code=(R/'analyze_source.py').read_text();exec(code[code.index('def sql_records'):code.index('summary={}')],ns);cat=ns['cat'];records=ns['sql_records'];requests=[];sqls={}
for delay in [0,2]:
 for variant in ['baseline','final']:
  d=R/'profiles'/f'delay-{delay}ms'/variant;p=d/'trace/events.jsonl';text=p.read_text()if p.exists()and'--prefer-gz'not in sys.argv else gzip.open(str(p)+'.gz','rt').read();events=[json.loads(s)for s in text.splitlines()];assert not[x for x in events if x['event']=='connection_error'];parsed={(e['connection'],e['statement']):e['sql']for e in events if e['event']=='frame'and e['direction']=='frontend'and e['type']=='P'}
  for row in json.loads((d/'requests/rows.json').read_text()):
   if row['warmup']:continue
   es=[e for e in events if e['request_tag']==row['request_tag']];frames=[e for e in es if e['event']=='frame'];pids={e['backend_pid']for e in frames if e.get('backend_pid')};raw=gzip.open(d/'requests'/row['query']/f'profile-{row["iteration"]-10}.log.gz','rt').read();execs=records(raw,pids);pairs=[]
   for conn in {e['connection']for e in frames}:
    fs=[e for e in frames if e['connection']==conn and e['direction']=='frontend'];bs=[e for e in fs if e['type']in('B','Q')];zs=[e for e in frames if e['connection']==conn and e['direction']=='backend'and e['type']=='Z'];assert len(bs)==len(zs),(delay,variant,row['query'],len(bs),len(zs));assert not ''.join(e['type']for e in fs).replace('BDES','').replace('Q','')
    pairs+=list(zip(bs,zs))
   pairs.sort(key=lambda p:p[0]['mono_ns']);assert len(pairs)==len(execs);ops=[];last=None
   for i,((be,z),ex)in enumerate(zip(pairs,execs)):
    assert be.get('statement')==ex['statement'];assert be['backend_pid']==z['backend_pid']==ex['pid'];sql=be['sql']if be['type']=='Q'else parsed[(be['connection'],be['statement'])];assert ' '.join(sql.split())==' '.join(ex['sql'].split());sid=hashlib.sha256(' '.join(sql.split()).encode()).hexdigest()[:16];sqls[sid]=sql
    front=next(e for e in es if e['event']=='chunk_received'and e['direction']=='frontend'and e['connection']==be['connection']and e['chunk']==be['start_chunk']);end=next(e for e in es if e['event']=='chunk_delivered'and e['direction']=='backend'and e['connection']==z['connection']and e['chunk']==z['end_chunk']);proof=last is None or front['mono_ns']>=last;assert proof,(row['query'],i);last=end['mono_ns'];ops.append({'sequence':i+1,'category':cat(sql),'sql_id':sid,'pid':ex['pid'],'connection':be['connection'],'execute_ms':ex['execute_ms'],'previous_ready_before_next_frontend':proof,'ready_delivery_mono_ns':last,'frontend_received_mono_ns':front['mono_ns']})
   requests.append({'query':row['query'],'variant':variant,'delay_ms':delay,'request_tag':row['request_tag'],'sql_executions':len(ops),'synchronization_flights':len(ops),'serialized_ready_proof':True,'all_sql_matches_server_log':True,'frontend_messages':dict(collections.Counter(e['type']for e in frames if e['direction']=='frontend')),'backend_messages':dict(collections.Counter(e['type']for e in frames if e['direction']=='backend')),'frontend_chunks':sum(e['event']=='chunk_received'and e['direction']=='frontend'for e in es),'backend_chunks':sum(e['event']=='chunk_received'and e['direction']=='backend'for e in es),'categories':dict(collections.Counter(e['category']for e in ops)),'operations':ops})
(R/'profiles/certified-requests.json').write_text(json.dumps(requests,indent=2));(R/'profiles/sql-catalog.json').write_text(json.dumps(sqls,indent=2));print('Certified requests',len(requests))
