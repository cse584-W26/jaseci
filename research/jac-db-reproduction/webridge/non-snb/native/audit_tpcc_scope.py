"""Audit all logged backend PIDs against every tagged native TPC-C protocol request."""
import pathlib,json,gzip,re,collections
from tpcc_sql import sql_records,category
R=pathlib.Path(__file__).resolve().parent
sources=['tpcc-profiles-0-baseline','tpcc-profiles-0-final-resumed','tpcc-profiles-2-baseline','tpcc-profiles-2-final'];observations=[]
for source in sources:
    cert=json.loads((R/source/'certified-requests.json').read_text())
    for cell in json.loads((R/source/'summary.json').read_text()):
        folder=R/cell['path']
        for row in map(json.loads,(folder/'rows.jsonl').read_text().splitlines()):
            if row['warmup']:continue
            p=folder/(str(row['iteration']-10)+'.sql.log.gz');text=gzip.open(p,'rt').read();allpids={int(s)for s in re.findall(r'\[(\d+)\] LOG:  duration:',text)};allrows=sql_records(text,allpids);c=next(x for x in cert if x['request_tag']==row['request_tag']);traced={x['pid']for x in c['operations']};outside=[x for x in allrows if x['pid']not in traced];assert not outside,(p,outside);assert len(allrows)==c['actual_SQL_commands']
            observations.append({'artifact':str(p.relative_to(R)),'request_tag':row['request_tag'],'variant':c['variant'],'label':c['label'],'delay_ms':c['delay_ms'],'all_executed_SQL':len(allrows),'actual_complete_response_flights':c['actual_complete_response_flights'],'per_backend_PID_counts':dict(collections.Counter(x['pid']for x in allrows)),'identity_SQL':sum(category(x['sql'])=='identity.lookup'for x in allrows),'untraced_logged_SQL':len(outside)})
result={'PASS':True,'profile_arms':28,'measured_requests':len(observations),'scope':'Tags begin before HTTP POST and end after HTTP response plus diagnostic log flush. Every executed SQL record in each raw window is checked across all backend PIDs; no graph-PID-only filter. Prepared-only exchanges remain separate flights. Auth/context behavior reflects these actual post-ten-warm source requests; this is not a claim about cold authentication or unrelated future inputs.','observations':observations};assert len(observations)==84;(R/'tpcc-all-connection-scope-verification.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS84 requests/all logged backend PIDs')
