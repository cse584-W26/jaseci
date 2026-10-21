#!/usr/bin/env python3
"""Freeze original littleX input provenance and seed-derived semantic oracles."""
import pathlib,json,hashlib,collections,importlib.util
H=pathlib.Path(__file__).resolve().parent;R=H.parents[2];L=R/'littlex'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out={'workloads':{'W1':{'operation':'full feed','tiers':['t20','t50','t100','t200'],'historical_timed_requests':500,'historical_warmup':110},'W2':{'operations':['create_tweet','follow','like'],'tiers':['t20','t50','t100','t200'],'historical_timed_requests':500,'historical_warmup':110,'protocols':{'canonical_fresh_matrix':'fresh cohort per operation','historical_original_recipe':'one tier/server cohort shared across like, follow, create_tweet in that order'}},'W3':{'operation':'paged feed plus deterministic writes','tiers':['t200'],'write_fraction_percent':[0,5,15,30],'write_mix_weights':{'create_tweet':10,'like':4,'follow':1},'historical_timed_requests':1000,'historical_warmup':110}},'sources':{},'tiers':{}}
for f in ['historical-app-source/app.jac','postgres/app.py','harness/write_run.py','harness/mix_run.py','harness/oracle.py','harness/run.py']:
 p=L/f;out['sources'][f]={'path':str(p),'sha256':sha(p)}
for tier in ['t20','t50','t100','t200']:
 seed=L/'dataset'/('uniform_seed.json'if tier=='t50'else tier+'_seed.json');s=json.loads(seed.read_text());fixture=next((p,json.loads(p.read_text()))for p in(L/'fixtures'/tier).glob('*/fixture.json')if json.loads(p.read_text())['runtime_commit'].startswith('ad469'));fp,fd=fixture
 assert sha(seed)==fd['seed_sha256'];users={x['id']:x for x in s['profiles']};follow=collections.defaultdict(set)
 for f in s['follows']:follow[f['follower']].add(f['followee'])
 feeds={};oracle=[]
 for uid,u in users.items():
  authors=follow[uid]|{uid};tweets=[t for t in s['tweets']if t['author']in authors];tweets.sort(key=lambda t:t['created_at'],reverse=True);feeds[u['username']]=len(tweets);oracle.append({'username':u['username'],'full_seed_ids':[t['id']for t in tweets],'page20_seed_ids':[t['id']for t in tweets[:20]]})
 out['tiers'][tier]={'seed':str(seed),'seed_sha256':sha(seed),'historical_snapshot':fd['snapshot'],'fixture_manifest':str(fp),'fixture_manifest_sha256':sha(fp),'profiles':len(users),'follows':len(s['follows']),'tweets':len(s['tweets']),'likes':sum(len(t['likes'])for t in s['tweets']),'feed_counts':sorted(set(feeds.values())),'oracle_payload_sha256':hashlib.sha256(json.dumps(oracle,sort_keys=True).encode()).hexdigest()}
 (H/(tier+'-seed-oracles.json')).write_text(json.dumps(oracle,indent=2)+'\n')
(H/'recipe.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:{x:v[x]for x in ['profiles','follows','tweets','feed_counts']}for k,v in out['tiers'].items()},indent=2))
