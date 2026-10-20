#!/usr/bin/env python3
"""Declare a source-level WeBridge body API without changing any request SQL."""
import difflib,hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent;source=R/'java/ReplayCompatibleAlignedIc5.java';s=source.read_text();renamed=s.replace('ReplayCompatibleAlignedIc5','RegionCompatibleAlignedIc5')
marker=' static Map<String,String> clientRootContext=new HashMap<>();'
addition='''
 public interface RegionBoundary {void enter(Connection c)throws Exception;void leave(Connection c)throws Exception;}
 static RegionBoundary regionBoundary=new RegionBoundary(){public void enter(Connection c){}public void leave(Connection c){}};
'''
assert renamed.count(marker)==1;renamed=renamed.replace(marker,marker+addition)
old='try{\n   Session s=new Session(c,root);';new='try{\n   regionBoundary.enter(c);\n   Session s=new Session(c,root);';assert renamed.count(old)==1;renamed=renamed.replace(old,new)
old='command(c,"commit","COMMIT");return';new='regionBoundary.leave(c);command(c,"commit","COMMIT");return';assert renamed.count(old)==1;renamed=renamed.replace(old,new)
p=R/'java/RegionCompatibleAlignedIc5.java';p.write_text(renamed)
(R/'region-compatibility.diff').write_text(''.join(difflib.unified_diff(s.splitlines(True),renamed.splitlines(True),fromfile=str(source),tofile=str(p))))
(R/'region-ledger.json').write_text(json.dumps(dict(source=str(source),source_sha256=hashlib.sha256(s.encode()).hexdigest(),derived=str(p),derived_sha256=hashlib.sha256(renamed.encode()).hexdigest(),region='After original SET SESSION statement, before original COMMIT; all original body code remains',default_hook='No-op; count/result gate runs this exact default',preserved_outside_region=['Identity resolution and process schema/type ensure','START TRANSACTION READ ONLY','SET SESSION innodb_lock_wait_timeout=10','COMMIT or original exception ROLLBACK'],changes_to_sql=[],changes_to_original_webridge_algorithms=[],automatic_whole_request_support=False),indent=2))
print(p)
