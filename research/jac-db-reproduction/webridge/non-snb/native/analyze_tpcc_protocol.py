"""Certify actual PG synchronization flights, including prepare-only exchanges."""
import pathlib,json,gzip,re,collections,hashlib,argparse
p=argparse.ArgumentParser();p.add_argument("--input",default="tpcc-profiles");args=p.parse_args()
R=pathlib.Path(__file__).resolve().parent;W=R.parents[1]
from tpcc_sql import sql_records as records,category as cat
result=[];catalog={}
def chunk(events,event,direction,stage,number):
 return next(x for x in events if x['event']==stage and x['direction']==direction and x['connection']==event['connection']and x['chunk']==number)
for directory in sorted((R/args.input).glob('delay-*ms')):
 delay=int(directory.name[6:-2]);path=directory/'trace/events.jsonl'
 with(path.open()if path.exists()else gzip.open(str(path)+'.gz','rt'))as stream:events=[json.loads(line)for line in stream]
 assert not[e for e in events if e['event']=='connection_error'];prepared={};bound={}
 for event in events:
  if event['event']!='frame'or event['direction']!='frontend':continue
  if event['type']=='P':prepared[event['connection'],event['statement']]=event['sql']
  if event['type']=='B':bound[event['connection'],event['mono_ns']]=prepared[event['connection'],event['statement']]
 for folder in sorted(directory.glob('*/*')):
  if not(folder/'rows.jsonl').exists():continue
  for row in map(json.loads,(folder/'rows.jsonl').read_text().splitlines()):
   if row['warmup']:continue
   es=[e for e in events if e['request_tag']==row['request_tag']];frames=[e for e in es if e['event']=='frame'];pids={e['backend_pid']for e in frames if e.get('backend_pid')}
   sql_events=records(gzip.open(folder/(str(row['iteration']-10)+'.sql.log.gz'),'rt').read(),pids);groups=[]
   for connection in {e['connection']for e in frames}:
    frontend=[e for e in frames if e['connection']==connection and e['direction']=='frontend'];pending=[];local=[]
    for frame in frontend:
     assert frame['type']in'PBDESQCH',frame['type'];pending.append(frame)
     if frame['type']in'SQH':local.append(pending);pending=[]
    assert not pending,'Unterminated frontend protocol group'
    backend=[e for e in frames if e['connection']==connection and e['direction']=='backend']
    for i,group in enumerate(local):
     upper=local[i+1][0]['mono_ns']if i+1<len(local)else float('inf');reply=[e for e in backend if group[0]['mono_ns']<=e['mono_ns']<upper];assert reply,'Pipelined or incomplete reply requires separate analysis'
     final=reply[-1]
     if group[-1]['type']in'SQ':assert final['type']=='Z'
     else:assert final['type']in'1TnC3EI',final['type']
     groups.append((group,reply,final))
   groups.sort(key=lambda x:x[0][0]['mono_ns']);commands=[];flights=[];last=None
   for group,reply,final in groups:
    first=group[0];sent=chunk(es,first,'frontend','chunk_received',first['start_chunk']);delivered=chunk(es,final,'backend','chunk_delivered',final['end_chunk']);assert last is None or sent['mono_ns']>=last,'Observed pipeline requires a dependency-aware flight analysis';last=delivered['mono_ns'];logical=[e for e in group if e['type']in'BQ'];assert len(logical)<=1
    flight={'frontend_types':''.join(e['type']for e in group),'backend_types':''.join(e['type']for e in reply),'frontend_received_ns':sent['mono_ns'],'reply_delivered_ns':last,'instrumented_roundtrip_ms':(last-sent['mono_ns'])/1e6,'connection':first['connection'],'pid':first['backend_pid'],'previous_complete_reply_before_next_frontend':True,'terminal_backend_type':final['type']}
    if logical:
     be=logical[0];sql=be['sql']if be['type']=='Q'else bound[be['connection'],be['mono_ns']];ex=sql_events[len(commands)];assert ' '.join(sql.split())==' '.join(ex['sql'].split());assert be['backend_pid']==ex['pid'];assert (be['statement']or'<unnamed>'if be['type']=='B'else None)==ex['statement'];sid=hashlib.sha256(' '.join(sql.split()).encode()).hexdigest()[:16];catalog[sid]=sql;operation={'sql_id':sid,'category':cat(sql),'pid':ex['pid'],'execute_ms':ex['execute_ms'],'flight_index':len(flights),'ready_transaction_status':final.get('transaction_status')};commands.append(operation);flight.update(kind='SQL_execution',sql_id=sid,category=operation['category'])
    else:
     parses=[e for e in group if e['type']=='P'];sql=parses[0]['sql']if parses else None;sid=hashlib.sha256(' '.join(sql.split()).encode()).hexdigest()[:16]if sql else None
     if sql:catalog[sid]=sql
     flight.update(kind='prepare_only'if parses else'protocol_control',sql_id=sid,category='driver.prepare'if parses else'driver.protocol_control')
    flights.append(flight)
   assert len(commands)==len(sql_events)
   result.append({'delay_ms':delay,'request_tag':row['request_tag'],'label':folder.name,'variant':folder.parent.name,'iteration':row['iteration'],'actual_SQL_commands':len(commands),'actual_complete_response_flights':len(flights),'prepare_only_flights':sum(x['kind']=='prepare_only'for x in flights),'frontend_messages':dict(collections.Counter(e['type']for e in frames if e['direction']=='frontend')),'backend_messages':dict(collections.Counter(e['type']for e in frames if e['direction']=='backend')),'frontend_frame_bytes':sum(e['bytes']for e in frames if e['direction']=='frontend'),'backend_frame_bytes':sum(e['bytes']for e in frames if e['direction']=='backend'),'frontend_chunks':sum(e['event']=='chunk_received'and e['direction']=='frontend'for e in es),'backend_chunks':sum(e['event']=='chunk_received'and e['direction']=='backend'for e in es),'operations':commands,'flights':flights,'all_PID_SQL_sequence_and_complete_response_boundaries_verified':True})
expected=sum(not row['warmup']for directory in (R/args.input).glob('delay-*ms')for folder in directory.glob('*/*')if(folder/'rows.jsonl').exists()for row in map(json.loads,(folder/'rows.jsonl').read_text().splitlines()))
assert len(result)==expected,(len(result),expected)
assert all(op['category']!='unclassified'for request in result for op in request['operations'])
(R/args.input/'certified-requests.json').write_text(json.dumps(result,indent=2));(R/args.input/'sql-catalog.json').write_text(json.dumps(catalog,indent=2));print('Certified',len(result),'measured actual requests')
