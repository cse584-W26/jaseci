"""Certify all-PID native littleX counts and retain early census counting scopes."""
import pathlib,json,gzip,re,collections
from tpcc_sql import sql_records
from littlex_sql import category
R=pathlib.Path(__file__).resolve().parent;L=R.parent/'littlex';out={'current':[],'early_feed':[]}
for source in json.loads((R/'littlex-profile-selections.json').read_text()):
    cert=json.loads((R/source/'certified-requests.json').read_text())
    for cell in json.loads((R/source/'summary.json').read_text()):
        folder=R/cell['path']
        for row in map(json.loads,gzip.open(folder/'rows.jsonl.gz','rt')):
            if row['warmup']:continue
            path=folder/('profile-'+str(row['iteration'])+'.sql.log.gz');text=gzip.open(path,'rt').read();pids={int(s)for s in re.findall(r'\[(\d+)\] LOG:  duration:',text)};allrows=sql_records(text,pids);c=next(x for x in cert if x['request_tag']==row['request_tag']);traced={q['pid']for q in c['operations']};assert not [q for q in allrows if q['pid']not in traced];assert len(allrows)==c['actual_SQL_commands']
            out['current'].append({'artifact':str(path.relative_to(R)),'tag':row['request_tag'],'all_DB_SQL':len(allrows),'per_PID_counts':dict(collections.Counter(q['pid']for q in allrows)),'identity_SQL':sum(category(q['sql'])=='identity.lookup'for q in allrows),'graph_store_SQL':sum(category(q['sql'])!='identity.lookup'for q in allrows),'untraced_logged_SQL':0})
for variant,dirname in [('baseline','20261020T232351Z-baseline'),('final','20261020T233449Z-final')]:
    legacy=json.loads((L/'native/census'/dirname/'sql-census.json').read_text())['feed']['requests']
    for iteration in range(3):
        graph_pids=set(legacy[iteration]['backend_pids'])
        path=L/'native/census'/dirname/'feed'/('profile-'+str(iteration)+'.log.gz');text=gzip.open(path,'rt').read();pids={int(s)for s in re.findall(r'\[(\d+)\] LOG:  duration:',text)};rows=sql_records(text,pids);identity=[q for q in rows if category(q['sql'])=='identity.lookup'];graph=[q for q in rows if q['pid']in graph_pids];other=[q for q in rows if q['pid']not in graph_pids and category(q['sql'])!='identity.lookup'];out['early_feed'].append({'artifact':str(path.relative_to(R.parent)),'variant':variant,'iteration':iteration,'all_raw_log_SQL':len(rows),'application_graph_plus_identity_SQL':len(graph)+len(identity),'other_raw_window_SQL_not_assigned_to_application':len(other),'identity_SQL':len(identity),'graph_store_SQL':len(graph),'graph_PIDs':sorted({q['pid']for q in graph}),'identity_PIDs':sorted({q['pid']for q in identity})})
out.update(PASS=True,scope='Current observations match all raw executed SQL across all backend PIDs against actual tagged protocol frames. Early graph-PID-only counts exclude the separate identity connection. Early measured actors/targets differ from the frozen ten-warm schedules; raw parameters and rows remain retained.',source_shared_root_resolver='ad469 runtimelib/impl/server.impl.jac1733–1739; query_planner.impl.jac21–38 and169')
(R/'littlex-all-connection-scope-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(len(out['current']),'current actual requests PASS; early',out['early_feed'])
