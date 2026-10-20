"""Incremental public summary of measured wire cycles and actual P_S statement categories."""
import pathlib,json,collections,statistics,gzip,argparse
R=pathlib.Path(__file__).resolve().parent;parser=argparse.ArgumentParser();parser.add_argument('--refresh-selection',action='store_true');args=parser.parse_args();existing=json.loads((R/'summary.json').read_text())if(R/'summary.json').exists()else{};selection={(c['query'],c['variant'],c['phase']):R/c['profile_path']/'analysis.json'for c in existing.get('cells',[])};cells=[];failures=[];grouped=collections.defaultdict(list)
for p in(R/'results').glob('*/*/analysis.json'):
 x=json.loads(p.read_text())
 for row in x['requests']:
  if not row['warmup']:grouped[row['query'],row['variant'],row['phase']].append((p,row))
for(q,variant,phase),values in sorted(grouped.items()):
 # Latest successful complete three-request capture; previous attempts remain on disk.
 paths=sorted({p for p,r in values},key=lambda p:p.stat().st_mtime_ns);chosen=selection.get((q,variant,phase))if not args.refresh_selection else None;chosen=chosen if chosen in paths else paths[-1];rows=[r for p,r in values if p==chosen];assert len(rows)==3
 ps=[r['P_S_CALL']for r in rows if r['P_S_CALL']];names=sorted({k for p in ps for k in p['direct_child_counts']});cats={k:{'counts':[p['direct_child_counts'].get(k,0)for p in ps],'timer_ms':[p['direct_child_timer_ms'].get(k,0)for p in ps]}for k in names}
 cells.append({'query':q,'variant':variant,'phase':phase,'profile_path':str(chosen.parent.relative_to(R)),'measured_requests':3,'actual_cycles':[r['cycles']for r in rows],'response_frames':[r['frames']for r in rows],'response_wire_bytes':[r['response_wire_bytes']for r in rows],'command_wire_bytes':[r['command_wire_bytes']for r in rows],'result_sets':[r['result_sets']for r in rows],'instrumented_request_ms':[r['instrumented_request_ms']for r in rows],'wire_categories':rows[0]['categories'],'sequential_complete_delivery_verified':all(r['sequential_complete_delivery_verified']for r in rows),'actual_output_hash_verified':all(r['actual_output_hash_verified']for r in rows),'P_S_CALL':{'parent_inclusive_ms':[p['parent_inclusive_ms']for p in ps],'all_event_id_ranges_complete':all(p['complete_event_id_range']for p in ps),'control_events_observed':all(p.get('control_events_observed',True)for p in ps),'control_events_instrumented':all(p.get('control_events_instrumented',True)for p in ps),'instrumentation_scope':sorted({p.get('instrumentation_scope','all_statement_events')for p in ps}),'business_count_matches_source':all(p.get('business_count_matches_source',True)for p in ps),'nested_event_counts':[p['captured_nested_events']for p in ps],'direct_child_categories':cats,'actual_business_statement_or_cursor_counts':[sum(v for k,v in p['direct_child_counts'].items()if k.startswith('business.'))for p in ps]}if ps else None})
for p in(R/'results').glob('*/*/run/process-result.json'):
 x=json.loads(p.read_text())
 if x['returncode']!=0:failures.append({'path':str(p.relative_to(R)),'returncode':x['returncode'],'stop_reason':x.get('stop_reason')})
for p in(R/'results').glob('*/*/analysis.stderr'):
 if p.read_text().strip():failures.append({'path':str(p.relative_to(R)),'failure_stage':'protocol_or_P_S_analysis','details':p.read_text()[-700:]})
slow=[]
W=R.parents[1]
for p in[W/'snb-extension/java/timing/summary.json',W/'expansion/set-sql/timing/summary.json']:
 if not p.exists():continue
 for c in json.loads(p.read_text()):
  if c['query']=='ic1'and c['phase']=='sp'and c['median_ms']is None:slow.append({'query':'ic1','variant':'conventional'if c.get('variant')=='set'else c.get('variant'),'phase':'sp','delay_ms':c['delay_ms'],'status':c['status'],'attempts':c['attempts'],'attempt_paths':c.get('attempt_paths')or c.get('timeout_paths'),'measurement_scope':'First-SP request right-censored; post-warm completed protocol sample unavailable.','primary_source':str(p)})
(R/'summary.json').write_text(json.dumps({'status':'incremental','slow_runtime_censored_markers':slow,'expected_pairs':18,'measured_arms':len(cells),'cells':cells,'preserved_failed_attempts':failures,'P_S_timing_scope':'Parent CALL duration is inclusive. Direct-child business reads, cursor opens, result materialization and control events are reported separately.','profile_delay_ms':2},indent=2));print(len(cells),'measured arms')
