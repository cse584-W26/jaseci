"""Stable selection of certified native TPC-C protocol groups, preserving each repetition."""
import pathlib,json,collections,hashlib
R=pathlib.Path(__file__).resolve().parent;arms=[];seen=set()
for p in sorted(R.glob('tpcc-profiles-*/certified-requests.json')):
 rows=json.loads(p.read_text());groups=collections.defaultdict(list)
 for row in rows:groups[row['variant'],row['delay_ms'],row['label']].append(row)
 for (variant,delay,label),rep in sorted(groups.items()):
  key=variant,delay,label;assert key not in seen,key;seen.add(key)
  sql=collections.Counter(x['actual_SQL_commands']for x in rep);flights=collections.Counter(x['actual_complete_response_flights']for x in rep)
  arms.append({'variant':variant,'delay_ms':delay,'class':label,'n':len(rep),'actual_SQL_counts':dict(sql),'actual_complete_response_flight_counts':dict(flights),'actual_prepare_only_counts':[x['prepare_only_flights']for x in rep],'SQL_categories_per_request':[dict(collections.Counter(op['category']for op in x['operations']))for x in rep],'actual_frontend_message_counts':[x['frontend_messages']for x in rep],'actual_backend_message_counts':[x['backend_messages']for x in rep],'source':str(p.relative_to(R)),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'all_response_delivery_and_PID_SQL_order_verified':all(x['all_PID_SQL_sequence_and_complete_response_boundaries_verified']for x in rep)})
(R/'protocol-summary.json').write_text(json.dumps({'scope':'Separate instrumented TPC-C census,10warm+3measured per class/variant/delay','arms':arms,'expected_total_arms':28,'completed_arms':len(arms),'completed_measured_requests':sum(x['n']for x in arms)},indent=2)+'\n');print(len(arms),'arms')
