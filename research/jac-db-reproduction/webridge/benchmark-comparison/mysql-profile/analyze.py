"""Actual wire cycles plus complete thread-scoped P_S CALL trees; controls are separate."""
import pathlib,json,gzip,collections,re,hashlib,argparse
R=pathlib.Path(__file__).resolve().parent;W=R.parents[1];historical=json.loads((R.parent/'historical-hashes.json').read_text())
def category(sql):
 s=' '.join((sql or'').lower().split())
 if s.startswith(('start transaction','begin')):return'transaction.begin'
 if s.startswith('set '):return'transaction.setting'
 if s.startswith('commit'):return'transaction.commit'
 if s.startswith('call '):return'stored_procedure.call'
 if 'information_schema'in s:return'driver.callable_metadata'
 if 'mysql.proc'in s or s.startswith(('show create procedure','select @@')):return'driver.callable_metadata'
 if s.startswith('select a.id, a.kind')or s.startswith('select a.id,a.kind'):return'hydration.full_anchor'
 if 'identity_users'in s or'identity_lookups'in s:return'identity.lookup'
 if 'graph_types'in s and 'anchors'not in s:return'type_registry'
 if 'to_regclass'in s:return'schema.guard'
 if 'select case'in s and'exists'in s:return'closure.bounded_case_exists'
 if 'select distinct dst'in s or'select distinct nb.dst'in s:return'closure.frontier_adjacency'
 if 'first_name'in s and'jac_snb_person'in s:return'person.filter_or_projection'
 if "'root'"in s and'access'in s:return'acl.root_permissions'
 if 'jac_snb_message'in s and'limit'in s:return'message.topk_join_roots_authors'if'ra.props'in s or'r.props'in s else'message.topk'
 for edge in ['Knows','IsLocatedIn','HasCreator','ReplyOf']:
  if edge.lower()in s:return'graph.'+edge
 if 'jac_snb_message'in s and'limit'in s:return'message.topk'
 if 'jac_snb_message'in s:return'message.projection'
 if 'jac_snb_person'in s:return'person.projection'
 if 'select' in s and 'anchors'in s:return'anchor.projection'
 if s.startswith('select')and'from'not in s:return'driver.scalar'
 return'other'
def pfs_category(e):
 name=e['name'];s=e.get('sql')or''
 if name=='statement/sp/copen':return'business.cursor_open'
 if name=='statement/sp/stmt':
  if s.lower().startswith('select')and re.search(r'\bfrom\b',s,re.I):return'business.'+category(s)
  if s.startswith('SELECT QUERY_ID'):return'return.replay_metadata'
  if s.lower().startswith('select'):return'return.materialized_rows'
  return'business.statement.'+s.split(' ',1)[0].lower()
 return'control.'+name.rsplit('/',1)[-1]
