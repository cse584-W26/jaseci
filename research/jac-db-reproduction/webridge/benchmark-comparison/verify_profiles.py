"""Independent streaming audit of all33 completed Java protocol arms."""
import pathlib,json,gzip,collections,re,hashlib
R=pathlib.Path(__file__).resolve().parent;W=R.parent;P=R/'mysql-profile';historical=json.loads((R/'historical-hashes.json').read_text());summary=json.loads((P/'summary.json').read_text());assert len(summary['cells'])==33
read=lambda p:json.loads(p.read_text())
def rebase(path):return W/str(path).split('/webridge/',1)[1]if'/webridge/'in str(path)else pathlib.Path(path)
verified=[]
for directory in sorted({P/x['profile_path']for x in summary['cells']}):
 analysis=read(directory/'analysis.json');rows=[json.loads(s)for s in(directory/'run/requests/rows.jsonl').read_text().splitlines()];commands=[];ends={};wirebytes=collections.Counter();errors=[]
 with gzip.open(directory/'protocol.jsonl.gz','rt')as stream:
  for line in stream:
   e=json.loads(line)
   if e['event']=='command':commands.append(e)
   elif e['event']=='response_complete':ends[e['connection'],e['command_id'],e['stage']]=e
   elif e['event']=='server_frame'and e['stage']=='delivered':wirebytes[e['connection'],e['command_id']]+=e['payload_bytes']+4
   elif e['event']in ['overlapping_command','unexpected_column_terminator','unsupported_local_infile','connection_error']:errors.append(e)
 assert not errors
 for a,b in zip(commands,commands[1:]):assert b['at']>=ends[a['connection'],a['id'],'delivered']['at']
 bounds=[i for i,c in enumerate(commands)if c['sql'].startswith('SHOW SESSION STATUS')];assert len(bounds)==2*len(rows);byrequest={(x['phase'],x['iteration']):x for x in analysis['requests']};pfs=[json.loads(s)for s in(directory/'pfs.jsonl').read_text().splitlines()];pid=read(directory/'connection.json')['pfs_thread_id'];assert all(x['thread']==pid for x in pfs);byevent={x['event']:x for x in pfs};group=[]
 for i,row in enumerate(rows):
  q=analysis['case']['query'];actual=hashlib.sha256(json.dumps(row['result'],sort_keys=True).encode()).hexdigest();assert actual==historical[q+':0'];a=byrequest[row['phase'],row['iteration']];request=commands[bounds[2*i]+1:bounds[2*i+1]];assert len(request)==row['questions']==a['cycles'];assert [c['sql']for c in request]==[o['sql']for o in a['operations']]
  for c in request:
   rx=ends[c['connection'],c['id'],'received'];tx=ends[c['connection'],c['id'],'delivered'];assert not rx['error']and not tx['error'];assert(rx['frames'],rx['rows'],rx['resultsets'])==(tx['frames'],tx['rows'],tx['resultsets'])
  assert a['frames']==sum(ends[c['connection'],c['id'],'delivered']['frames']for c in request);assert a['result_sets']==sum(ends[c['connection'],c['id'],'delivered']['resultsets']for c in request);assert a['response_wire_bytes']==sum(wirebytes[c['connection'],c['id']]for c in request)
  if row['warmup']:continue
  tree=a['P_S_CALL'];proof=None
  if row['phase']=='sp':
   assert len(request)==4 and row['sp_enabled_at_end'];parent=byevent[tree['parent_event_id']];assert parent['name']=='statement/sql/call_procedure'and parent['error']==0;children=[e for e in pfs if e['nest']==parent['event']and parent['event']<e['event']<=parent['end_event']];assert{e['event']for e in children}=={e['event']for e in tree['direct_children']};real=sum(e['name']=='statement/sp/copen'or(e['name']=='statement/sp/stmt'and(e.get('sql')or'').lower().startswith('select')and re.search(r'\bfrom\b',e['sql'],re.I)is not None)for e in children);assert real==row['source_calls']-3==sum(v for k,v in tree['direct_child_counts'].items()if k.startswith('business.'))
   source=rebase(tree['generated_SP_source']);text=source.read_text();assert hashlib.sha256(source.read_bytes()).hexdigest()==tree['generated_SP_source_sha256'];declarations=dict(re.findall(r'DECLARE cursor_(\d+) CURSOR FOR (.*?);',text,re.S));opened={e['event']for e in children if e['name']=='statement/sp/copen'};assert opened=={x['open_event_id']for x in tree['cursor_associations']}
   for association in tree['cursor_associations']:
    number=association['cursor_number'];assert association['declared_SQL']==declarations[number];assert hashlib.sha256(declarations[number].encode()).hexdigest()==association['declared_SQL_sha256'];returned=byevent[association['return_event_id']];assert returned['sql'].startswith('SELECT cursor_cnt_'+number);assert not any(e['name']=='statement/sp/copen'and association['open_event_id']<e['event']<returned['event']for e in children)
   ids={e['event']for e in pfs if parent['event']<e['event']<=parent['end_event']};missing=set(range(parent['event']+1,parent['end_event']+1))-ids;assert len(missing)==len(tree['missing_event_ids']);observed=tree.get('control_events_instrumented',True)
   if observed:assert not missing
   active=directory/'SP-instruments-active.tsv'
   if active.exists():
    settings={line.split('\t')[0]:line.split('\t')[1:]for line in active.read_text().splitlines()};assert settings['statement/sp/stmt']==['YES','YES']and settings['statement/sp/copen']==['YES','YES']
    if not observed:assert all(v==['NO','NO']for k,v in settings.items()if k not in ['statement/sp/stmt','statement/sp/copen'])
   proof={'actual_business_statements_or_cursor_opens':real,'source_body_count_matches':True,'all_cursor_associations_verified':True,'control_events_instrumented':observed,'observed_event_id_gaps':len(missing),'parent_CALL_inclusive_ms':parent['timer_ps']/1e9}
  else:assert len(request)==row['source_calls']
  group.append({'query':q,'variant':analysis['case']['kind'],'phase':row['phase'],'iteration':row['iteration'],'cycles':len(request),'frames':a['frames'],'response_wire_bytes':a['response_wire_bytes'],'command_wire_bytes':a['command_wire_bytes'],'result_sets':a['result_sets'],'P_S_proof':proof})
 assert read(directory/'proxy-process.json')['stopped'];assert read(directory/'run/final-group-cleanup.json')['verified_empty'];restoration=directory/'SP-instruments-restored.json'
 if restoration.exists():assert read(restoration)['exact_prior_settings_restored']
 else:assert read(directory/'pfs-polls.json')['instrumentation_changes']is False
 verified.extend(group)
