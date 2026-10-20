#!/usr/bin/env python3
import pathlib,subprocess,json,hashlib,shutil,difflib
R=pathlib.Path(__file__).resolve().parent;B=R.parents[1];W=B.parents[1]/'webridge';original=W/'SourceCode/webridge-common/basic-components/src/main/java/webridge/wbridge/storedprocedure/StoredProcedureManager.java';src=R/'src/webridge/wbridge/storedprocedure/StoredProcedureManager.java';src.parent.mkdir(parents=True,exist_ok=True)
a=original.read_text();needle='''            case "I":
            case "J":
            case "S":
              return new SymbolicInteger(expStr);''';replacement='''            case "I":
            case "S":
              return new SymbolicInteger(expStr);
            case "J":
              return new SymbolicInteger(expStr, Types.T_LONG);''';assert a.count(needle)==1;b=a.replace(needle,replacement);src.write_text(b);(R/'overlay.diff').write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=str(original),tofile=str(src))))
classes=R/'classes';shutil.copytree(R.parent/'sql-frontend/classes',classes,dirs_exist_ok=True);cp=':'.join(map(str,[classes,B/'deps/basic-components.jar',B/'deps/*']));cmd=['taskset','-c','9,19',str(B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(classes),str(src)];q=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE);(R/'build.stdout').write_bytes(q.stdout);(R/'build.stderr').write_bytes(q.stderr)
(R/'provenance.json').write_text(json.dumps(dict(original=str(original),original_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),overlay_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),change='Preserve native graph J symbol as typed Java long instead of default untyped integer',frontend_overlay=str(R.parent/'sql-frontend/provenance.json'),command=cmd,returncode=q.returncode),indent=2));assert q.returncode==0
rename_original=W/'SourceCode/webridge-common/basic-components/src/main/java/webridge/wbridge/graph/visit/impl/SQLGraphExpressionRenameVisitor.java'
rename_src=R/'src/webridge/wbridge/graph/visit/impl/SQLGraphExpressionRenameVisitor.java';rename_src.parent.mkdir(parents=True,exist_ok=True)
x=rename_original.read_text();assert x.count('new SymbolicInteger(newName);')==1
y=x.replace('new SymbolicInteger(newName);','new SymbolicInteger(newName, ((SymbolicInteger) oldExpression)._min, ((SymbolicInteger) oldExpression)._max, ((SymbolicInteger) oldExpression).getTypeCode());');rename_src.write_text(y)
(R/'rename-overlay.diff').write_text(''.join(difflib.unified_diff(x.splitlines(True),y.splitlines(True),fromfile=str(rename_original),tofile=str(rename_src))))
q=subprocess.run(['taskset','-c','9,19',str(B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(classes),str(rename_src)],stdout=subprocess.PIPE,stderr=subprocess.PIPE);(R/'rename-build.stderr').write_bytes(q.stderr);assert q.returncode==0
record=json.loads((R/'provenance.json').read_text());record['rename_original_sha256']=hashlib.sha256(rename_original.read_bytes()).hexdigest();record['rename_overlay_sha256']=hashlib.sha256(rename_src.read_bytes()).hexdigest();record['rename_change']='Preserve original symbolic integer typecode and bounds during alpha-renaming';(R/'provenance.json').write_text(json.dumps(record,indent=2))
