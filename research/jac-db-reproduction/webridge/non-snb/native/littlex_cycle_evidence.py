"""Build explicit-selection actual littleX flight evidence, with condition/category detail."""
import pathlib,json,collections
R=pathlib.Path(__file__).resolve().parent;W=R.parents[1]
selection=R/'littlex-profile-selections.json'
if not selection.exists():selection.write_text(json.dumps(['littlex-pilot-like'],indent=2)+'\n')
result={}
for dirname in json.loads(selection.read_text()):
    path=R/dirname/'certified-requests.json';rows=json.loads(path.read_text());groups=collections.defaultdict(list)
    for x in rows:groups[(x['tier'],x['label'],x['variant'])].append(x)
    for (tier,label,variant),reqs in groups.items():
        workload,op=label.split('-',1);case='littlex-mixed-'+tier+'-w'+op if workload=='W3' else'littlex-'+op+'-'+tier
        arm='jac_original'if variant=='baseline'else'jac_final';observations=[]
        for x in reqs:
            assert x['all_PID_SQL_sequence_and_complete_response_boundaries_verified']
            observations.append({'request_tag':x['request_tag'],'logical_operation':x.get('logical_operation',op),'delay_ms':x['delay_ms'],'actual_SQL_commands':x['actual_SQL_commands'],'actual_complete_response_flights':x['actual_complete_response_flights'],'prepare_only_flights':x['prepare_only_flights'],'SQL_category_counts':dict(collections.Counter(q['category']for q in x['operations'])),'SQL_ID_sequence':[q['sql_id']for q in x['operations']],'per_backend_PID_counts':dict(collections.Counter(q['pid']for q in x['operations'])),'identity_SQL_commands':sum(q['category']=='identity.lookup'for q in x['operations']),'graph_store_SQL_commands':sum(q['category']!='identity.lookup'for q in x['operations']),'frontend_messages':x['frontend_messages'],'backend_messages':x['backend_messages']})
        entry=result.setdefault(case,{}).setdefault(arm,{'display':'','artifact':str(path.relative_to(W)),'observations':[],'scope':'Separately instrumented actual post-warm requests across all tagged database connections; identity and graph-store SQL are separated. SQL counts, complete-response flights, protocol messages and TCP chunks are distinct. Each case/condition is measured directly.'})
        entry['observations'].extend(observations)
        vals=sorted({q['actual_complete_response_flights']for q in entry['observations']});entry['display']=str(vals[0])if len(vals)==1 else str(vals[0])+'–'+str(vals[-1]);entry['measured_logical_operation_counts']=dict(collections.Counter(q['logical_operation']for q in entry['observations']))
(R/'littlex-cycle-evidence.json').write_text(json.dumps(result,indent=2)+'\n');print(len(result),'directly measured cases')
