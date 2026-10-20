import json,pathlib,collections,base64
def objects(path):
 s=path.read_text();i=0;out=[];decoder=json.JSONDecoder(strict=False)
 while i<len(s):
  while i<len(s) and s[i].isspace():i+=1
  if i==len(s):break
  x,i=decoder.raw_decode(s,i)
  if isinstance(x.get("sql"),str) and x["sql"].startswith("base64:type250:"):x["sql"]=base64.b64decode(x["sql"].split(":",2)[2]).decode("utf-8")
  out.append(x)
 return out
R=pathlib.Path(__file__).resolve().parent
for variant in ['full','pruned']:
 p=R/'census'/('small-'+variant+'-utf8');rows=[json.loads(s) for s in (p/'run/requests/rows.jsonl').read_text().splitlines()];logs=objects(p/'general-log.jsonl');queries=[x for x in logs if x['command']=='Query'];bounds=[i for i,x in enumerate(queries) if x['sql'].startswith('SHOW SESSION STATUS')];assert len(bounds)==2*len(rows),(len(bounds),len(rows));events=objects(p/'pfs.jsonl');eb=[x['event'] for x in events if x['sql'] and x['sql'].startswith('SHOW SESSION STATUS')];assert len(eb)==2*len(rows),(len(eb),len(rows));out=[]
 for i,r in enumerate(rows):
  q=queries[bounds[2*i]+1:bounds[2*i+1]];ev=[x for x in events if eb[2*i]<x['event']<eb[2*i+1]];tops=[x for x in ev if x['nest'] is None];assert len(q)==r['questions'],(i,len(q),r['questions']);cats=collections.Counter('CALL' if x['sql'].lower().startswith('call ') else 'metadata' if 'information_schema' in x['sql'].lower() else x['sql'].split()[0].upper() for x in q);calls=[x for x in tops if x['sql'] and x['sql'].lower().startswith('call ')];item={'phase':r['phase'],'warmup':r['warmup'],'iteration':r['iteration'],'client_ms':r['ms'],'app_thread_cpu_ms':r['thread_cpu_ms'],'wire_queries':len(q),'wire_categories':dict(cats),'pfs_top_level_ms':sum((x['timer_ps']or 0)/1e9 for x in tops),'pfs_top_level_rows_examined':sum(x['rows_examined']or 0 for x in tops)}
  if calls:
   c=calls[0];children=[x for x in ev if x['nest']==c['event']];g=collections.defaultdict(lambda:{'n':0,'ms':0.,'rows_examined':0})
   for x in children:
    a=g[x['name']];a['n']+=1;a['ms']+=(x['timer_ps']or 0)/1e9;a['rows_examined']+=x['rows_examined']or 0
   item.update(call_ms=c['timer_ps']/1e9,procedure_direct_children=dict(g),top_nested_sql=sorted([x for x in children if x['sql'] and x['sql'].upper().startswith('SELECT')],key=lambda x:x['timer_ps']or 0,reverse=True)[:5])
  out.append(item)
 (p/'classified.json').write_text(json.dumps({'all_wire_counts_match':True,'requests':out,'pfs_note':'Top-level times inclusive of stored procedure children; child categories reported separately and not added twice. Instrumented census, separate from quiet timings.'},indent=2));print(variant,[(x['phase'],x['wire_queries'],round(x['pfs_top_level_ms'],3)) for x in out])
