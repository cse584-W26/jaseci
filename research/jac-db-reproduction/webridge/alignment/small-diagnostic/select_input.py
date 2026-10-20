import json,re,collections
from pathlib import Path
home=Path(__file__).resolve().parent; fixture=home.parent/'graph-fixture'; x=json.loads((fixture/'inputs.json').read_text())[1]
def unescape(s):
 return re.sub(r'\\([\\tnr])',lambda m:{'\\':'\\','t':'\t','n':'\n','r':'\r'}[m[1]],s)
knows=[];members=[];containers=collections.defaultdict(list);creators=collections.defaultdict(list);forums={}
for line in (fixture/'anchors.tsv').open():
 a=line.rstrip('\n').split('\t'); kind,t=a[1:3]
 if t=='Knows':knows.append((a[6],a[7],int(a[11])))
 elif t=='HasMember':members.append((a[6],a[7],json.loads(unescape(a[9]))['archetype']['joinDate'],int(a[11])))
 elif t=='ContainerOf':containers[a[6]].append((int(a[11]),a[7]))
 elif t=='HasCreator':creators[a[6]].append((int(a[11]),a[7]))
 elif t=='Forum':forums[a[0]]=json.loads(unescape(a[9]))['archetype']
friends=[b for a,b,s in sorted(knows,key=lambda z:z[2]) if a==x['person_jid']]+[a for a,b,s in sorted(knows,key=lambda z:z[2]) if b==x['person_jid']]
relevant=[m for m in members if m[1] in friends and m[2]>x['min_date']]; dates=sorted(set(m[2] for m in relevant));candidates=[]
for threshold in dates:
 joined=collections.defaultdict(set)
 for f,p,d,s in relevant:
  if d>threshold:joined[f].add(p)
 posts=sum(len(containers[f]) for f in joined)
 if not joined or not posts:continue
 out=[]
 for f,users in joined.items():
  count=0
  for _,post in sorted(containers[f]):
   cs=sorted(creators[post]);count+=bool(cs and cs[0][1] in users)
  out.append([forums[f]['forum_id'],forums[f]['title'],count])
 out.sort(key=lambda r:(-r[2],r[0]));candidates.append({'threshold':threshold,'forums':len(joined),'posts':posts,'expected':out[:20]})
candidates.sort(key=lambda r:(r['posts']+r['forums'],r['forums'],-r['threshold']))
chosen=candidates[0];new=dict(x,min_date=chosen['threshold'],expected=chosen['expected']);(home/'input.json').write_text(json.dumps(new,indent=2));(home/'selection.json').write_text(json.dumps({'original_idx':1,'original_min_date':x['min_date'],'friends':len(friends),'chosen':chosen,'candidate_count':len(candidates),'best10':candidates[:10],'subset_proof':'Same person; threshold strictly increases, so every accepted HasMember edge and all dependent Forum/Post/creator edges belong to original exported fixture.'},indent=2));print(json.dumps(chosen))
