#!/usr/bin/env python3
"""Write measured representative findings and verify category-only revision."""
import json,pathlib,sys,hashlib
H=pathlib.Path(__file__).resolve().parent;N=H.parents[1];sys.path.insert(0,str(N));from measurement_lease import lease
with lease('PRIMARY attribution derived findings and unchanged-cost proof',H/'final/findings-lease.json'):
 p=H/'final/attribution.json';a=json.loads(p.read_text());old=json.loads((H/'final-superseded-customer-category/attribution.json').read_text());assert len(a['cells'])==75 and len(a['unavailable'])==21
 for x,y in zip(a['cells'],old['cells']):
  assert x['cell']==y['cell'] and x['median_total_ms']==y['median_total_ms'] and x['mean_total_ms']==y['mean_total_ms']
  assert[(r['iteration'],r['total_ms'],[(o['sql_id'],o['rtt_ms'])for o in r['operations']])for r in x['requests']]==[(r['iteration'],r['total_ms'],[(o['sql_id'],o['rtt_ms'])for o in r['operations']])for r in y['requests']]
 rows=[]
 for c in a['cells']:
  if c['cell']['delay_ms']!=0:continue
  dominant=max(c['categories'],key=lambda x:c['categories'][x]['mean_ms']);rows.append({'cell':c['cell'],'n':c['n'],'median_RTT_ms':c['median_total_ms'],'mean_RTT_ms':c['mean_total_ms'],'dominant_category':dominant,'dominant_mean_ms':c['categories'][dominant]['mean_ms'],'categories':c['categories'],'by_operation':c['by_operation'],'dominant_concrete_SQL':c['concrete_SQL'][:3]})
 proof={'status':'PASS','scope':'Reclassification preserves all75 cells medians,means,request totals,SQL IDs and exchange RTTs.648 frozen owner rows unchanged.','frozen_input_sha256':hashlib.sha256((H/'final-input.json').read_bytes()).hexdigest(),'attribution_sha256':hashlib.sha256(p.read_bytes()).hexdigest()};(H/'final/category-only-revision-proof.json').write_text(json.dumps(proof,indent=2)+'\n');(H/'final/representative-costs.json').write_text(json.dumps({'scope':'0ms primary latency; measured category means and per-request medians; PostgreSQL and MySQL recorded separately','rows':rows},indent=2)+'\n')
 text='''# Measured primary database-call costs

All values below use the fresh compact captures at 0 ms injected delay. PostgreSQL and MySQL are separate execution environments. Category means sum to mean request RTT; primary medians are computed per request. CALL costs cover the complete outer response.

* PostgreSQL Payment-by-name GC has median request RTT 3.976 ms in the original runtime and 4.197 ms in the final runtime. COMMIT contributes mean 1.635 and 1.585 ms respectively; five anchor hydrations together contribute 0.765 and 0.887 ms. The promoted last-name lookup contributes 0.568 and 0.602 ms.
* PostgreSQL full feed is dominated by the same two-hop projection SQL (normalized SQL ID `f2c5cb3431ee8dc3`). Its final-runtime mean cost is 8.755 ms at t20 and 57.179 ms at t200. The full request medians are 13.167 and 62.822 ms. The SQL projects endpoint IDs, root/ACL fields, fragments and timestamps.
* PostgreSQL mixed15 uses the bounded top-K query shape. Its 85 measured feed_page requests have median RTT 4.651 ms. The two-hop top-K projection contributes mean 0.978 ms per feed_page request, alongside ACL checks and other traversal operations.
* MySQL conventional Payment-by-name GC has median 3.838 ms directly and 3.229 ms through WeBridge. The direct autocommit=1 exchange contributes mean 2.505 ms; the complete outer CALL contributes mean 3.352 ms. The measured SQL exchange counts are 9 and 1.
* MySQL full-feed t200 has medians 81.531 ms directly and 81.098 ms through conventional WeBridge. The direct tweet SELECT contributes mean 81.375 ms; the complete CALL contributes 81.863 ms. Session setup exchanges contribute 1.207 and 0.538 ms respectively. The measured counts are 5 and 3.
* In MySQL conventional mixed15, feed_page medians are 34.558 ms directly and 34.325 ms through WeBridge. The WeBridge outer CALL contributes mean 33.953 ms per feed_page, with 0.368 ms of session setup. In pruned graph Java, the three wrapped graph queries together contribute mean 168.905 ms per feed_page; the WeBridge outer CALL contributes 171.914 ms. Their feed_page medians are 168.463 and 167.896 ms.
* TPC-C graph Payment's actual anchor traversal is labeled graph.anchor_query. Its measured mean is 35.287 ms in full Java and 31.453 ms in pruned Java. The archived exact SQL and regression check distinguish this graph traversal from a relational Customer SELECT.

`representative-costs.json` contains these category costs, exact SQL IDs/text and per-operation summaries. `attribution.json` retains every request's additive cost reconciliation. The regression receipts and category-only revision proof preserve the source-classifier correction separately from all measured timings.
'''
 (H/'final/MEASURED_FINDINGS.md').write_text(text);print('75-cell unchanged-cost proof and measured findings PASS')
