"""Export an exact IC5 workload slice of the original anchor graph.
Only connection-local temp tables are created in PostgreSQL. Original tables stay intact.
"""
import argparse,base64,hashlib,json,os,time,uuid
from pathlib import Path
import psycopg
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 inputs=json.loads((HERE.parent/'inputs.json').read_text());app=ROOT/'benchmark/snb/jaseci-pg';targets=json.loads((app/'targets_person.json').read_text());token=json.loads((app/'svc_token.json').read_text())['svc'];claims=json.loads(base64.urlsafe_b64decode(token.split('.')[1]+'==='));uid=claims.get('sub') or claims['user_id'];manifest={'source_database':'jac_snb_bench_pg_fbdb3a2c','created_unix':time.time(),'scope':'Exact union of queried IC5 edge relations for the declared20inputs, plus their endpoint anchors and transitive owner roots. Generic node/edge records preserve original UUIDs, sequence, properties and ACL.','steps':[],'files':{}}
 c=psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname=manifest['source_database']);cur=c.cursor()
 def run(name,sql,params=None):
  t=time.monotonic();cur.execute(sql,params);manifest['steps'].append({'name':name,'sql':sql,'seconds':time.monotonic()-t,'rowcount':cur.rowcount});print(name,cur.rowcount,flush=True)
 run('inputs','CREATE TEMP TABLE align_inputs(idx int, id uuid, min_date bigint)')
 with cur.copy('COPY align_inputs FROM STDIN') as cp:
  for x in inputs:cp.write_row((x['idx'],uuid.UUID(targets[str(x['pid'])]),x['min_date']))
 run('knows',"CREATE TEMP TABLE align_knows AS SELECT DISTINCT e.id FROM align_inputs i JOIN anchors e ON e.kind='EdgeAnchor' AND e.arch_type='Knows' AND (e.src=i.id OR e.dst=i.id)")
 run('friends',"CREATE TEMP TABLE align_friends AS SELECT DISTINCT i.idx,i.min_date,CASE WHEN e.src=i.id THEN e.dst ELSE e.src END AS id FROM align_inputs i JOIN anchors e ON e.kind='EdgeAnchor' AND e.arch_type='Knows' AND (e.src=i.id OR e.dst=i.id) JOIN anchors n ON n.id=CASE WHEN e.src=i.id THEN e.dst ELSE e.src END AND n.arch_type='Person'")
 run('members',"CREATE TEMP TABLE align_members AS SELECT DISTINCT e.id,e.src AS forum FROM align_friends f JOIN anchors e ON e.dst=f.id AND e.kind='EdgeAnchor' AND e.arch_type='HasMember' AND (e.props->'archetype'->>'joinDate')::bigint>f.min_date JOIN anchors n ON n.id=e.src AND n.arch_type='Forum'")
 run('forums','CREATE TEMP TABLE align_forums AS SELECT DISTINCT forum AS id FROM align_members');run('forum_index','CREATE UNIQUE INDEX ON align_forums(id)')
 run('containers',"CREATE TEMP TABLE align_containers AS SELECT e.id,e.dst AS post FROM align_forums f JOIN anchors e ON e.src=f.id AND e.kind='EdgeAnchor' AND e.arch_type='ContainerOf' JOIN anchors n ON n.id=e.dst AND n.arch_type='Post'")
 run('posts','CREATE TEMP TABLE align_posts AS SELECT DISTINCT post AS id FROM align_containers');run('post_index','CREATE UNIQUE INDEX ON align_posts(id)')
 run('creators',"CREATE TEMP TABLE align_creators AS SELECT e.id FROM align_posts p JOIN anchors e ON e.src=p.id AND e.kind='EdgeAnchor' AND e.arch_type='HasCreator' JOIN anchors n ON n.id=e.dst AND n.arch_type='Person'")
 run('edges','CREATE TEMP TABLE align_edges AS SELECT id FROM align_knows UNION SELECT id FROM align_members UNION SELECT id FROM align_containers UNION SELECT id FROM align_creators');run('edge_index','CREATE UNIQUE INDEX ON align_edges(id)')
 run('nodes',"CREATE TEMP TABLE align_ids(id uuid PRIMARY KEY); INSERT INTO align_ids SELECT id FROM align_edges UNION SELECT a.src FROM anchors a JOIN align_edges e ON e.id=a.id WHERE a.src IS NOT NULL UNION SELECT a.dst FROM anchors a JOIN align_edges e ON e.id=a.id WHERE a.dst IS NOT NULL UNION SELECT id FROM align_inputs")
 doc=cur.execute('SELECT doc FROM identity_users WHERE user_id=%s',(uid,)).fetchone()[0];rootid=doc['root_id'];cur.execute('INSERT INTO align_ids VALUES(%s) ON CONFLICT DO NOTHING',(uuid.UUID(rootid),))
 for depth in range(16):
  cur.execute('INSERT INTO align_ids SELECT DISTINCT a.root_id FROM anchors a JOIN align_ids i ON i.id=a.id WHERE a.root_id IS NOT NULL ON CONFLICT DO NOTHING')
  if cur.rowcount==0:break
 else:raise RuntimeError('Owner-root closure exceeded16levels')
 def export(name,query):
  p=a.out/(name+'.tsv')
  with cur.copy('COPY ('+query+') TO STDOUT WITH(FORMAT text)') as cp,p.open('wb') as f:
   for chunk in cp:f.write(chunk)
  h=hashlib.sha256()
  with p.open('rb') as f:
   for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
  manifest['files'][name]={'bytes':p.stat().st_size,'sha256':h.hexdigest()};print('export',name,p.stat().st_size,flush=True)
 export('anchors',"SELECT a.id,a.kind,a.arch_type,a.arch_module,a.fingerprint,a.root_id,a.src,a.dst,a.undirected,a.props::text,a.xmin::text,a.seq,a.src_type,a.dst_type FROM anchors a JOIN align_ids i ON i.id=a.id ORDER BY a.id")
 export('graph_types','SELECT type_name,ancestor FROM graph_types ORDER BY type_name,ancestor')
 export('identity_users','SELECT user_id,doc::text FROM identity_users WHERE user_id='+psycopg.sql.Literal(uid).as_string(c))
 (a.out/'identity_users.tsv').chmod(0o600)
 private=a.out/'request-context.json';private.write_text(json.dumps({'user_id':uid,'root_id':rootid,'claims':claims,'token_sha256':hashlib.sha256(token.encode()).hexdigest()},indent=2));private.chmod(0o600)
 for name in ['align_inputs','align_friends','align_forums','align_posts','align_edges','align_ids']:manifest[name]=cur.execute('SELECT count(*) FROM '+name).fetchone()[0]
 ainputs=[dict(x,person_jid=str(uuid.UUID(targets[str(x['pid'])])) ) for x in inputs];(a.out/'inputs.json').write_text(json.dumps(ainputs,indent=2))
 (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2));c.rollback();c.close()
if __name__=='__main__':main()
