#!/usr/bin/env python3
"""Complete union closure for all20 original remaining-six SNB inputs; source graph unchanged."""
import pathlib,json,time,hashlib,psycopg
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];REPRO=B.parent;APP=REPRO/'benchmark/snb/jaseci-pg';PARAM=REPRO/'benchmark/snb/data/substitution_parameters-sf1';out=H/'data';out.mkdir(exist_ok=False)
files=['interactive_1_param.txt','interactive_2_param.txt','interactive_13_param.txt'];targets=json.loads((APP/'targets_person.json').read_text());inputs={}
for f in files:
 lines=(PARAM/f).read_text().splitlines();head=lines[0].split('|');inputs[f]=[dict(zip(head,x.split('|')))for x in lines[1:21]]
(out/'parameters.json').write_text(json.dumps(inputs,indent=2)+'\n');receipt={'source_database':'jac_snb_bench_pg_fbdb3a2c','source_app_sha256':hashlib.sha256((APP/'app.jac').read_bytes()).hexdigest(),'scope':'AllPerson+allKnows; complete authored messages for IS2 persons and IC2 friends; complete ReplyOf ancestor paths; IS1 location relations; endpoint and owner-root closure','steps':[]}
c=psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname=receipt['source_database']);cur=c.cursor()
def run(n,s,p=None):
 t=time.monotonic();cur.execute(s,p);receipt['steps'].append({'name':n,'sql':s,'rows':cur.rowcount,'seconds':time.monotonic()-t});print(n,cur.rowcount,flush=True)
run('parameters','CREATE TEMP TABLE seed_people(id uuid, role text)')
with cur.copy('COPY seed_people FROM STDIN')as cp:
 for row in inputs[files[0]]:cp.write_row((targets[row['personId']],'is2'))
 for row in inputs[files[1]]:cp.write_row((targets[row['personId']],'ic2'))
run('all_person','CREATE TEMP TABLE selected_ids(id uuid PRIMARY KEY)');run('persons',"INSERT INTO selected_ids SELECT id FROM anchors WHERE kind='NodeAnchor' AND arch_type='Person'")
run('all_knows',"INSERT INTO selected_ids SELECT id FROM anchors WHERE kind='EdgeAnchor' AND arch_type='Knows' ON CONFLICT DO NOTHING")
run('authors',"CREATE TEMP TABLE authors AS SELECT id FROM seed_people WHERE role='is2' UNION SELECT CASE WHEN e.src=p.id THEN e.dst ELSE e.src END FROM seed_people p JOIN anchors e ON e.kind='EdgeAnchor' AND e.arch_type='Knows' AND(e.src=p.id OR e.dst=p.id) WHERE p.role='ic2'");run('author_index','CREATE UNIQUE INDEX ON authors(id)')
run('messages',"CREATE TEMP TABLE messages AS SELECT DISTINCT e.src AS id FROM authors a JOIN anchors e ON e.dst=a.id AND e.kind='EdgeAnchor' AND e.arch_type='HasCreator' JOIN anchors m ON m.id=e.src AND m.kind='NodeAnchor' AND m.arch_type IN('Post','Comment')");run('msg_index','CREATE UNIQUE INDEX ON messages(id)')
run('reply_chain',"CREATE TEMP TABLE reply_nodes AS WITH RECURSIVE chain(id) AS(SELECT id FROM messages UNION SELECT e.dst FROM chain c JOIN anchors e ON e.src=c.id AND e.kind='EdgeAnchor' AND e.arch_type='ReplyOf') SELECT id FROM chain");run('reply_index','CREATE UNIQUE INDEX ON reply_nodes(id)')
run('reply_nodes_insert','INSERT INTO selected_ids SELECT id FROM reply_nodes ON CONFLICT DO NOTHING')
run('reply_edges',"INSERT INTO selected_ids SELECT e.id FROM reply_nodes n JOIN anchors e ON e.src=n.id AND e.kind='EdgeAnchor' AND e.arch_type IN('HasCreator','ReplyOf') ON CONFLICT DO NOTHING")
run('locations',"INSERT INTO selected_ids SELECT e.id FROM seed_people p JOIN anchors e ON e.src=p.id AND e.kind='EdgeAnchor' AND e.arch_type='IsLocatedIn' ON CONFLICT DO NOTHING")
run('endpoints',"INSERT INTO selected_ids SELECT a.src FROM anchors a JOIN selected_ids s ON s.id=a.id WHERE a.src IS NOT NULL UNION SELECT a.dst FROM anchors a JOIN selected_ids s ON s.id=a.id WHERE a.dst IS NOT NULL ON CONFLICT DO NOTHING")
for depth in range(20):
 cur.execute('INSERT INTO selected_ids SELECT a.root_id FROM anchors a JOIN selected_ids s ON s.id=a.id WHERE a.root_id IS NOT NULL ON CONFLICT DO NOTHING')
 if cur.rowcount==0:break
else:raise RuntimeError('owner closure exceeded20')
receipt['types']=cur.execute('SELECT a.kind,a.arch_type,count(*) FROM anchors a JOIN selected_ids s ON s.id=a.id GROUP BY 1,2 ORDER BY 1,2').fetchall()
for name,query in [('anchors','SELECT a.id,a.kind,a.arch_type,a.arch_module,a.fingerprint,a.root_id,a.src,a.dst,a.undirected,a.props::text,a.xmin::text,a.seq,a.src_type,a.dst_type FROM anchors a JOIN selected_ids s ON s.id=a.id ORDER BY a.id'),('graph_types','SELECT type_name,ancestor FROM graph_types ORDER BY 1,2')]:
 p=out/(name+'.tsv');h=hashlib.sha256();count=0
 with cur.copy('COPY ('+query+') TO STDOUT WITH(FORMAT text)')as cp,p.open('wb')as f:
  for chunk in cp:f.write(chunk);h.update(chunk);count+=bytes(chunk).count(b'\n')
 receipt[name]={'bytes':p.stat().st_size,'rows':count,'sha256':h.hexdigest()};print(name,receipt[name],flush=True)
(H/'export-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');c.rollback();c.close()
