#!/usr/bin/env python3
"""Freeze original schedules/TargetPlan inputs; measured loop restarts i=0 after warmup."""
import pathlib,json,uuid,sys,datetime,collections,hashlib
H=pathlib.Path(__file__).resolve().parent;REPRO=H.parents[2];sys.path.insert(0,str(REPRO/'littlex/harness'));from write_run import TargetPlan
recipe=json.loads((H/'recipe.json').read_text());schedules=json.loads((H.parent/'littlex-schedules.json').read_text());out=H/'plans';out.mkdir(exist_ok=True);ledger=[]
for tier,t in recipe['tiers'].items():
 seed=json.loads(pathlib.Path(t['seed']).read_text());targets=json.loads((pathlib.Path(t['fixture_manifest']).parent/'tokens/targets.jaseci.json').read_text());users=sorted(targets['users']);roots={}
 for line in(H/'fixtures'/tier/'anchors.tsv').open():
  r=line.rstrip('\n').split('\t')
  if r[1]=='NodeAnchor'and r[2]=='Profile':roots[r[0]]=r[5]
 def uid(s):return str(uuid.UUID(s.zfill(32)))
 workloads=[('W1','feed')]+[('W2',op)for op in ['like','follow','create_tweet']]+([('W3',str(n))for n in [0,5,15,30]]if tier=='t200'else[])
 for family,workload in workloads:
  for method in ['reference','latency']:
   warm=110 if method=='reference'or family=='W3'else 10;measure=(1000 if family=='W3'else 500)if method=='reference'else(100 if family=='W3'else 30);plan=TargetPlan(seed,targets,users);rows=[];counts={'warmup':collections.Counter(),'measured':collections.Counter()}
   for iswarm,n in [(True,warm),(False,measure)]:
    for i in range(n):
     name=users[i%len(users)];op=schedules[workload][i%100]if family=='W3'else workload;actor=uid(targets['users'][name]);signed=-1-i if iswarm else i;label='littlex/'+tier+'/'+family+'/'+workload+'/'+method+'/'+('warm'if iswarm else'measured')+'/'+str(i);x={'op':op,'actor_id':actor,'actor_root_id':roots[actor],'username':name}
     if op=='follow':x['target_id']=uid(plan.next_follow(name));x['new_edge_id']=str(uuid.uuid5(uuid.NAMESPACE_URL,label+'/follow'))
     elif op=='like':x['tweet_id']=uid(plan.next_like(name))
     elif op=='create_tweet':x.update(new_id=str(uuid.uuid5(uuid.NAMESPACE_URL,label+'/tweet')),new_edge_id=str(uuid.uuid5(uuid.NAMESPACE_URL,label+'/post')),seed_id='w2_'+str(signed),content='write bench tweet '+str(signed)+' #bench',created_at=(datetime.datetime(2026,10,20,23,tzinfo=datetime.timezone.utc)+datetime.timedelta(microseconds=len(rows))).isoformat(timespec='microseconds').replace('+00:00','Z'))
     rows.append({'warmup':iswarm,'iteration':i,'input':x});counts['warmup'if iswarm else'measured'][op]+=1
   name=tier+'-'+family+'-'+workload+'-'+method;p=out/(name+'.json');p.write_text(json.dumps(rows,indent=2)+'\n');ledger.append({'tier':tier,'workload':family,'operation':workload,'method':method,'warmup':warm,'measured':measure,'per_operation_counts':counts,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'reset_scope':'fresh state per cell; TargetPlan survives warmup→measurement; schedule and user indices restart at0'})
(out/'manifest.json').write_text(json.dumps(ledger,indent=2)+'\n');print('Frozen plans',len(ledger))
