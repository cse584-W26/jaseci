#!/usr/bin/env python3
"""Read existing profiles: primary summed SQL RTT; secondary inclusive server duration."""
import argparse,collections,datetime,hashlib,importlib.util,json,pathlib,re,statistics,sys,time
D=pathlib.Path(__file__).resolve().parent;N=D.parents[1]
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x)for x in p.open()if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):(D/name).write_text(json.dumps(value,indent=2)+'\n')
def stats(v):return {'n':len(v),'median':statistics.median(v),'min':min(v),'max':max(v),'sum':sum(v)}if v else{'n':0,'median':None}
def norm(s):return' '.join((s or'').split()).lower()
def business(c):return c=='graph.anchor_query'or c.startswith('traversal.')or bool(re.match(r'relational\.lx_\w+\.select$',c))
def inventory():
 candidates=[]
 for p in sorted((N/'profiles').glob('littlex-batch-*/*/analysis.json')):
  match=re.fullmatch(r'(t\d+)-(feed_page|create_tweet|follow|mixed|feed|like)-(LittleXSql|LittleXFull|LittleXPruned)-(baseline|sp)(?:-w(\d+))?',p.parent.name)
  if not match:continue
  tier,op,cl,phase,mix=match.groups();m=read(p);v=p.parent/'business-verification.json';gate=read(v).get('status')if v.exists()else None
  case=f'littlex-mixed-{tier}-w{mix}'if op=='mixed'else f'littlex-{op}-{tier}';arm=('java_'if phase=='baseline'else'webridge_')+{'LittleXSql':'conventional','LittleXFull':'full','LittleXPruned':'pruned'}[cl]
  eligible=m['status']=='PASS'and gate=='PASS';reason=None
  if cl=='LittleXPruned'and op=='mixed'and p.parent.parent.name not in ['littlex-batch-1792555546513752376','littlex-batch-1792555553389885692']:eligible=False;reason='Superseded failed encoding/collation diagnostic; only final init+charset independently verified pair accepted'
  if not eligible and reason is None:reason='Protocol and independent business gate must both PASS'
  candidates.append({'case_id':case,'arm':arm,'profile':str(p.parent),'analysis_sha256':sha(p),'collection_status':m['status'],'business_gate':gate,'eligible':eligible,'exclusion':reason,'auxiliary':op=='feed_page','measured_n':sum(not r['warmup']for r in m['requests'])})
 selected={}
 for row in candidates:
  if row['eligible']:selected[row['case_id'],row['arm']]=row
 save('inventory.json',{'candidates':candidates,'selected':list(selected.values()),'policy':'Latest existing independently gated profile for the exact tier/operation/mix; no borrowing t20 profiles for other tiers; pruned mixed encoding failure excluded'})
