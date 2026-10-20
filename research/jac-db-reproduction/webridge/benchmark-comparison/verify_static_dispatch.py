"""Independently verify all emitted bounded cursor dispatch loops for IC1/IC13."""
import pathlib,json,re,hashlib
R=pathlib.Path(__file__).resolve().parent;W=R.parent;states=json.loads((W/'snb-extension/java/case-status.json').read_text());rows=[]
for q in ['ic1','ic13']:
 for variant in ['full','pruned']:
  recorded=next(x['selected_case']for x in states if x['query']==q and x['variant']==variant);case=W/recorded.split('/webridge/',1)[1];paths=list(case.glob('generated/sql/*/graph-SP-*ver0.sql'));assert len(paths)==1;p=paths[0];source=p.read_text();loops=[]
  for match in re.finditer(r'loop_(\d+): LOOP\n(.*?)END LOOP loop_\1;',source,re.S):
   k=match[1];body=match[2];indices=list(map(int,re.findall('IF cursor_cnt_'+k+r'=(\d+) THEN',body)));n=len(indices);assert indices==list(range(n));assert'IF cursor_cnt_'+k+'>='+str(n)+' THEN'in body;assert'SET cursor_cnt_'+k+' = cursor_cnt_'+k+' + 1;'in body;assert'SET cursor_cnt_'+k+' = 0;'in source[:match.start()];loops.append({'loop':int(k),'dispatch_branches':n,'full_cardinality_guard_evaluations':n*(n+1)})
  rows.append({'query':q,'variant':variant,'source':str(p.relative_to(W)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'loops':loops,'sum_guard_evaluations':sum(x['full_cardinality_guard_evaluations']for x in loops)})
assert sum(len(x['loops'])for x in rows)==12
(R/'static-dispatch-loops-verified.json').write_text(json.dumps({'status':'PASS','loop_count':12,'cases':rows,'scope':'Static generated dispatch at recorded result cardinalities; distinct from measured quiet time and instrumentation counters.'},indent=2));print('PASS 12 finite loops')
