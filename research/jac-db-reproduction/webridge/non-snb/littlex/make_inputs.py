#!/usr/bin/env python3
"""Deterministic valid targets from original seed+TargetPlan, with seed-derived oracle rows."""
import pathlib,json,uuid,sys
H=pathlib.Path(__file__).resolve().parent;R=H.parents[2];recipe=json.loads((H/'recipe.json').read_text());sys.path.insert(0,str(R/'littlex/harness'));from write_run import TargetPlan
for tier,t in recipe['tiers'].items():
 seed=json.loads(pathlib.Path(t['seed']).read_text());f=pathlib.Path(t['fixture_manifest']).parent;targets=json.loads((f/'tokens/targets.jaseci.json').read_text());users=sorted(targets['users']);plan=TargetPlan(seed,targets,users);oracles=json.loads((H/(tier+'-seed-oracles.json')).read_text());byuser={r['username']:r for r in oracles};rows=[]
 def uid(v):return str(uuid.UUID(v.zfill(32)))
 for name in users:
  for op,key in [('feed','full_seed_ids'),('feed_page','page20_seed_ids')]:rows.append({'op':op,'actor_id':uid(targets['users'][name]),'username':name,'expected_seed_ids':byuser[name][key]})
 actor=users[0];base={'actor_id':uid(targets['users'][actor]),'username':actor};rows.extend([dict(base,op='follow',target_id=uid(plan.next_follow(actor))),dict(base,op='like',tweet_id=uid(plan.next_like(actor))),dict(base,op='create_tweet',new_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'littlex-gate-'+tier)),seed_id='w2_gate_'+tier,content='write bench tweet gate #bench',created_at='2026-10-20T23:00:00Z')]);(H/(tier+'-gate-inputs.json')).write_text(json.dumps(rows,indent=2)+'\n')