def mysql():
 spec=importlib.util.spec_from_file_location('categories',N/'analyze_mysql_profile.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);output=[];raw=[]
 for item in read(D/'inventory.json')['selected']:
  root=pathlib.Path(item['profile']);analysis=read(root/'analysis.json');pfs=lines(root/'pfs.jsonl');outer=sorted((e for e in pfs if e.get('nest')is None and e.get('sql')),key=lambda e:e['event'])
  bounds=[e['event']for e in outer if norm(e['sql']).startswith('show session status')and norm(e['sql'])!="show session status like 'questions'"]
  assert len(bounds)==2*len(analysis['requests']),(root,len(bounds),len(analysis['requests']))
  rr=[]
  for index,r in enumerate(analysis['requests']):
   if r['warmup']:continue
   events=[e for e in outer if bounds[2*index]<e['event']<bounds[2*index+1]]
   assert len(events)==len(r['operations']),(root,index,len(events),len(r['operations']))
   truncated=[]
   for event,wire in zip(events,r['operations']):
    left,right=norm(event['sql']),norm(wire['sql'])
    if left!=right:
     maximum=left.endswith('...')and right.startswith(left[:-3])and len(event['sql'].encode('utf8'))>=1021
     unicode_boundary=right.startswith(left)and bool(right[len(left):].lstrip())and ord(right[len(left):].lstrip()[0])>0xffff and all(ord(c)<=0xffff for c in left)
     assert maximum or unicode_boundary,(root,index,event['event'],'P_S/wire SQL mismatch beyond proved SQL_TEXT prefix truncation')
     truncated.append({'event':event['event'],'pfs_text_bytes':len(event['sql'].encode('utf8')),'wire_text_bytes':len(wire['sql'].encode('utf8')),'association':'same ordered request event; P_S prefix matches full wire SQL','truncation_boundary':'maximum SQL_TEXT with ellipsis'if maximum else'observed SQL_TEXT ends immediately before first non-BMP Unicode character in full wire SQL'})
   category_ms=collections.defaultdict(float);selects=[];calls=[];nested_selects=[]
   for e in events:
    c=mod.category(e['sql']);ms=e['timer_ps']/1e9
    if e['name']=='statement/sql/call_procedure':calls.append(ms)
    else:
     category_ms[c]+=ms
     if business(c):selects.append(e)
   # Breakdowns use direct children; these are inside already-counted outer CALL time.
   for tree in r['CALLs']:
    assert not tree['missing_event_ids']
    for c,ms in tree['direct_child_timer_ms'].items():category_ms[c]+=ms
    cursors={c['open_event_id']:c['declared_SQL']for c in tree.get('cursor_associations',[])}
    for e in tree['direct_children']:
     sql=e.get('sql')or cursors.get(e['event']);c=mod.category(sql)if sql else''
     if business(c):selects.append(e);nested_selects.append(e)
   tx=sum(v for c,v in category_ms.items()if c.startswith('transaction.'))
   select_ms=sum(e['timer_ps']/1e9 for e in selects)
   row={'case_id':item['case_id'],'arm':item['arm'],'iteration':r['iteration'],'op':r['op'],'summed_db_call_rtt_ms':sum(o['command_to_complete_ms']for o in r['operations']),'db_call_count':len(r['operations']),'db_sum_ms':sum(e['timer_ps']/1e9 for e in events),'business_select_ms':select_ms,'transaction_control_ms':tx,'call_inclusive_ms':sum(calls),'call_nonselect_remainder_ms':sum(calls)-sum(e['timer_ps']/1e9 for e in nested_selects),'rows_examined_business_select':sum(e['rows_examined']for e in selects),'no_index_used_business_select_events':sum(bool(e['no_index'])for e in selects),'business_select_events':len(selects),'outer_foreground_events':len(events),'outer_event_ids':[e['event']for e in events],'sql_text_truncations':truncated,'category_ms':dict(category_ms),'profile':str(root)};rr.append(row);raw.append(row)
  output.append({'case_id':item['case_id'],'arm':item['arm'],'engine':'MySQL5.7','scope':'Existing rich-trace diagnostic. summed_db_call_rtt_ms sums outer command-to-complete-response delivery durations; db_sum_ms is secondary P_S outer foreground timer sum within exact request SHOWSTATUS boundaries. Observer status excluded; CALL counted once inclusive, child SQL only attribution.','profile':str(root),'source_files':{name:sha(root/name)for name in['analysis.json','pfs.jsonl','business-verification.json']},'metrics':{k:stats([r[k]for r in rr])for k in['summed_db_call_rtt_ms','db_call_count','db_sum_ms','business_select_ms','transaction_control_ms','call_inclusive_ms','call_nonselect_remainder_ms','rows_examined_business_select','no_index_used_business_select_events']},'op_counts':dict(collections.Counter(r['op']for r in rr))})
 save('mysql-request-rows.json',raw);save('mysql-summary.json',output)
def native():
 source=N/'native/db-time-analysis/requests.json';group=collections.defaultdict(list);raw=[];flights={}
 for folder in ['t20','remaining-tiers','mixes']:
  for r in read(N/('native/littlex-profiles-'+folder+'/certified-requests.json')):flights[r['request_tag']]=r
 for r in read(source):
  case='littlex-mixed-'+r['tier']+'-w'+r['label'].split('-')[1]if r['label'].startswith('W3-')else'littlex-'+(r['logical_operation']or r['label'].split('-',1)[1])+'-'+r['tier'];arm='jac_final'if r['variant']=='final'else'jac_original'
  row={'case_id':case,'arm':arm,'op':r['logical_operation']or r['label'].split('-',1)[1],'request_tag':r['request_tag'],'summed_db_call_rtt_ms':sum(f['instrumented_roundtrip_ms']for f in flights[r['request_tag']]['flights']),'db_call_count':len(flights[r['request_tag']]['flights']),'sql_count':flights[r['request_tag']]['actual_SQL_commands'],'prepare_only_flights':flights[r['request_tag']]['prepare_only_flights'],'db_sum_ms':r['server_phase_sum_ms'],'business_select_ms':sum(v for c,v in r['category_ms'].items()if c.startswith('traversal.')),'transaction_control_ms':r['bucket_ms'].get('transaction',0),'category_ms':r['category_ms'],'phase_ms':r['phase_ms'],'source_log':r['source_log']};group[case,arm].append(row);raw.append(row)
 output=[]
 for(case,arm),rr in group.items():output.append({'case_id':case,'arm':arm,'engine':'PostgreSQL18','scope':'Existing rich-trace diagnostic. summed_db_call_rtt_ms sums certified complete-response flights, including prepare-only flights. db_sum_ms is secondary owner-verified parse+bind+execute/simple server phases on every tagged backendPID including identity; server metric excludes proxy/client gaps.','profile':str(source.parent),'source_sha256':sha(source),'metrics':{k:stats([r[k]for r in rr])for k in['summed_db_call_rtt_ms','db_call_count','db_sum_ms','business_select_ms','transaction_control_ms']},'op_counts':dict(collections.Counter(r['op']for r in rr))})
 save('native-request-rows.json',raw);save('native-summary.json',output)
def join():
 measured=read(D/'mysql-summary.json')+read(D/'native-summary.json');by={(x['case_id'],x['arm']):x for x in measured};cases=[f'littlex-{op}-t{tier}'for tier in[20,50,100,200]for op in['feed','like','follow','create_tweet']]+[f'littlex-mixed-t200-w{w}'for w in[0,5,15,30]];arms=['jac_original','jac_final','java_full','webridge_full','java_pruned','webridge_pruned','java_conventional','webridge_conventional'];out=[]
 for c in cases:
  for a in arms:
   row=by.get((c,a));out.append({'case_id':c,'arm':a,'status':'actual_profile_available'if row else'no_eligible_exact_case_profile','actual_n':row['metrics']['db_sum_ms']['n'] if row else 0,'record':row})
 save('coverage-20cases-8arms.json',{'rows':out,'coverage':dict(collections.Counter(r['status']for r in out)),'auxiliary_profiles':[x for x in measured if x['case_id']not in cases],'native_source':'Native owner full-phase table: native/db-time-analysis; no duplicatePGrawlogscan here'})
 # Exact feed-page subset of the existing 15% mixed measured schedule.
 subsets=[]
 for source in['mysql-request-rows.json','native-request-rows.json']:
  rows=read(D/source)
  for arm in arms:
   rr=[r for r in rows if r['case_id']=='littlex-mixed-t200-w15'and r['arm']==arm and r['op']=='feed_page']
   if rr:subsets.append({'arm':arm,'scope':source,'metrics':{k:stats([r[k]for r in rr])for k in['summed_db_call_rtt_ms','db_call_count','db_sum_ms','business_select_ms','transaction_control_ms']},'additional_metrics':{k:stats([r[k]for r in rr])for k in['call_inclusive_ms','call_nonselect_remainder_ms','rows_examined_business_select']if k in rr[0]}})
 save('paged-feed-w15-subset.json',subsets)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('group',choices=['inventory','mysql','native','join']);a=p.parse_args();sys.path.insert(0,str(N));from measurement_lease import lease
 with lease('Read-only DB-side existing-profile analysis '+a.group,D/('lease-'+a.group+'-'+str(time.time_ns())+'.json')):globals()[a.group]()
 print(a.group,'complete')