assert len(verified)==99
for cell in summary['cells']:
 rs=[x for x in verified if(x['query'],x['variant'],x['phase'])==(cell['query'],cell['variant'],cell['phase'])];assert len(rs)==3;assert[x['cycles']for x in rs]==cell['actual_cycles']
 for field,summary_field in [('frames','response_frames'),('response_wire_bytes','response_wire_bytes'),('command_wire_bytes','command_wire_bytes'),('result_sets','result_sets')]:assert[x[field]for x in rs]==cell[summary_field],(cell['query'],cell['variant'],cell['phase'],field)
 if cell['P_S_CALL']:assert[x['P_S_proof']['actual_business_statements_or_cursor_opens']for x in rs]==cell['P_S_CALL']['actual_business_statement_or_cursor_counts']
(R/'combined-protocol-33-arms-verified.json').write_text(json.dumps({'status':'PASS','measured_arms':33,'measured_requests':99,'all_actual_hashes_and_Questions_verified':True,'all_complete_response_cycles_frames_wirebytes_verified':True,'all_cursor_SQL_associations_verified':True,'business_counts_match_original_body':True,'scope':'Actual observed statement-event ranges and source body counts certify business work. Disabled control instrumentation remains explicitly unobserved.','requests':verified},indent=2));print('PASS33arms99requests')
