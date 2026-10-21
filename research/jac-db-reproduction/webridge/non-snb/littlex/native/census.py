#!/usr/bin/env python3
"""Actual warmed littleX statements and bound parameters on a dedicated mutable clone."""
import pathlib,json,time,sys,subprocess,gzip,hashlib,uuid,shutil,argparse
import psycopg,httpx
H=pathlib.Path(__file__).resolve().parent;L=H.parent;REPRO=H.parents[3];sys.path.insert(0,str(L.parent));from measurement_lease import lease
sys.path.insert(0,str(REPRO/'littlex/harness'));from write_run import TargetPlan
p=argparse.ArgumentParser();p.add_argument('--variant',choices=['baseline','final'],default='baseline');p.add_argument('--operations',nargs='+',default=['feed','feed_page','like','follow','create_tweet']);p.add_argument('--page-walker',default='load_feed_page_chain',choices=['load_feed_page','load_feed_page_chain']);p.add_argument('--page-warmup',type=int,default=1);a=p.parse_args();stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime());out=H/'census'/(stamp+'-'+a.variant+('-page-original'if a.page_walker=='load_feed_page'else''));out.mkdir(parents=True);recipe=json.loads((L/'recipe.json').read_text())['tiers']['t20'];folder=pathlib.Path(recipe['fixture_manifest']).parent;tokens=json.loads((folder/'tokens/tokens.jaseci.json').read_text());targets=json.loads((folder/'tokens/targets.jaseci.json').read_text());users=sorted(tokens);seed=json.loads(pathlib.Path(recipe['seed']).read_text());plan=TargetPlan(seed,targets,users);log=REPRO/'dbcache/pg/main/server.log';db='jac_wb_lx_census_'+a.variant+'_'+stamp.lower();service=H/'service.py';admin=psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname='postgres',autocommit=True);rows=[];started=False

def launch(action):
 r=subprocess.run([sys.executable,str(service),action,'--variant',a.variant,'--database',db],capture_output=True,text=True);(out/(action+'.stdout')).write_text(r.stdout);(out/(action+'.stderr')).write_text(r.stderr);assert r.returncode==0,r.stderr

def counts():
 with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname=db)as c:return dict(tweets=c.execute("SELECT count(*) FROM anchors WHERE kind='NodeAnchor' AND arch_type='Tweet'").fetchone()[0],follows=c.execute("SELECT count(*) FROM anchors WHERE kind='EdgeAnchor' AND arch_type='Follow'").fetchone()[0],likes=c.execute("SELECT COALESCE(sum(jsonb_array_length(props->'archetype'->'likes')),0) FROM anchors WHERE kind='NodeAnchor' AND arch_type='Tweet'").fetchone()[0])
with lease('littlex actual native census '+a.variant,out/'lease.json'):
 try:
  admin.execute(psycopg.sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(psycopg.sql.Identifier(db),psycopg.sql.Identifier(recipe['historical_snapshot'])))
  for key,val in [('log_min_duration_statement','0'),('log_statement','none'),('log_duration','off')]:admin.execute(psycopg.sql.SQL('ALTER DATABASE {} SET {} TO {}').format(psycopg.sql.Identifier(db),psycopg.sql.Identifier(key),psycopg.sql.Literal(val)))
  launch('start');started=True;shutil.copy2(H/a.variant/'launch.json',out/'launch.json');shutil.copy2(H/a.variant/'source.json',out/'source.json')
  with httpx.Client(base_url='http://127.0.0.1:18134',timeout=120)as c:
   for op,walker in [('feed','load_feed_chain'),('feed_page',a.page_walker),('like','like_tweet'),('follow','follow_user'),('create_tweet','create_tweet')]:
    if op not in a.operations:continue
    d=out/op;d.mkdir()
    if op=='feed_page'and a.page_warmup>1:
     for w in range(a.page_warmup-1):
      name=users[w%len(users)];r=c.post('/walker/'+walker,json={},headers={'Authorization':'Bearer '+tokens[name]});r.raise_for_status()
     (out/'additional-page-warmup.json').write_text(json.dumps({'walker':walker,'requests':a.page_warmup-1,'phase':'before recorded warm plus3 measured','user_cycle':'sorted original users round robin'},indent=2))
    for i in range(4):
     name=users[i];body={}
     if op=='like':body={'tweet_id':plan.next_like(name)}
     elif op=='follow':body={'target_id':plan.next_follow(name)}
     elif op=='create_tweet':body={'seed_id':'w2_census_'+stamp+'_'+str(i),'content':'write bench tweet '+str(i)+' #bench'}
     before=counts();offset=log.stat().st_size;t=time.monotonic_ns();r=c.post('/walker/'+walker,json=body,headers={'Authorization':'Bearer '+tokens[name]});elapsed=(time.monotonic_ns()-t)/1e6;r.raise_for_status();payload=r.json();data=payload.get('data',payload);result=data['reports'][0]if isinstance(data,dict)and'reports'in data else data;time.sleep(.1)
     with log.open('rb')as f:f.seek(offset);raw=f.read()
     gzip.open(d/('warm.log.gz'if i==0 else'profile-'+str(i-1)+'.log.gz'),'wb').write(raw);after=counts();entry={'op':op,'walker':walker,'username':name,'actor_id':targets['users'][name],'body':body,'warmup':i==0,'iteration':i,'client_ms':elapsed,'headers':dict(r.headers),'state_before':before,'state_after':after,'result':result,'log_bytes':len(raw)};rows.append(entry)
     if op in ['feed','feed_page']:
      expected=(1020 if op=='feed' else 20);assert len(result['feed'])==expected,(op,len(result['feed']))
     else:
      key={'like':'likes','follow':'follows','create_tweet':'tweets'}[op];assert after[key]-before[key]==1,(op,before,after,result)
     (out/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(op,'captured3 warmed requests',flush=True)
 finally:
  if started:launch('stop')
  for key in ['log_min_duration_statement','log_statement','log_duration']:admin.execute(psycopg.sql.SQL('ALTER DATABASE {} RESET {}').format(psycopg.sql.Identifier(db),psycopg.sql.Identifier(key)))
  (out/'cleanup.json').write_text(json.dumps({'service_stopped':not(H/a.variant/'service.pid').exists(),'database_settings_reset':True,'dedicated_database':db,'requests':len(rows),'source_snapshot_preserved':recipe['historical_snapshot']},indent=2));admin.close()
print(out)