def analyze(d):
 case=json.loads((d/'case.json').read_text());casepath=pathlib.Path(case['case']);casepath=W/str(casepath).split('/webridge/',1)[1]if'/webridge/'in str(casepath)else casepath;sources=list(casepath.glob('generated/sql/*/graph-SP-*ver0.sql'));assert len(sources)==1 or case.get('phases')=='baseline',(casepath,sources);source=sources[0].read_text()if sources else'';declarations={m[0]:m[1]for m in re.findall(r'DECLARE cursor_(\d+) CURSOR FOR (.*?);',source,re.S)};constants=dict(re.findall(r'SET (q\d+_i\d+) = (\'[^\']*\');',source));p=d/'protocol.jsonl.gz';events=[json.loads(s)for s in gzip.open(p,'rt')];assert not[e for e in events if e['event']in ['overlapping_command','unexpected_column_terminator','unsupported_local_infile','connection_error']];commands=[e for e in events if e['event']=='command'];ends={(e['connection'],e['command_id'],e['stage']):e for e in events if e['event']=='response_complete'};assert len({c['connection']for c in commands})==1
 for c,nxt in zip(commands,commands[1:]):assert nxt['at']>=ends[c['connection'],c['id'],'delivered']['at']
 rows=[json.loads(s)for s in(d/'run/requests/rows.jsonl').read_text().splitlines()];bounds=[i for i,c in enumerate(commands)if c['sql'].startswith('SHOW SESSION STATUS')];assert len(bounds)==2*len(rows),(d,len(bounds),len(rows));pfs=[json.loads(s)for s in(d/'pfs.jsonl').read_text().splitlines()];assert all(e['thread']==json.loads((d/'connection.json').read_text())['pfs_thread_id']for e in pfs);calls=[e for e in pfs if e['name']=='statement/sql/call_procedure'];callidx=0;output=[]
 for i,row in enumerate(rows):
  assert hashlib.sha256(json.dumps(row['result'],sort_keys=True).encode()).hexdigest()==historical[case['query']+':0'];cc=commands[bounds[2*i]+1:bounds[2*i+1]];assert len(cc)==row['questions'];ops=[];tree=None
  for c in cc:
   rx=ends[c['connection'],c['id'],'received'];tx=ends[c['connection'],c['id'],'delivered'];assert not rx['error']and not tx['error'];assert(rx['frames'],rx['rows'],rx['resultsets'])==(tx['frames'],tx['rows'],tx['resultsets']);ops.append({'sql':c['sql'],'category':category(c['sql']),'command_id':c['id'],'command_at':c['at'],'response_delivered_at':tx['at'],'response_frames':tx['frames'],'response_wire_bytes':sum(e['payload_bytes']+4 for e in events if e['event']=='server_frame'and e['stage']=='delivered'and e['command_id']==c['id']and e['connection']==c['connection']),'command_wire_bytes':len(c['sql'].encode())+5,'result_sets':tx['resultsets'],'returned_rows':tx['rows'],'complete_received_ms':rx['elapsed_ms'],'complete_delivered_ms':tx['elapsed_ms']})
   if c['sql'].lower().startswith('call '):
    assert callidx<len(calls),(d,callidx,len(calls));parent=calls[callidx];callidx+=1;inside=[e for e in pfs if parent['event']<e['event']<=parent['end_event']];missing=sorted(set(range(parent['event']+1,parent['end_event']+1))-{e['event']for e in inside});direct=[e for e in inside if e['nest']==parent['event']];associations=[];overrides={}
    def actual_event_category(e):
     if e['name']=='statement/sp/stmt'and (e.get('sql')or'').lower().startswith('select')and re.search(r'\bfrom\b',e.get('sql')or'',re.I):return'business.'+category(re.sub(r'\bq\d+_i\d+\b',lambda m:constants.get(m[0],m[0]),e['sql']))
     return pfs_category(e)
    for k,e in enumerate(direct):
     if e['name']!='statement/sp/copen':continue
     following=next((v for v in direct[k+1:]if v['name']=='statement/sp/stmt'and re.match(r'SELECT cursor_cnt_\d+',v.get('sql')or'')),None);assert following
     next_open=next((v for v in direct[k+1:]if v['name']=='statement/sp/copen'),None);assert next_open is None or following['event']<next_open['event'],'Cursor association requires executed return before next open'
     number=re.match(r'SELECT cursor_cnt_(\d+)',following['sql'])[1];assert number in declarations;decl=declarations[number];resolved=re.sub(r'\bq\d+_i\d+\b',lambda m:constants.get(m[0],m[0]),decl);cat='business.cursor.'+category(resolved);overrides[e['event']]=cat;associations.append({'open_event_id':e['event'],'return_event_id':following['event'],'cursor_number':number,'association_proof':'Next executed materialized-result SELECT names cursor_cnt_N, matching generated DECLARE cursor_N CURSOR FOR SQL.','declared_SQL':decl,'declared_SQL_sha256':hashlib.sha256(decl.encode()).hexdigest(),'category':cat})
    counts=collections.Counter(overrides.get(e['event'],actual_event_category(e))for e in direct);timers=collections.defaultdict(float)
    for e in direct:timers[overrides.get(e['event'],actual_event_category(e))]+=e['timer_ps']/1e9
    tree={'parent_event_id':parent['event'],'parent_end_event_id':parent['end_event'],'parent_inclusive_ms':parent['timer_ps']/1e9,'captured_nested_events':len(inside),'missing_event_ids':missing,'complete_event_id_range':not missing,'direct_child_counts':dict(counts),'direct_child_timer_ms':dict(timers),'cursor_associations':associations,'generated_SP_source':str(sources[0]),'generated_SP_source_sha256':hashlib.sha256(source.encode()).hexdigest(),'direct_children':direct,'parent_error':parent['error'],'control_events_observed':case.get('control_event_counts_observed',True),'control_events_instrumented':case.get('control_event_counts_observed',True),'instrumentation_scope':case.get('P_S_mode','all_statement_events'),'instrumentation_settings_receipt':'SP-instruments-active.tsv','poll_capture_receipt':'pfs-polls.json','business_statement_or_cursor_count':sum(v for k,v in counts.items()if k.startswith('business.')),'source_business_statement_count':row['source_calls']-3,'business_count_matches_source':sum(v for k,v in counts.items()if k.startswith('business.'))==row['source_calls']-3}
  if row['phase']=='sp':assert tree and row['sp_enabled_at_end'];assert sum(o['category']=='stored_procedure.call'for o in ops)==1
  else:assert len(cc)==row['source_calls']
  output.append({'query':case['query'],'variant':case['kind'],'phase':row['phase'],'iteration':row['iteration'],'warmup':row['warmup'],'cycles':len(cc),'instrumented_request_ms':row['ms'],'sequential_complete_delivery_verified':True,'actual_output_hash_verified':True,'categories':dict(collections.Counter(o['category']for o in ops)),'frames':sum(o['response_frames']for o in ops),'response_wire_bytes':sum(o['response_wire_bytes']for o in ops),'command_wire_bytes':sum(o['command_wire_bytes']for o in ops),'result_sets':sum(o['result_sets']for o in ops),'operations':ops,'P_S_CALL':tree})
 assert callidx==len(calls)
 assert all(x['P_S_CALL']['complete_event_id_range']or not x['P_S_CALL']['control_events_observed']for x in output if x['phase']=='sp'and not x['warmup']), 'Measured full-control CALL P_S event range incomplete'
 assert all(x['P_S_CALL']['business_count_matches_source']for x in output if x['phase']=='sp'and not x['warmup']), 'Business statement/cursor execution count differs from source body'
 result={'path':str(d),'case':case,'status':'PASS','requests':output,'measured_requests':len([x for x in output if not x['warmup']]),'all_measured_CALL_event_ranges_complete':all(x['P_S_CALL']['complete_event_id_range']for x in output if x['phase']=='sp'and not x['warmup'])};(d/'analysis.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory',type=pathlib.Path);a=p.parse_args();x=analyze(a.directory.resolve());print(x['status'],x['measured_requests'],x['all_measured_CALL_event_ranges_complete'])
