"""Compare compact pilot's actual SQL sequences against retained full protocol proof."""
import pathlib,json,hashlib
R=pathlib.Path(__file__).resolve().parent;old=json.loads((R/'littlex-profiles-t20/certified-requests.json').read_text());comparisons=[]
for variant in ['baseline','final']:
 p=R/'littlex-rtt-pilot/delay-0ms'/variant/'t20/W1-feed/rtt-requests.json';new=[r for r in json.loads(p.read_text())if not r['warmup']]
 original=[r for r in old if r['variant']==variant and r['label']=='W1-feed'];assert len(original)==3 and len(new)==30
 for a,b in zip(original,new):
  expected=[x['sql_id']for x in a['operations']];actual=[sid for f in b['calls']for sid in f['SQL_ids']];assert actual==expected,(variant,a['request_tag']);assert b['sql_command_count']==a['actual_SQL_commands'];assert b['response_exchange_count']==a['actual_complete_response_flights'];comparisons.append({'variant':variant,'full_protocol_request':a['request_tag'],'compact_request':b['request_tag'],'exact_SQL_order_and_count_equal':True,'SQL_count':len(actual),'complete_response_exchanges':b['response_exchange_count']})
(R/'compact-pilot-alignment.json').write_text(json.dumps({'PASS':True,'scope':'First three warmed inputs match the retained fully instrumented protocol SQL IDs/order/counts; all30new requests have independent complete-response metadata and source-state gates. Original comparison2ms versus compact0ms is a counting check, not a latency equivalence claim.','comparisons':comparisons},indent=2)+'\n');print('Compact pilot exact SQL sequence alignment PASS')
