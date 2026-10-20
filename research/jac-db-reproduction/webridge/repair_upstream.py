"""Apply narrowly scoped compatibility repairs to the pinned public artifact."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2]/'webridge'
fixes={
'SourceCode/openjdk8-webridge/hotspot/src/share/vm/concolic/jdbc/reference/symbolicStatement.cpp':('webridge/sql/ResultSetHolder','webridge/wbridge/sql/ResultSetHolder'),
'SourceCode/openjdk8-webridge/hotspot/src/share/vm/concolic/jdbc/reference/symbolicResultSet.cpp':('webridge/sql/result/MultipleRowResultSetImpl','webridge/wbridge/sql/result/MultipleRowResultSetImpl'),
'SourceCode/openjdk8-webridge/hotspot/src/share/vm/webridge/pathCondition/pathConditionPruner.cpp':('webridge/storedprocedure/invocation/SPInvokeManager','webridge/wbridge/storedprocedure/invocation/SPInvokeManager'),
'Application/my-blog/src/main/java/com/site/blog/my/core/controller/blog/MyBlogController.java':('import webridge.storedprocedure.invocation.SPInvokeManager;','import webridge.wbridge.storedprocedure.invocation.SPInvokeManager;'),
'Application/my-blog/src/main/java/com/site/blog/my/core/controller/admin/BlogController.java':('import webridge.storedprocedure.invocation.SPInvokeManager;','import webridge.wbridge.storedprocedure.invocation.SPInvokeManager;')}
receipts=[]
for rel,(old,new) in fixes.items():
 p=R/rel;s=p.read_text()
 if old in s:s=s.replace(old,new);p.write_text(s)
 elif new not in s:raise RuntimeError('Unexpected upstream source: '+rel)
 receipts.append({'path':rel,'old':old,'new':new,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(Path(__file__).resolve().parent/'upstream-repairs.json').write_text(json.dumps(receipts,indent=2)+'\n')
