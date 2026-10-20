import pathlib,json,struct,re,gzip,hashlib,collections
R=pathlib.Path(__file__).resolve().parent;OUT=R/'results';sqls={};requests=[]
def normalize(s):return' '.join(s.split())
def bindings(path):
 b=path.read_bytes();i=0;out=[]
 while i<len(b):
  kind=chr(b[i]);n=struct.unpack('!I',b[i+1:i+5])[0];p=b[i+5:i+1+n];i+=1+n
  if kind!='B':continue
  portal,name,rest=p.split(b'\0',2);nf=struct.unpack('!H',rest[:2])[0];fmts=list(struct.unpack('!'+str(nf)+'H',rest[2:2+2*nf]))if nf else[];rest=rest[2+2*nf:];np=struct.unpack('!H',rest[:2])[0];rest=rest[2:];params=[]
  for j in range(np):
   n=struct.unpack('!i',rest[:4])[0];rest=rest[4:];v=rest[:n]if n>=0 else None;rest=rest[n:]if n>=0 else rest;fmt=fmts[0]if len(fmts)==1 else fmts[j]if fmts else 0;params.append(None if v is None else v.decode('utf8')if fmt==0 else{'binary_hex':v.hex()})
  out.append({'statement':name.decode(),'portal':portal.decode(),'params':params})
 return out

def server_execs(raw):
 entries=re.split(r'(?=^\d{4}-\d\d-\d\d )',raw,flags=re.M);out=[]
 for text in entries:
  m=re.search(r'\[(\d+)\] LOG:  duration: ([\d.]+) ms\s+execute ([^:]+):\s*(.*)',text,re.S)
  if m:out.append({'pid':int(m[1]),'ms':float(m[2]),'statement':m[3],'sql':m[4].strip()})
 return out

def classify(sql,params,history):
 t=normalize(sql);values=[x for x in params if isinstance(x,str)]
 if t.startswith('BEGIN'):return'transaction.begin'
 if t.startswith('SET LOCAL'):return'transaction.setting'
 if t=='COMMIT':return'transaction.commit'
 if t.startswith('SELECT type_name FROM graph_types WHERE ancestor'):return'type_probe.'+values[0]
 if t.startswith('WITH pr(k, m)'):return'fused.forum_post_creator_count_order_limit'
 if 'SELECT u.nid, u.eid, u.oid'in t and "'HasMember'"in t:return'graph.HasMember.batch10'
 if 'SELECT a.id, a.kind'in t:
  if not any(x.startswith('hydrate.')for x in history):return'hydrate.root'
  if history[-1]=='hydrate.root':return'hydrate.input_person'
  for prior in reversed(history):
   if prior.startswith('graph.'):
    if 'Knows.out'in prior:return'hydrate.friends_out7'
    if 'Knows.in'in prior:return'hydrate.friends_in3'
    if 'HasMember'in prior:return'hydrate.forum1'
    if 'ContainerOf'in prior:return'hydrate.posts15'
    if 'HasCreator'in prior:return'hydrate.creator1'
  raise AssertionError(history)
 for edge in ['Knows','HasMember','ContainerOf','HasCreator']:
  if edge in values:
   if edge=='Knows':return'graph.Knows.'+('out'if re.search(r'e1\.(src|dst) = f0.id',t)[1]=='src'else'in')
   return'graph.'+edge
 raise AssertionError((t,values))

