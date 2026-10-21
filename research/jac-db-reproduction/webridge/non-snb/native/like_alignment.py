"""Record actual LIKE target-owner aliasing, source branch, and measured command ledger."""
import pathlib,json,gzip,collections
R=pathlib.Path(__file__).resolve().parent;L=R.parent/'littlex';recipe=json.loads((L/'recipe.json').read_text());fixture=L/'fixtures/t20/anchors.tsv';roots={}
for line in fixture.open():
    x=line.rstrip('\n').split('\t');roots[x[0]]=x[5]
private=pathlib.Path(recipe['tiers']['t20']['fixture_manifest']).parent/'tokens/targets.jaseci.json';users=json.loads(private.read_text())['users']
def uuid(x):return x if '-'in x else x[:8]+'-'+x[8:12]+'-'+x[12:16]+'-'+x[16:20]+'-'+x[20:]
cert=json.loads((R/'littlex-pilot-like/certified-requests.json').read_text());out=[]
for variant in ['baseline','final']:
    p=R/'littlex-pilot-like/delay-0ms'/variant/'t20/W2-like';rows=[json.loads(s)for s in gzip.open(p/'rows.jsonl.gz','rt')];rows=[x for x in rows if not x['warmup']]
    for row in rows:
        actor=roots[uuid(users[row['username']])];owner=roots[row['request_body']['tweet_id']];c=next(x for x in cert if x['request_tag']==row['request_tag']);out.append({'variant':variant,'iteration':row['iteration'],'actor_root':actor,'target_Tweet_root':owner,'same_owner':actor==owner,'actual_SQL_commands':c['actual_SQL_commands'],'actual_delivered_response_flights':c['actual_complete_response_flights'],'categories':dict(collections.Counter(x['category']for x in c['operations']))})
assert [x['same_owner']for x in out]==[True,False,False]*2
result={'scope':'Actual t20 LIKE original frozen 10-warm+3-profile schedule. Earlier census uses different actors/targets.','observations':out,'source_branch':{'ad469_path':'jac/jaclang/jac0core/impl/runtime.impl.jac','owner_fast_path_line':134,'owner_root_load_line':146,'same_owner_behavior':'jroot.id == to.root returns WRITE before the owner-root mem.get; nonowner access reaches mem.get(to.root).','session_cache_path':'jac/jaclang/runtimelib/impl/session.impl.jac','session_get_lines':[296,306]},'alignment':'First measured input owns the target Tweet and executes one fewer owner-root hydration. The following two nonowner inputs match the early census counts11/10. Transaction, traversal, flush and type-registry statement counts are unchanged. Java full remains the separately frozen early warm-access port; these observed input-dependent branches are reported without padding.'}
(R/'littlex-like-alignment.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
