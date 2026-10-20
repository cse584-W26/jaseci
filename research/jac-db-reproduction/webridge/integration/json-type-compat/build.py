#!/usr/bin/env python3
"""Rebuild isolated JSON dispatch aliases from pinned original source."""
import pathlib,subprocess,json,hashlib
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];W=H.parents[3]/'webridge/SourceCode/webridge-common/basic-components/src/main/java';names=['webridge/wbridge/storedprocedure/transformation/TypeConverter.java','webridge/wbridge/sql/types/SQLVarType.java'];paths=[];receipt={}
for name in names:
 p=W/name;s=p.read_text()
 if p.name=='TypeConverter.java':s=s.replace('SQL2JAVA_TYPE_CONVERSION.put("longtext", "longtext");','SQL2JAVA_TYPE_CONVERSION.put("longtext", "longtext");\n    SQL2JAVA_TYPE_CONVERSION.put("json", "longtext");')
 else:s=s.replace('public static SQLVarType of(String tp) {','public static SQLVarType of(String tp) {\n    if (tp.equalsIgnoreCase("JSON")) return SQLVarType.LONGTEXT;')
 target=H/'src'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(s);paths.append(target);receipt[name]={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'overlay_sha256':hashlib.sha256(s.encode()).hexdigest()}
c=H/'classes';c.mkdir(exist_ok=True);subprocess.run([str(B/'boot-jdk8/bin/javac'),'-d',str(c),*map(str,paths),str(H/'JSONTypeTest.java')],check=True)
with(H/'test.log').open('w')as f:subprocess.run([str(B/'boot-jdk8/bin/java'),'-cp',str(c),'JSONTypeTest'],stdout=f,stderr=subprocess.STDOUT,check=True)
(H/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
