#!/usr/bin/env python3
"""Independent canonical littleX entity/relation state, shared by both storage forms."""
import pathlib,json,subprocess,hashlib,argparse,sys
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease

def snapshot(database,graph,rows_out=None):
 queries={
 'profiles':"SELECT id,JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.username')) FROM anchors WHERE kind='NodeAnchor' AND arch_type='Profile' ORDER BY id"if graph else'SELECT id,username FROM lx_profiles ORDER BY id',
 'follows':"SELECT src,dst FROM anchors WHERE kind='EdgeAnchor' AND arch_type='Follow' ORDER BY src,dst"if graph else'SELECT follower_id,followee_id FROM lx_follows ORDER BY follower_id,followee_id',
 'tweets':"SELECT id,JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.seed_id')),JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.content')),JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.author_username')),JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.created_at')),JSON_EXTRACT(props,'$.archetype.likes'),JSON_EXTRACT(props,'$.archetype.comments') FROM anchors WHERE kind='NodeAnchor' AND arch_type='Tweet' ORDER BY id"if graph else'SELECT t.id,t.seed_id,t.content,p.username,t.created_at,t.likes,t.comments FROM lx_tweets t JOIN lx_profiles p ON p.id=t.author_id ORDER BY t.id'}
 out={};all_rows={}
 for name,q in queries.items():
  # JSON_ARRAY transports tabs/newlines safely; outer query retains the original stable order.
  cols={'profiles':['id','username'],'follows':['src','dst'],'tweets':['id','seed_id','content','author','created','likes','comments']}[name]
  # Use the text protocol and undo its explicit escaping; every selected field has a known type.
  r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot','-N','-B',database],input=q.encode(),capture_output=True);assert r.returncode==0,r.stderr
  def unescape(v):
   chars={'0':'\0','n':'\n','r':'\r','t':'\t','b':'\b','Z':'\x1a','\\':'\\'};import re
   return re.sub(r'\\(.)',lambda m:chars.get(m[1],m[1]),v)
  rows=[]
  for line in r.stdout.decode().split('\n'):
   if not line:continue
   v=[unescape(x)for x in line.split('\t')]
   if name=='tweets':v[-2:]=[json.loads(x)for x in v[-2:]]
   rows.append(v)
  all_rows[name]=rows
  out[name]={'rows':len(rows),'sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),'query':q}
 if rows_out:
  import gzip
  with gzip.open(rows_out,'wt',encoding='utf-8')as f:json.dump(all_rows,f,ensure_ascii=False,separators=(',',':'))
 return out
def expected_rows(oracle):
 import uuid
 normal=lambda x:str(uuid.UUID(x))
 profiles={normal(k):v for k,v in oracle.profiles.items()};by_name={name:id for id,name in profiles.items()};by_seed={seed:normal(id)for id,seed in oracle.id_seed.items()}
 rows={'profiles':sorted([[id,name]for id,name in profiles.items()]),'follows':sorted([[by_name[a],by_name[b]]for a,b in oracle.follows]),'tweets':sorted([[by_seed[seed],seed,t['content'],t['author_username'],t['created_at'],t['likes'],t['comments']]for seed,t in oracle.tweets.items()])}
 return rows
def expected(oracle):
 return {k:{'rows':len(v),'sha256':hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()}for k,v in expected_rows(oracle).items()}

def assert_expected(actual,wanted):
 compact={k:{'rows':v['rows'],'sha256':v['sha256']}for k,v in actual.items()};assert compact==wanted,{'actual':compact,'expected':wanted};return compact

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--database',required=True);p.add_argument('--implementation',default='LittleXSql');p.add_argument('--out',required=True,type=pathlib.Path);p.add_argument('--lease-held',action='store_true');a=p.parse_args()
 def run():a.out.write_text(json.dumps(snapshot(a.database,a.implementation!='LittleXSql'),indent=2)+'\n')
 if a.lease_held:run()
 else:
  with lease('littlex canonical business state',a.out.with_suffix('.lease.json')):run()
