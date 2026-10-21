"""Recompute PostgreSQL server phase times from retained littleX request logs."""
import argparse,collections,gzip,hashlib,json,pathlib,re,statistics,sys
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from littlex_sql import category
P=re.compile(r'\[(\d+)\] LOG:  duration: ([\d.]+) ms\s+(parse ([^:]+)|bind ([^:]+)|execute ([^:]+)|statement):\s*(.*)',re.S)
def sid(s):return hashlib.sha256(' '.join(s.split()).encode()).hexdigest()[:16]
def bucket(c):
 if c.startswith('transaction.'):return'transaction'
 if c.startswith('identity.'):return'identity'
 if c.startswith('write.'):return'write'
 return'read'
def parse(text):
 out=[]
 for entry in re.split(r'(?=^\d{4}-\d\d-\d\d )',text,flags=re.M):
  m=P.search(entry)
  if not m:continue
  phase=m[3].split()[0];sql=m[7].strip()
  out.append({'pid':int(m[1]),'ms':float(m[2]),'phase':phase,'prepared_statement':m[4]or m[5]or m[6],'sql_id':sid(sql),'category':category(sql)})
 return out
def analyze(root):
 requests=[];inputs=[]
 for selection in ['littlex-profiles-t20','littlex-profiles-remaining-tiers','littlex-profiles-mixes']:
  home=root/selection;cert=json.loads((home/'certified-requests.json').read_text());catalog=json.loads((home/'sql-catalog.json').read_text())
  for row in cert:
   assert row['delay_ms']==2 and row['all_PID_SQL_sequence_and_complete_response_boundaries_verified']
   folder=home/'delay-2ms'/row['variant']/row['tier']/row['label'];path=folder/('profile-'+str(row['iteration'])+'.sql.log.gz')
   raw=path.read_bytes();text=gzip.decompress(raw).decode();events=parse(text);expected=row['operations'];own={x['pid']for x in expected}
   relevant=[e for e in events if e['pid']in own]
   executed=[e for e in relevant if e['phase']in('execute','statement')]
   assert [(e['pid'],e['sql_id'])for e in executed]==[(e['pid'],e['sql_id'])for e in expected],(path,'execute mismatch')
   assert [e['ms']for e in executed]==[e['execute_ms']for e in expected],(path,'duration mismatch')
   # The previously audited all-connection scope must remain complete.
   assert len(executed)==row['actual_SQL_commands']
   counts=collections.Counter(e['phase']for e in relevant)
   for phase,wire in [('parse','P'),('bind','B'),('execute','E'),('statement','Q')]:assert counts[phase]==row['frontend_messages'].get(wire,0),(path,phase,'phase versus protocol message mismatch')
   assert not[e for e in events if e['pid']not in own],(path,'uncertified duration PID')
   assert all(e['sql_id']in catalog and e['category']!='unclassified'for e in relevant),path
   # Each phase is independently logged; parse/bind/execute durations are disjoint.
   pending=collections.defaultdict(list);matched=[]
   for e in relevant:
    key=e['pid'],e['sql_id']
    if e['phase']in('parse','bind'):pending[key].append(e)
    else:
     phases=pending.pop(key,[])+[e]
     assert len([x for x in phases if x['phase']=='bind'])<=1,(path,'duplicate bind')
     assert len([x for x in phases if x['phase']=='parse'])<=1,(path,'duplicate parse')
     matched.append({'sql_id':e['sql_id'],'pid':e['pid'],'category':e['category'],'phase_ms':{x['phase']:x['ms']for x in phases},'server_ms':sum(x['ms']for x in phases)})
   remaining=[e for es in pending.values()for e in es]
   # Parse-only wire flights legitimately contribute preparation work without execution.
   assert all(e['phase']=='parse'for e in remaining),(path,'unmatched bind')
   for e in remaining:matched.append({'sql_id':e['sql_id'],'pid':e['pid'],'category':e['category'],'phase_ms':{'parse':e['ms']},'server_ms':e['ms'],'parse_only':True})
   phase=collections.defaultdict(float);phase_n=collections.Counter();buckets=collections.defaultdict(float);category_ms=collections.defaultdict(float)
   for e in relevant:phase[e['phase']]+=e['ms'];phase_n[e['phase']]+=1;buckets[bucket(e['category'])]+=e['ms'];category_ms[e['category']]+=e['ms']
   item={k:row[k]for k in ['request_tag','variant','tier','label','delay_ms','iteration']}
   item.update(logical_operation=row.get('logical_operation'),sql_count=len(executed),server_phase_sum_ms=sum(e['ms']for e in relevant),phase_ms=dict(phase),phase_counts=dict(phase_n),bucket_ms={b:buckets[b]for b in ['transaction','read','write','identity']},category_ms=dict(category_ms),commands=matched,source_log=str(path.relative_to(root)),source_compressed_sha256=hashlib.sha256(raw).hexdigest(),all_PID_SQL_order_and_execute_duration_verified=True)
   requests.append(item);inputs.append({'path':item['source_log'],'sha256':item['source_compressed_sha256']})
 groups=collections.defaultdict(list)
 for r in requests:groups[r['tier'],r['label'],r['variant']].append(r)
 summary=[]
 for (tier,label,variant),rs in sorted(groups.items()):
  expected_n=100 if label.startswith('W3-')else 3;assert len(rs)==expected_n
  summary.append({'case_id':('littlex-mixed-t200-w'+label[3:]if label.startswith('W3-')else'littlex-'+{'W1-feed':'feed','W2-like':'like','W2-follow':'follow','W2-create_tweet':'create_tweet'}[label]+'-'+tier),'tier':tier,'workload':label,'arm':'jac_original'if variant=='baseline'else'jac_final','delay_ms':2,'n':len(rs),'median_db_server_ms':statistics.median(r['server_phase_sum_ms']for r in rs),'sql_count_distribution':dict(sorted(collections.Counter(str(r['sql_count'])for r in rs).items())),'median_phase_ms':{p:statistics.median(r['phase_ms'].get(p,0)for r in rs)for p in ['parse','bind','execute','statement']},'median_bucket_ms':{b:statistics.median(r['bucket_ms'][b]for r in rs)for b in ['transaction','read','write','identity']},'phase_event_counts':dict(sum((collections.Counter(r['phase_counts'])for r in rs),collections.Counter()))})
 assert len(summary)==40 and len(requests)==896,(len(summary),len(requests))
 return {'scope':'PostgreSQL logged server parse+bind+execute/simple-statement phase durations. Instrumented2ms profiles;40 native arms. No application, HTTP or proxy timing. Phase durations are summed per request across all certified database PIDs.','request_n':len(requests),'arms':summary},requests,inputs
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,default=R);p.add_argument('--out',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent);p.add_argument('--check',action='store_true');a=p.parse_args();a.out.mkdir(exist_ok=True,parents=True)
 summary,requests,inputs=analyze(a.root)
 for name,data in [('summary.json',summary),('requests.json',requests),('inputs.json',inputs)]:
  if a.check:assert json.loads((a.out/name).read_text())==data,(name,'saved output mismatch')
  else:(a.out/name).write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps({'arms':len(summary['arms']),'requests':len(requests),'phase_counts':dict(sum((collections.Counter(r['phase_counts'])for r in requests),collections.Counter()))}))