for delay in [0,2]:
 d=OUT/f'delay-{delay}ms';eventpath=d/'trace/events.jsonl';eventtext=eventpath.read_text()if eventpath.exists()else gzip.open(str(eventpath)+'.gz','rt').read();events=[json.loads(s)for s in eventtext.splitlines()];assert not[x for x in events if x['event']=='connection_error']
 parsed={}
 for e in events:
  if e['event']=='frame'and e['direction']=='frontend'and e['type']=='P':parsed[(e['connection'],e['statement'])]=e['sql']
 for variant in ['baseline','final']:
  rows=[x for x in json.loads((d/variant/'rows.json').read_text())if not x['warmup']];assert len(rows)==3
  for request in rows:
   tag=request['request_tag'];es=[x for x in events if x['request_tag']==tag];frames=[x for x in es if x['event']=='frame'];cs={x['connection']for x in frames};assert len(cs)==1;conn=next(iter(cs));f=[x for x in frames if x['direction']=='frontend'];b=[x for x in frames if x['direction']=='backend'];bs=[x for x in f if x['type']=='B'];zs=[x for x in b if x['type']=='Z'];assert len(bs)==len(zs)==request['execution_count'];assert ''.join(x['type']for x in f)=='BDES'*len(bs)
   bind=json.loads((OUT/'bind-metadata.json').read_text())[str(delay)+'|'+tag+'|'+str(conn)];assert len(bind)==len(bs)
   raw=gzip.open(d/variant/f'request{request["iteration"]}.log.gz','rt').read();execs=server_execs(raw);assert len(execs)==len(bs)
   delivered={x['chunk']:x for x in es if x['event']=='chunk_delivered'and x['direction']=='backend'};forwarded={x['chunk']:x for x in es if x['event']=='chunk_forwarded'and x['direction']=='frontend'};received={x['chunk']:x for x in es if x['event']=='chunk_received'and x['direction']=='frontend'};ops=[];history=[];last=None
   for i,(be,z,bi,ex)in enumerate(zip(bs,zs,bind,execs)):
    assert be['statement']==bi['statement']==ex['statement'];assert ex['pid']==be['backend_pid']==z['backend_pid'];sql=parsed[(conn,bi['statement'])];assert normalize(sql)==normalize(ex['sql']);sid='sql-'+hashlib.sha256(normalize(sql).encode()).hexdigest()[:12];sqls[sid]=sql;cat=classify(sql,bi['params'],history);history.append(cat);end=delivered[z['end_chunk']]['mono_ns'];start=forwarded[be['start_chunk']]['mono_ns'];assert end>=start
    previous_ready_before_next=last is None or received[be['start_chunk']]['mono_ns']>=last;assert previous_ready_before_next
    prev_frame_ns=zs[i-1]['mono_ns']if i else -1;reply=[x for x in b if prev_frame_ns<x['mono_ns']<=z['mono_ns']];cmd=[x['command_tag']for x in reply if x['type']=='C'];assert len(cmd)==1
    ops.append({'sequence':i+1,'category':cat,'sql_id':sid,'statement':bi['statement'],'parameters':bi['params'],'backend_pid':ex['pid'],'server_execute_ms':ex['ms'],'frontend_chunk':be['start_chunk'],'ready_backend_chunk':z['end_chunk'],'frontend_forwarded_mono_ns':start,'ready_delivered_mono_ns':end,'synchronization_span_ms':(end-start)/1e6,'previous_ready_before_next_frontend':previous_ready_before_next,'command_tag':cmd[0],'frontend_types':'BDES','backend_message_counts':dict(collections.Counter(x['type']for x in reply))});last=end
   counts=dict(collections.Counter(history));item={'delay_ms':delay,'variant':variant,'request_tag':tag,'start_wall_ns':request['start_wall_ns'],'start_mono_ns':request['start_mono_ns'],'response_mono_ns':request['response_mono_ns'],'server_ms':request['server_ms'],'client_ms':request['client_ms'],'backend_pid':ops[0]['backend_pid'],'connection':conn,'sql_executions':len(ops),'synchronization_flights':len(ops),'frontend_message_counts':dict(collections.Counter(x['type']for x in f)),'backend_message_counts':dict(collections.Counter(x['type']for x in b)),'frontend_chunks':sum(x['event']=='chunk_received'and x['direction']=='frontend'for x in es),'backend_chunks':sum(x['event']=='chunk_received'and x['direction']=='backend'for x in es),'categories':counts,'all_sql_matches_server_log':True,'serialized_ready_proof':True,'operations':ops};requests.append(item)
  assert len({json.dumps(x['categories'],sort_keys=True)for x in requests if x['variant']==variant})==1
# Sanitized bind metadata supports archived re-analysis without raw binary payloads.
private=OUT/'requests-detailed-derived.json';private.write_text(json.dumps(requests,indent=2))
(OUT/'sql-catalog.json').write_text(json.dumps(sqls,indent=2));public=[]
for x in requests:
 y={k:v for k,v in x.items()if k!='operations'};y['operations']=[{k:v for k,v in z.items()if k!='parameters'}for z in x['operations']];public.append(y)
(OUT/'flight-summary.json').write_text(json.dumps({'all_pass':True,'requests':public,'definition':'One frontend B-D-E-S command group followed by its backend ReadyForQuery, with the next Bind observed only after previous Ready delivery. Front/backend TCP read chunks counted separately. Parse/Flush absent after10warmups.'},indent=2))
compact={'all_pass':True,'profile_requests':len(requests),'variants':{}}
for v in ['baseline','final']:
 a=[x for x in requests if x['variant']==v];compact['variants'][v]={'sql_executions':a[0]['sql_executions'],'sync_flights':a[0]['synchronization_flights'],'frontend_messages':a[0]['frontend_message_counts'],'backend_chunks_each':[x['backend_chunks']for x in a],'categories':a[0]['categories'],'operations':[{k:z[k]for k in ['sequence','category','sql_id','frontend_types','command_tag']}for z in a[0]['operations']],'evidence_requests':[{'delay_ms':x['delay_ms'],'request_tag':x['request_tag'],'backend_pid':x['backend_pid'],'server_ms':x['server_ms']}for x in a]}
compact['source_anchors']=json.loads((R/'source-anchors.json').read_text());compact['grouped_change']=json.loads((R/'grouped-change.json').read_text());(OUT/'operation-map.json').write_text(json.dumps(compact,indent=2));print(json.dumps({v:{k:x[k]for k in['sql_executions','sync_flights','categories']}for v,x in compact['variants'].items()},indent=2))
