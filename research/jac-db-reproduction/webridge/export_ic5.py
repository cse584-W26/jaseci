"""Export the existing SNB SF1 fixture for an equivalent Java/JDBC traversal."""
from pathlib import Path
import json,hashlib
import psycopg
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
queries={
 'knows':'SELECT person1_id,person2_id FROM knows ORDER BY person1_id,person2_id',
 'forum':'SELECT id,title FROM forum ORDER BY id',
 'forum_member':'SELECT forum_id,person_id,join_date FROM forum_member ORDER BY forum_id,person_id',
 'post':'SELECT id,creator_id,forum_id FROM post WHERE forum_id IS NOT NULL ORDER BY id',
}
manifest={}
with psycopg.connect('postgresql://postgres@127.0.0.1:55436/snb') as c:
 for name,sql in queries.items():
  p=DATA/(name+'.tsv')
  with c.cursor().copy('COPY ('+sql+") TO STDOUT WITH (FORMAT text)") as copy,p.open('wb') as f:
   for b in copy:f.write(b)
  manifest[name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':c.execute('SELECT count(*) FROM ('+sql+') q').fetchone()[0]}
  print(name,manifest[name],flush=True)
 rows=json.loads((ROOT.parent/'results/baseline-census/rows.json').read_text())
 inputs=[{'idx':r['idx'],'pid':int(r['input']['personId']),'min_date':int(r['input']['minDate'])} for r in rows]
 seen=set();inputs=[x for x in inputs if not (x['idx'] in seen or seen.add(x['idx']))]
 oracle_sql='''WITH friends AS (SELECT person2_id AS id FROM knows WHERE person1_id=%s), joined AS (SELECT fm.forum_id,fm.person_id FROM forum_member fm JOIN friends f ON f.id=fm.person_id WHERE fm.join_date>%s) SELECT j.forum_id,fo.title,count(po.id) FROM joined j JOIN forum fo ON fo.id=j.forum_id LEFT JOIN post po ON po.forum_id=j.forum_id AND po.creator_id=j.person_id GROUP BY j.forum_id,fo.title ORDER BY count(po.id) DESC,j.forum_id ASC LIMIT 20'''
 for x in inputs:x['expected']=[list(r) for r in c.execute(oracle_sql,(x['pid'],x['min_date'])).fetchall()]
(ROOT/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
(ROOT/'data-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
