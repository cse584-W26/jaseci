#!/usr/bin/env python3
"""Load exported historical graph plus explicit conventional relations into dedicated MySQL DBs."""
import pathlib,json,subprocess,time,sys,hashlib,argparse
H=pathlib.Path(__file__).resolve().parent;W=H.parents[1];sys.path.insert(0,str(H.parent));from measurement_lease import lease
p=argparse.ArgumentParser();p.add_argument('--tiers',nargs='+',default=['t20','t50','t100','t200']);a=p.parse_args();C='jac-webridge-mysql57'
def cli(s):
 r=subprocess.run(['docker','exec','-i',C,'mysql','--local-infile=1','--default-character-set=utf8mb4','-uroot','-N','-B','-r'],input=s.encode(),capture_output=True);assert r.returncode==0,r.stderr.decode();return r.stdout.decode()
with lease('littlex dedicated MySQL fixture load',H/('mysql-load-lease-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'.json')):
 for tier in a.tiers:
  d=H/'fixtures'/tier;meta=json.loads((d/'export.json').read_text());db='jac_lx_'+tier+'_20261020';assert cli("SELECT count(*) FROM information_schema.schemata WHERE schema_name='"+db+"'").strip()=='0','Refuse overwrite';assert cli('SELECT @@global.local_infile').strip()=='1'
  sql=(W/'alignment/schema.sql').read_text().replace('jac_alignment',db).replace('CHARACTER SET ascii COLLATE ascii_bin','CHARACTER SET utf8mb4 COLLATE utf8mb4_bin').replace('CHARACTER SET ascii','CHARACTER SET utf8mb4 COLLATE utf8mb4_bin');cli(sql)
  for t,info in meta['tables'].items():
   if t not in ['anchors','graph_types','identity_users','kv_state']:
    cli('USE '+db+';CREATE TABLE `'+t+'`('+','.join('`'+col[0]+'` LONGTEXT CHARACTER SET utf8mb4' for col in info['source_columns'])+');')
   tmp='/tmp/wb-littlex-'+tier+'-'+t+'.tsv';subprocess.run(['docker','cp',info['path'],C+':'+tmp],check=True,capture_output=True)
   try:
    suffix="(id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,@undirected,props,row_version,seq,src_type,dst_type) SET undirected=(@undirected='t')"if t=='anchors'else'';cli('USE '+db+";LOAD DATA LOCAL INFILE '"+tmp+"' INTO TABLE `"+t+'` CHARACTER SET utf8mb4 '+suffix+';')
   finally:subprocess.run(['docker','exec',C,'rm','-f',tmp],check=True)
  mirror="""
CREATE TABLE lx_profiles(id CHAR(36) COLLATE utf8mb4_bin PRIMARY KEY,username VARCHAR(255) COLLATE utf8mb4_bin UNIQUE,bio LONGTEXT,created_at VARCHAR(100));
INSERT INTO lx_profiles SELECT id,JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.username')),JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.bio')),JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.created_at')) FROM anchors WHERE kind='NodeAnchor' AND arch_type='Profile';
CREATE TABLE lx_follows(follower_id CHAR(36) COLLATE utf8mb4_bin,followee_id CHAR(36) COLLATE utf8mb4_bin,PRIMARY KEY(follower_id,followee_id),KEY reverse_follow(followee_id,follower_id));
INSERT INTO lx_follows SELECT src,dst FROM anchors WHERE kind='EdgeAnchor' AND arch_type='Follow';
CREATE TABLE lx_tweets(id CHAR(36) COLLATE utf8mb4_bin PRIMARY KEY,seed_id VARCHAR(255) COLLATE utf8mb4_bin UNIQUE,author_id CHAR(36) COLLATE utf8mb4_bin,content LONGTEXT,created_at VARCHAR(100),likes LONGTEXT,comments LONGTEXT,KEY author_time(author_id,created_at));
INSERT INTO lx_tweets SELECT t.id,JSON_UNQUOTE(JSON_EXTRACT(t.props,'$.archetype.seed_id')),e.src,JSON_UNQUOTE(JSON_EXTRACT(t.props,'$.archetype.content')),JSON_UNQUOTE(JSON_EXTRACT(t.props,'$.archetype.created_at')),JSON_EXTRACT(t.props,'$.archetype.likes'),JSON_EXTRACT(t.props,'$.archetype.comments') FROM anchors t JOIN anchors e ON e.dst=t.id AND e.kind='EdgeAnchor' AND e.arch_type='Post' WHERE t.kind='NodeAnchor' AND t.arch_type='Tweet';
ANALYZE TABLE anchors,lx_profiles,lx_tweets,lx_follows;
""";cli('USE '+db+';'+mirror);(d/'mysql-schema.sql').write_text(sql+'\nUSE '+db+';\n'+mirror)
  counts=cli('USE '+db+';SELECT (SELECT count(*) FROM anchors),(SELECT count(*) FROM lx_profiles),(SELECT count(*) FROM lx_follows),(SELECT count(*) FROM lx_tweets);').strip();expected=json.loads((H/'recipe.json').read_text())['tiers'][tier];actual=list(map(int,counts.split('\t')));assert actual==[meta['tables']['anchors']['rows'],expected['profiles'],expected['follows'],expected['tweets']],actual
  (d/'mysql-load.json').write_text(json.dumps({'database':db,'container':C,'counts':actual,'schema_sha256':hashlib.sha256((sql+mirror).encode()).hexdigest(),'export_sha256':hashlib.sha256((d/'export.json').read_bytes()).hexdigest(),'ended_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())},indent=2)+'\n');print(tier,counts,flush=True)
