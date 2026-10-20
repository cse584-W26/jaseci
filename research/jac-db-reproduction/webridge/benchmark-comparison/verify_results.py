"""Offline independent checks of frozen-oracle outputs and actual protocol flights."""
import collections,gzip,hashlib,json,math,pathlib,re,statistics,sys
R=pathlib.Path(__file__).resolve().parent;W=R.parent;N=W/'snb-extension/native';H=(R/'historical-hashes.json')if(R/'historical-hashes.json').exists()else W.parent/'results/baseline-other-parity/hashes.json';historical=json.loads(H.read_text());queries=['is1','is2','is3','ic1','ic2','ic13']
def read(p):return json.loads(p.read_text())
def canonical(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
def check_result(x,q,idx):
 expected=historical[f'{q}:{idx}'];assert canonical(x)==expected,(q,idx);return expected

def headers(row):
 h=row['headers'];total=float(h['x-server-total-ms']);commit=float(h.get('x-server-commit-ms',0));assert abs(row.get('server_ms',total+commit)-total-commit)<1e-8;assert total>=0 and commit>=0

def native():
 gates=[]
 for variant in ['baseline','final']:
  d=N/'gates'/f'{variant}-canonical';rows=[json.loads(s)for s in(d/'rows.jsonl').read_text().splitlines()];assert len(rows)==120;assert len({(x['query'],x['idx'])for x in rows})==120
  for x in rows:check_result(x['result'],x['query'],x['idx']);headers(x)
  assert read(d/'summary.json')['service_stopped'];gates.append({'variant':variant,'requests':len(rows),'actual_result_hashes_pass':True})
 timings=[];n=0
 for delay in [0,2,10]:
  for variant in ['baseline','final']:
   d=N/'latency'/f'delay-{delay}ms'/'timing'/variant;rows=read(d/'rows.json');assert len(rows)==240;assert read(d/'cleanup.json')['logging_restored']and read(d/'cleanup.json')['service_stopped']
   for q in queries:
    xs=[x for x in rows if x['query']==q];assert len(xs)==40;assert len([x for x in xs if x['warmup']])==10
    for x in xs:check_result(x['result'],q,0);headers(x);n+=1
    measured=[x for x in xs if not x['warmup']];timings.append({'query':q,'variant':variant,'delay_ms':delay,'n':30,'server_median_ms':statistics.median(x['server_ms']for x in measured),'client_median_ms':statistics.median(x['client_ms']for x in measured)})
  assert read(N/'latency'/f'delay-{delay}ms'/'proxy-exit.json')['stopped']
 assert n==1440
 reported=read(N/'latency/summary.json')
 for x in timings:
  z=next(z for z in reported if(z['query'],z['variant'],z['added_response_delay_ms'])==(x['query'],x['variant'],x['delay_ms']));assert abs(z['server_median_ms']-x['server_median_ms'])<1e-10
 certified=read(N/'profiles/certified-requests.json');actual=[];ordinary={};ttl=[]
 for delay in [0,2]:
  for variant in ['baseline','final']:
   d=N/'profiles'/f'delay-{delay}ms'/variant
   with gzip.open(d/'trace/events.jsonl.gz','rt')as f:events=[json.loads(s)for s in f]
   bytag=collections.defaultdict(list)
   parsed={}
   for e in events:
    bytag[e['request_tag']].append(e)
    if e['event']=='frame'and e['direction']=='frontend'and e['type']=='P':parsed[e['connection'],e['statement']]=e['sql']
   rows=[x for x in read(d/'requests/rows.json')if not x['warmup']];assert len(rows)==18
   for row in rows:
    q=row['query'];check_result(row['result'],q,0);headers(row);es=bytag[row['request_tag']];fs=[e for e in es if e['event']=='frame'];pids={e['backend_pid']for e in fs if e.get('backend_pid')};raw=gzip.open(d/'requests'/q/f'profile-{row["iteration"]-10}.log.gz','rt').read();sql=[]
    for entry in re.split(r'(?=^\d{4}-\d\d-\d\d )',raw,flags=re.M):
     m=re.search(r'\[(\d+)\] LOG:  duration: ([\d.]+) ms\s+(execute ([^:]+)|statement):\s*(.*)',entry,re.S)
     if m and int(m[1])in pids:sql.append({'pid':int(m[1]),'sql':' '.join(m[5].split()),'stmt':m[4]})
    pairs=[]
    for conn in {e['connection']for e in fs}:
     front=[e for e in fs if e['connection']==conn and e['direction']=='frontend'];commands=[e for e in front if e['type']in['B','Q']];ready=[e for e in fs if e['connection']==conn and e['direction']=='backend'and e['type']=='Z'];assert len(commands)==len(ready);assert not ''.join(e['type']for e in front).replace('BDES','').replace('Q','');pairs.extend(zip(commands,ready))
    pairs.sort(key=lambda p:p[0]['mono_ns']);assert len(pairs)==len(sql);last=None;seq=[];guard=0
    for(be,z),statement in zip(pairs,sql):
     emitted=be['sql']if be['type']=='Q'else parsed[be['connection'],be['statement']];assert ' '.join(emitted.split())==statement['sql'];assert be['backend_pid']==z['backend_pid']==statement['pid'];assert be.get('statement')==statement['stmt'];front=next(e for e in es if e['event']=='chunk_received'and e['direction']=='frontend'and e['connection']==be['connection']and e['chunk']==be['start_chunk']);ready=next(e for e in es if e['event']=='chunk_delivered'and e['direction']=='backend'and e['connection']==z['connection']and e['chunk']==z['end_chunk']);assert last is None or front['mono_ns']>=last;last=ready['mono_ns']
     if 'to_regclass(v.n)'in emitted:guard+=1
     else:seq.append(statement['sql'])
    ordinary.setdefault(q,set()).add(tuple(seq));receipt={'query':q,'variant':variant,'delay_ms':delay,'request_tag':row['request_tag'],'actual_sql':len(sql),'actual_flights':len(pairs),'schema_guard':guard,'actual_hash_pass':True};actual.append(receipt)
    c=next(x for x in certified if(x['query'],x['variant'],x['delay_ms'],x['request_tag'])==(q,variant,delay,row['request_tag']));assert c['sql_executions']==len(sql)==c['synchronization_flights'];assert c['categories'].get('schema.ttl_guard',0)==guard
    if guard:ttl.append(receipt)
   assert read(d/'cleanup.json')['proxy_stopped'];assert read(d/'requests/cleanup.json')['logging_restored']
 assert len(actual)==72 and all(len(v)==1 for v in ordinary.values())
 return {'status':'PASS','historical_oracle_file':str(H),'historical_oracle_sha256':hashlib.sha256(H.read_bytes()).hexdigest(),'gates':gates,'quiet_requests':n,'quiet_measured_requests':1080,'timing_cells':timings,'protocol_requests':actual,'protocol_total':72,'all_SQL_matches_actual_backend_logs':True,'all_next_command_after_prior_ready':True,'ordinary_SQL_identical_across_variants_and_conditions':{q:len(next(iter(v)))for q,v in ordinary.items()},'TTL_guard_observations':ttl,'cleanup_restoration_pass':True}
def java_gates():
 directory=W/'snb-extension/java/gates-20261020T215324439277Z';summary=read(directory/'summary.json');verified=[]
 for cell in summary:
  q=cell['query'];variant=cell['variant'];d=directory/q/variant;rows=[]
  for line in(d/'stdout.log').read_text().splitlines():
   try:x=json.loads(line)
   except json.JSONDecodeError:continue
   if 'result'in x:rows.append(x)
  assert len(rows)==20 and {x['idx']for x in rows}==set(range(20))
  for x in rows:
   check_result(x['result'],q,x['idx']);assert x['jdbc_calls']==x['server_questions']==sum(x['categories'].values())
  assert [x['jdbc_calls']for x in rows]==cell['counts']
  verified.append({'query':q,'variant':variant,'requests':20,'result_hashes_pass':True,'driver_and_server_counts_equal':True,'source_sha256_recorded':cell['source_sha256'],'counts':cell['counts']})
 assert len(verified)==12
 # Preserve real pipeline success/failure stages; later manifests can be added without assuming success.
 pipelines=[]
 for p in sorted((W/'snb-extension/java').glob('pipeline-*.json')):
  data=read(p)
  for c in data:
   stages=[]
   for x in c.get('stages',[]):stages.append({'stage':x['stage'],'returncode':x['returncode'],'path':x.get('path')})
   pipelines.append({'manifest':str(p),'query':c.get('query'),'variant':c.get('variant'),'attempt':c.get('attempt'),'stages':stages})
 return {'status':'PASS','gate_requests':240,'cells':verified,'pipeline_observations':pipelines,'native_full20_SQL_count_alignment_scope':'Native outputs verified for all20 inputs; native protocol SQLcount equality is directly measured for representative index0. Java driver/server counts independently agree for all20.'}

def conventional_gates():
 base=W/'expansion/set-sql';final=read(base/'final-gate-summary.json');d=pathlib.Path(final['gate_path']);d=(W/str(d).split('/webridge/',1)[1])if'/webridge/'in str(d)else d if d.is_absolute()else W.parents[1]/d
 manifest=read(d/'source-sha256.json');source=d/'SnbSetSql.java';sha=hashlib.sha256(source.read_bytes()).hexdigest();assert sha==manifest['source']==final['source_sha256'];cells=[]
 for q in queries:
  rows=[json.loads(x)for x in(d/q/'rows.jsonl').read_text().splitlines()];assert len(rows)==20 and{x['idx']for x in rows}==set(range(20))
  for x in rows:check_result(x['result'],q,x['idx']);assert x['source_calls']==len(x['sql'])
  command=read(d/(q+'-command.json'));cells.append({'query':q,'n':20,'all_actual_hashes_pass':True,'idx0_source_calls':rows[0]['source_calls'],'flags':[x for x in command if x.startswith('-Dsnb.')],'source_sha256_verified':sha})
 # Independently check the retained finite-depth IC13 alternative against the frozen oracles.
 alternative=base/'gates-20261020T215409Z';rows=[json.loads(x)for x in(alternative/'ic13/rows.jsonl').read_text().splitlines()];assert len(rows)==20
 for x in rows:
  check_result(x['result'],'ic13',x['idx']);query=next(y for y in x['sql']if y.startswith('SELECT CASE'));assert query.startswith('SELECT CASE WHEN ?=? THEN 0');assert sum(query.count('THEN '+str(depth))for depth in range(1,7))==6;assert query.endswith('ELSE -1 END')or query.endswith('ELSE -1 END AS length')
 return {'status':'PASS','gate_requests':120,'source_snapshot':str(source),'source_sha256':sha,'cells':cells,'IC13_alternative':{'actual_hashes_pass':20,'algorithm':'Ordered CASE equality then EXISTS walks of lengths1 through6 on the symmetric adjacency relation, returning first successful depth or-1.','observed_output_lengths':sorted({x['result']['length']for x in rows}),'bounded_source_cap':6,'source_comparison':'Native walker explicitly bounds Knows traversal at6; Java BFS also caps at6. Selected SQL preserves that finite cap.'}}

def selected_sources():
 base=W/'expansion/set-sql';checks=[];gates=[]
 frozen=base/'frozen-source-gates-20261020T221420Z'
 if frozen.exists():
  for q,entry in read(frozen/'summary.json').items():
   case=W/'integration/cases'/pathlib.Path(entry['case']).name;source=case/'source/SnbSetSql.java';clazz=case/'source/classes/SnbSetSql.class';assert hashlib.sha256(source.read_bytes()).hexdigest()==entry['source_sha256']==read(case/'metadata.json')['source_sha256'];assert hashlib.sha256(clazz.read_bytes()).hexdigest()==entry['class_sha256'];rows=[json.loads(line)for line in(frozen/q/'rows.jsonl').read_text().splitlines()];assert len(rows)==20
   for x in rows:check_result(x['result'],q,x['idx'])
   checks.append({'query':q,'frozen_source_sha256':entry['source_sha256'],'frozen_class_sha256':entry['class_sha256'],'metadata_source_sha_verified':True,'exact_frozen_source_gate':str(frozen),'actual_hashes_pass':20})
  assert len(checks)==6;return {'status':'PASS','gate_requests':120,'selected_cases':checks,'IS1_exact_source_gate_supersedes_prior_static_path_identity':True}
 for directory in base.glob('gates-*'):
  source=directory/'SnbSetSql.java'
  if source.exists():gates.append((directory,hashlib.sha256(source.read_bytes()).hexdigest()))
 for q in queries:
  case=W/'integration/cases'/('set-snb-'+q+('-nonnull'if q=='ic1'else'')+'-20261020');meta=read(case/'metadata.json');source=case/'source/SnbSetSql.java';sha=hashlib.sha256(source.read_bytes()).hexdigest();assert sha==meta['source_sha256'];matches=[d for d,h in gates if h==sha and(d/q/'rows.jsonl').exists()];receipt={'query':q,'case':str(case),'frozen_source_sha256':sha,'metadata_source_sha_verified':True}
  if matches:
   gate=sorted(matches)[-1];rows=[json.loads(s)for s in(gate/q/'rows.jsonl').read_text().splitlines()];assert len(rows)==20
   for x in rows:check_result(x['result'],q,x['idx'])
   receipt.update(exact_frozen_source_gate=str(gate),actual_hashes_pass=20)
  else:
   assert q=='is1';gate=base/'gates-20261020T215618Z';a=source.read_text();b=(gate/'SnbSetSql.java').read_text();prefix=lambda x:x[x.index('static JSONObject body'):x.index('if(query.equals("is3"))')];assert prefix(a)==prefix(b)
   names=['uuid','j','num','marks','columns','sql','command','personFields','request'];same=[]
   for name in names:
    la=next(x for x in a.splitlines()if re.search(r'\b'+name+r'\(',x)and('static 'in x));lb=next(x for x in b.splitlines()if re.search(r'\b'+name+r'\(',x)and('static 'in x));assert la==lb,name;same.append(name)
   receipt.update(full20_gate=str(gate),gate_source_sha256=hashlib.sha256(b.encode()).hexdigest(),IS1_executed_body_prefix_identical=True,executed_helpers_identical=same,selected_input_actual_profile_hashes_pass=3)
  checks.append(receipt)
 return {'status':'PASS','selected_cases':checks}

if __name__=='__main__'and'--timing-only'not in sys.argv:
 result=native();(R/'combined-native-verified.json').write_text(json.dumps(result,indent=2));print('Native PASS:240 gates,1440 quiet requests,72 raw protocol checks')
 if '--java'in sys.argv:
  result=java_gates();(R/'combined-java-gates-verified.json').write_text(json.dumps(result,indent=2));print('Java full/pruned PASS:240 historical result hashes and independent count agreement')

 if '--conventional'in sys.argv:
  result=conventional_gates();(R/'combined-conventional-verified.json').write_text(json.dumps(result,indent=2));print('Conventional PASS:120 actual hashes, immutable sourceSHA and IC13 bounded CASE20')

 if '--selected-sources'in sys.argv:
  result=selected_sources();(R/'combined-selected-sources-verified.json').write_text(json.dumps(result,indent=2));print('Selected frozen source gates and IS1 executed-path identity PASS')

# Standalone entry point for final quiet timing audit: import and call java_timing()
# after both coordinated windows finish; the function performs no live requests.
def rebase(path):
 text=str(path)
 if '/webridge/'in text:return W/text.split('/webridge/',1)[1]
 return pathlib.Path(text)if pathlib.Path(text).is_absolute()else W/text

def java_timing():
 instrumentation=W/'snb-extension/java/quiet-instrumentation';prior=read(instrumentation/'before.json');disabled=read(instrumentation/'after-disable.json');restored=read(instrumentation/'restored.json');assert restored['exact_full_snapshot_equal']and restored['state']==prior;assert disabled['consumers']==prior['consumers']and disabled['general_log']==prior['general_log'];assert prior['general_log'][0][0]=='0';before={r[0]:r[1:]for r in prior['instruments']};off={r[0]:r[1:]for r in disabled['instruments']};assert set(before)==set(off)
 for name,value in off.items():assert value==(['NO','NO']if name.startswith('statement/sp/')else before[name]),name
 output=[];seen=set();all_cids=set();isolation=[];summary_files=[W/'snb-extension/java/timing/summary.json',W/'expansion/set-sql/timing/summary.json']
 for summary_path in summary_files:
  summary=read(summary_path);expected_cells=72 if'snb-extension'in summary_path.parts else 36;assert len(summary)==expected_cells,(summary_path,len(summary));rowcache={}
  for cell in summary:
   q=cell['query'];variant=cell.get('variant','set');phase=cell['phase'];delay=cell['delay_ms'];key=(q,variant,phase,delay);assert key not in seen;seen.add(key)
   if cell['median_ms']is None:
    assert q=='ic1'and phase=='sp'and cell['n']==0 and cell['attempts']==3;paths=cell.get('attempt_paths')or cell['timeout_paths'];assert len(paths)==3;attempts=[]
    for path in paths:
     directory=rebase(path);directory=directory.parent if directory.name=='owned-watchdog-summary.json'else directory;watch=read(directory/'owned-watchdog-summary.json');assert watch['timed_out']and watch['limit_s']==15;t=watch['timeout_receipt'];cid=t['connection_id'];marker=t['request_marker'];actual=t['verified_process'];assert actual['id']==cid and actual['db']=='jac_snb_six_20261020';assert 'call 'in actual['info'].lower()and'7856cd3b-3a91-5cd0-8cda-63a0a04e4afb'in actual['info']and'Chau'in actual['info'];assert t['returncode']==0 and t['action']=='KILL CONNECTION '+str(cid);assert marker['phase']=='sp'and marker['watchdog_elapsed_s']>15;assert cid not in all_cids;all_cids.add(cid);identity=read(directory/'connection-id.json');recorded=identity if isinstance(identity,int)else next(identity[k]for k in ['connection_id','connectionId','mysql_connection_id','id']if k in identity);assert recorded==cid;assert read(directory/'final-group-cleanup.json')['verified_empty'];absence=directory/'server-absence-verification.json';cleanup=watch['final_database_cleanup'];assert cleanup.get('connection_id',cid)==cid
     if absence.exists():assert read(absence).get('connection_id',cid)==cid
     strict=directory/'strict-server-absence.json'
     if strict.exists():
      proof=read(strict);assert proof['connection_id']==cid and proof['absent_before_next_request'];observations=[o for o in proof['observations']if not o['processlist'].strip()];assert observations;absence_ns=observations[-1]['wall_ns'];proofpath=str(strict)
     else:
      assert absence.exists()and read(absence)['verified_absent'];provenance=read(R/'conventional-censor-time-provenance.json');proof=next(x for x in provenance['rows']if rebase(x['path'])==directory);assert hashlib.sha256(absence.read_bytes()).hexdigest()==proof['sha256'];absence_ns=proof['original_absence_receipt_mtime_ns'];proofpath=str(R/'conventional-censor-time-provenance.json')
     active=read(directory/'request-active.json');start_ns=int(active['start_wall_ms']*1e6);assert absence_ns>t['wall_ns'];isolation.append({'connection_id':cid,'request_start_wall_ns':start_ns,'absence_wall_ns':absence_ns,'absence_proof':proofpath,'path':str(directory)})
     attempts.append({'path':str(directory),'connection_id':cid,'database':actual['db'],'observed_request_s':marker['watchdog_elapsed_s'],'owned_KILL_verified':True,'server_absence_verified':True,'absence_proof':proofpath,'request_start_wall_ns':start_ns,'absence_wall_ns':absence_ns})
    output.append({'query':q,'variant':variant,'phase':phase,'delay_ms':delay,'status':'right-censored >15s','n':0,'median_ms':None,'actual_attempts':attempts,'measurement_scope':'Fresh connection first-SP request; completed warmup and post-warm median unavailable.'});continue
   rows_path=rebase(cell['rows_path']);rows=rowcache.setdefault(str(rows_path),[json.loads(line)for line in rows_path.read_text().splitlines()]);phase_rows=[x for x in rows if x['phase']==phase];assert len(phase_rows)==40;warm=[x for x in phase_rows if x['warmup']];measured=[x for x in phase_rows if not x['warmup']];assert len(warm)==10 and len(measured)==30;assert {x['iteration']for x in warm}==set(range(10))and{x['iteration']for x in measured}==set(range(10,40))
   for x in phase_rows:check_result(x['result'],q,0);assert x['oracle_ok']
   for x in measured:
    calls=x.get('call_procedure',x.get('status_delta',{}).get('Com_call_procedure'))
    if phase=='sp':assert calls==1 and x['sp_enabled_at_end']and x.get('sp_enabled_at_start',True)and x['questions']==4
    else:assert calls==0 and x['questions']==x['source_calls']
   median=statistics.median(x['ms']for x in measured);assert abs(median-cell['median_ms'])<1e-9;assert cell['n']==30;output.append({'query':q,'variant':variant,'phase':phase,'delay_ms':delay,'status':'measured','n':30,'warmup_n':10,'recomputed_median_ms':median,'actual_result_hashes_pass':40,'postwarm_Questions':sorted({x['questions']for x in measured}),'postwarm_CALLs':sorted({x.get('call_procedure',x.get('status_delta',{}).get('Com_call_procedure'))for x in measured}),'rows_path':str(rows_path)})
 isolation.sort(key=lambda x:x['request_start_wall_ns'])
 for previous,nxt in zip(isolation,isolation[1:]):assert previous['absence_wall_ns']<nxt['request_start_wall_ns'],(previous,nxt)
 retry=W/'snb-extension/java/quiet-instrumentation-retry';rb=read(retry/'before.json');rd=read(retry/'after-disable.json');rr=read(retry/'restored.json');assert rr['exact_full_snapshot_equal']and rr['state']==rb;assert rd['consumers']==rb['consumers']and rd['general_log']==rb['general_log'];assert all(row[1:]==['NO','NO']for row in rd['instruments']if row[0].startswith('statement/sp/'));preclear=read(W/'snb-extension/java/timing/censored-retries/old-owned-connections-preclear.json');assert preclear['all_absent']and not preclear['processlist'].strip();newtries=[x for x in isolation if'censored-retries'in x['path']];assert len(newtries)==18 and preclear['wall_ns']<min(x['request_start_wall_ns']for x in newtries)
 assert len(output)==108;assert sum(x['status']=='measured'for x in output)==99;assert sum(x['status'].startswith('right-censored')for x in output)==9;assert len(all_cids)==27
 # A successful actual CALL is usable even when an earlier post-emission synthesis
 # process returned nonzero. The observed phase flags and result hashes above decide.
 statuses=read(W/'snb-extension/java/case-status.json');full_ic2=next(x for x in statuses if x['query']=='ic2'and x['variant']=='full');assert any(x['query']=='ic2'and x['variant']=='full'and x['phase']=='sp'and x['status']=='measured'for x in output)
 return {'status':'PASS','java_matrix_cells':108,'measured_cells':99,'censored_cells':9,'censored_actual_attempts':27,'sequential_absence_before_next_primary_attempt_verified':True,'attempt_isolation':isolation,'retry_instrumentation_exact_restoration_verified':True,'old_attempts_preclear_verified':True,'actual_result_hashes_verified':3960,'P_S_OFF_prior_and_exact_restoration_verified':True,'cells':output,'IC2_full_generated_SP_usable':True,'IC2_full_pipeline_observations':full_ic2,'scope':'Native adds36 measured cells; total144 cells,135 post-warm medians and9 right-censored slow-SP cells.'}

if __name__=='__main__'and'--java-timing'in sys.argv:
 result=java_timing();(R/'combined-java-timing-verified.json').write_text(json.dumps(result,indent=2));print('Java quiet matrix PASS:99 measuredcells,9 censoredcells,27 ownedattempts')
