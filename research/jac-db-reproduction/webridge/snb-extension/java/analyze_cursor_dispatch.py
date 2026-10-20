#!/usr/bin/env python3
"""Extract actual emitted finite cursor-dispatch bounds; no latency estimates."""
import hashlib,json,pathlib,re
H=pathlib.Path(__file__).resolve().parent;E=H.parent;cases=json.loads((H/'case-status.json').read_text());out=[]
for case in cases:
 root=pathlib.Path(case['selected_case'])if case.get('selected_case')else None
 if not root:continue
 for p in root.glob('generated/sql/*/graph-SP-*_sp_*.sql'):
  s=p.read_text();loops=[]
  for m in re.finditer(r'loop_(\d+): LOOP(.*?)END LOOP loop_\1;',s,re.S):
   n=m[1];body=m[2];values=[int(x)for x in re.findall(r'IF cursor_cnt_'+n+r'=(\d+) THEN',body)];bound=re.findall(r'IF cursor_cnt_'+n+r'>=(\d+) THEN',body);increments=re.findall(r'SET cursor_cnt_'+n+r' = cursor_cnt_'+n+r' \+ 1;',body);leaves=re.findall(r'LEAVE loop_'+n+';',body);N=max(values)+1 if values else 0
   loops.append({'loop':int(n),'start_line':s.count('\n',0,m.start())+1,'independent_row_equality_branches':len(values),'capture_rows':N,'explicit_exit_bounds':list(map(int,bound)),'counter_increment_present':bool(increments),'leave_present':bool(leaves),'full_captured_result_equality_checks':N*(N+1)if len(values)==N and int(bound[0])==N and increments and leaves else None})
  out.append({'query':case['query'],'variant':case['variant'],'case':str(root),'sql_path':str(p),'sql_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sql_bytes':p.stat().st_size,'loops':loops,'total_full_result_equality_checks':sum(x['full_captured_result_equality_checks']or 0 for x in loops),'interpretation':'Independent IF dispatch tests all row indices on every cursor iteration; finite counter increment/exit retained. Counts are generated control tests, not distinct data rows or a latency prediction.'})
(H/'cursor-dispatch-analysis.json').write_text(json.dumps(out,indent=2));print(json.dumps([{k:r[k]for k in ['query','variant','total_full_result_equality_checks']}for r in out],indent=2))
