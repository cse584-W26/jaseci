"""Independent source-fixture littleX state and request-result checker."""
import json,pathlib,re,uuid,hashlib,datetime,gzip

def uid(s):return str(uuid.UUID(s))
def uncopy(value):
 return re.sub(r'\\([0-7]{1,3}|.)',lambda m: chr(int(m[1],8))if m[1][0].isdigit()else {'b':'\b','f':'\f','n':'\n','r':'\r','t':'\t','v':'\v','\\':'\\'}.get(m[1],m[1]),value)
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
class Oracle:
 def __init__(self,fixture):
  self.profiles={};self.profile_props={};self.tweets={};self.id_seed={};self.follows=set();self.generated=set();self.new_times=[];edges=[]
  fixture=pathlib.Path(fixture)
  if fixture.name.endswith('.json.gz'):
   data=json.load(gzip.open(fixture,'rt'));self.profiles=data['profiles'];self.profile_props=data['profile_props'];self.tweets=data['tweets'];self.id_seed=data['id_seed'];self.follows={tuple(x)for x in data['follows']};self.initial_tweets=len(self.tweets);self.initial_follows=len(self.follows);self.initial_likes=sum(len(t['likes'])for t in self.tweets.values());return
  for line in fixture.open():
   r=line.rstrip('\n').split('\t')
   if r[1]=='NodeAnchor'and r[2]in ('Profile','Tweet'):
    a=json.loads(uncopy(r[9]))['archetype']
    if r[2]=='Profile':self.profiles[r[0]]=a['username'];self.profile_props[r[0]]=a
    else:self.tweets[a['seed_id']]=a;self.id_seed[r[0]]=a['seed_id']
   elif r[1]=='EdgeAnchor'and r[2]=='Follow':edges.append((r[6],r[7]))
  for a,b in edges:self.follows.add((self.profiles[a],self.profiles[b]))
  self.initial_tweets=len(self.tweets);self.initial_follows=len(self.follows);self.initial_likes=sum(len(t['likes'])for t in self.tweets.values())
 def apply(self,x,result):
  op=x['op'];name=x['username']
  if op in ('feed','feed_page'):
   authors={name}|{b for a,b in self.follows if a==name};expected=sorted((t for t in self.tweets.values()if t['author_username']in authors),key=lambda t:t['created_at'],reverse=True)
   if op=='feed_page':expected=expected[:20]
   actual=result['feed'];assert len(actual)==len(expected),(op,len(actual),len(expected))
   for a,e in zip(actual,expected):
    for k in ['seed_id','content','author_username','created_at','likes','comments']:assert a[k]==e[k],(op,k,a.get('seed_id'),e.get('seed_id'))
   return {'verified':True,'feed_rows':len(actual),'ordered_seed_sha256':digest([t['seed_id']for t in actual])}
  if op=='create_tweet':
   a=result['tweet'];assert a['seed_id']==x['seed_id']and a['content']==x['content']and a['author_username']==name
   assert a['likes']==[]and a['comments']==[];assert a['seed_id']not in self.tweets
   parsed=datetime.datetime.fromisoformat(a['created_at'].replace('Z','+00:00'));assert not self.new_times or parsed>=self.new_times[-1];self.new_times.append(parsed)
   self.tweets[a['seed_id']]={k:a[k]for k in ['seed_id','content','author_username','created_at','likes','comments']};self.id_seed[uid(a['_jac_id'])]=a['seed_id'];self.generated.add(a['seed_id'])
  elif op=='follow':
   assert result['success']is True;self.follows.add((name,self.profiles[uid(x['target_id'])]))
  elif op=='like':
   t=self.tweets[self.id_seed[uid(x['tweet_id'])]]
   if name not in t['likes']:t['likes'].append(name)
   assert result['success']is True and result['likes_count']==len(t['likes'])
  else:raise ValueError(op)
  return {'verified':True,'operation':op}
 def canonical(self):
  tweets=[]
  for seed,t in sorted(self.tweets.items()):tweets.append([seed,t['content'],t['author_username'],'GENERATED_TIME'if seed in self.generated else t['created_at'],t['likes'],t['comments']])
  return {'profiles':sorted([[self.profiles[id],props]for id,props in self.profile_props.items()]),'follows':sorted(map(list,self.follows)),'tweets':tweets}
 def verify_database(self,conn):
  actual={};ids={};post=[];follows=[]
  for kind,typ,id,src,dst,props in conn.execute("SELECT kind,arch_type,id::text,src::text,dst::text,props FROM anchors WHERE (kind='NodeAnchor' AND arch_type IN ('Profile','Tweet'))OR(kind='EdgeAnchor' AND arch_type IN('Follow','Post'))"):
   if kind=='NodeAnchor':
    if typ=='Profile':
     ids[id]=props['archetype']['username'];assert props['archetype']==self.profile_props[id],id
    else:
     a=props['archetype'];actual[a['seed_id']]=a
   elif typ=='Follow':follows.append((src,dst))
   else:post.append((src,dst))
  assert set(ids.values())==set(self.profiles.values());assert{(ids[a],ids[b])for a,b in follows}==self.follows;assert len(follows)==len(self.follows)
  assert set(actual)==set(self.tweets)
  for seed,a in actual.items():
   for k in ['seed_id','content','author_username','created_at','likes','comments']:assert a[k]==self.tweets[seed][k],(seed,k)
  assert len(post)==len(actual)
  # Every Post relation points from the declared author to its exact Tweet.
  reverse={seed:id for id,seed in self.id_seed.items()};assert{(ids[a],b)for a,b in post}=={(t['author_username'],reverse[seed])for seed,t in actual.items()}
  c=self.canonical();return {'exact_business_state_verified':True,'rows':{k:len(v)for k,v in c.items()},'sha256':{k:digest(v)for k,v in c.items()},'generated_uuid_and_clock_normalization':'new Tweet keyed by seed_id, new timestamp replaced by GENERATED_TIME; raw response retained','canonical':c}
