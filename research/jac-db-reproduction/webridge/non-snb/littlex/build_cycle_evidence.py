#!/usr/bin/env python3
"""Expose accepted actual wire/P_S observations using the shared report case/arm keys."""
import pathlib,json,argparse,hashlib,collections
H=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('analyses',nargs='*',type=pathlib.Path);p.add_argument('--analysis-list',type=pathlib.Path,default=H/'wire-analysis-inputs.json');p.add_argument('--normalized',type=pathlib.Path,help='Complete normalized 360-cell Java latency matrix');p.add_argument('--out',type=pathlib.Path,default=H/'cycle-evidence.json');a=p.parse_args();result={}
if a.analysis_list.exists():a.analyses.extend(pathlib.Path(x)for x in json.loads(a.analysis_list.read_text()))
a.analyses=list(dict.fromkeys(a.analyses))
if a.normalized:
 normalized=json.loads(a.normalized.read_text())
 grouped=collections.defaultdict(list)
 for row in normalized['cells']:
  if row['method']!='latency':continue
  case='littlex-mixed-t'+str(row['tweets_per_user'])+'-w'+str(row['write_percent'])if row['workload']=='mixed'else'littlex-'+row['workload']+'-t'+str(row['tweets_per_user'])
  grouped[(case,row['arm'])].append(row)
 assert len(grouped)==120,('Expected all 120 workload-arm entries',len(grouped))
 for (case,arm),rows in grouped.items():
  observations=[{'delay_ms':r['delay_ms'],'status':r['status'],'artifact':r['artifact'],'actual_questions_distribution':r.get('actual_questions_distribution'),'actual_CALL_count_distribution':r.get('actual_call_count_distribution'),'actual_call_fraction':r.get('actual_call_fraction'),'sdk_enabled_at_end_requests':r.get('sdk_enabled_at_end_requests'),'sdk_enabled_at_end_fraction':r.get('sdk_enabled_at_end_fraction'),'sdk_flag_scope':r.get('sdk_flag_scope'),'activation_by_operation':r.get('activation_by_operation'),'state_result_gate':r.get('state_result_gate'),'error':r.get('error'),'failed_stage':r.get('failed_stage'),'pipeline_evidence':r.get('pipeline_evidence'),'frontend_selection':r.get('frontend_selection')}for r in rows]
  values=[]
  for r in rows:
   distribution=r.get('actual_questions_distribution')or{}
   if isinstance(distribution,dict):values.extend(float(k)for k in distribution if str(k).replace('.','',1).isdigit())
   elif isinstance(distribution,list):values.extend(float(v)for v in distribution if isinstance(v,(int,float)))
  def number(v):return str(int(v))if v==int(v)else str(v)
  display=(number(min(values))if len(set(values))==1 else number(min(values))+'–'+number(max(values)))+' Questions/request'if values else next((r.get('failed_stage')or'runtime/oracle failure'for r in rows if r['status']!='accepted'),'count receipt pending')
  result.setdefault(case,{})[arm]={'display':display,'artifact':str(a.normalized),'scope':'All three RTT cells; MySQL session Questions observations are distinct from instrumented complete-response wire cycles','count_definition':'Questions are server session command counters; the representative_wire_profile field supplies independently observed complete-response cycles when available','observations':observations}
for path in a.analyses:
 root=path.parent
 if(root/'scope.json').exists()and json.loads((root/'scope.json').read_text()).get('accepted_for_primary_comparison')is False:continue
 analysis=json.loads(path.read_text());assert analysis['status']=='PASS';verified=json.loads((root/'business-verification.json').read_text());assert verified['status']=='PASS';cmd=json.loads((root/'request-command.json').read_text());i=cmd.index('LittleXTiming');planpath=pathlib.Path(cmd[i+1]);phase=cmd[i+3];factory=planpath.parent;provenance=json.loads((factory/'plan-provenance.json').read_text());config=json.loads((root/'config.json').read_text());tier=config['database'].split('_')[2];impl=next(x.split('=',1)[1]for x in cmd if x.startswith('-Dlittlex.implementation='));stem={'LittleXFull':'full','LittleXPruned':'pruned','LittleXSql':'conventional'}[impl];arm=('webridge_'if phase=='sp'else'java_')+stem;plan=json.loads(planpath.read_text());op=plan[0]['input']['op'];case='littlex-mixed-'+tier+'-w'+str(provenance['write_percent'])if provenance['workload']=='W3'else'littlex-'+op+'-'+tier
 measured=[r for r in analysis['requests']if not r['warmup']];assert measured
 if impl=='LittleXFull'and phase=='baseline'and op.startswith('feed')and provenance['workload']!='W3':assert all(r['wire_categories'].get('identity.lookup')==2 for r in measured),'Final full-read scope includes two real guest identity reads'
 cycles=[r['cycles']for r in measured];display=str(cycles[0])if len(set(cycles))==1 else str(min(cycles))+'–'+str(max(cycles));source=pathlib.Path(factory/'build.json');sample_scope='complete original 100-slot mix cycle after 110 warm-up requests'if len(measured)==100 else 'instrumented representative requests after '+str(provenance['warmup_count'])+' warm-up requests'
 wire_entry={'display':display,'artifact':str(path),'scope':sample_scope,'measured_requests':len(measured),'actual_complete_response_cycles':cycles,'actual_CALL_counts':[r['actual_CALL_count']for r in measured],'outside_business_command_counts':[r['business_commands_outside_CALL']for r in measured],'actual_wire_category_counts':[r['wire_categories']for r in measured],'execution_paths':[r['execution_path']for r in measured],'build_manifest':str(source),'build_manifest_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'independent_response_and_committed_state_gate':str(root/'business-verification.json'),'generated_sources':analysis.get('generated_sources'),'observations':[{'iteration':r['iteration'],'operations':r['operations'],'CALLs':r['CALLs'],'sp_enabled_at_end':r['sp_enabled_at_end']}for r in measured],'count_definition':'Actual frontend SQL commands matched to delivered complete responses; P_S stored-program events and generated cursor SQL mapped separately'}
 if arm in result.get(case,{}):
  result[case][arm]['representative_wire_profile']=wire_entry
  result[case][arm]['display']=display+' wire (representative)'
 else:result.setdefault(case,{})[arm]=wire_entry
a.out.write_text(json.dumps(result,indent=2)+'\n');print(a.out)
