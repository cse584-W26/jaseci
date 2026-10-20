#!/usr/bin/env python3
import pathlib,subprocess,importlib.util,hashlib,json,difflib
H=pathlib.Path(__file__).resolve().parent;I=H.parent;sp=importlib.util.spec_from_file_location('ctl',I/'control.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);sources={}
p=I/'sql-frontend/src/webridge/wbridge/sql/ast/SQLAstVisitor.java';a=p.read_text();b=a.replace('  private Pair<String,String> parameterType(SQLVariantRefExpr parameter) {','''  private java.util.List<String> recordedParameterJavaTypes=java.util.Collections.emptyList();
  public void setRecordedParameterJavaTypes(java.util.List<String> types){recordedParameterJavaTypes=new java.util.ArrayList<>(types);}
  private String recordedParameterSqlType(int index){
    if(index<0||index>=recordedParameterJavaTypes.size())return null;
    String t=recordedParameterJavaTypes.get(index);if(t==null)return null;
    if(t.equals("java/lang/String")||t.equals("java.lang.String"))return "VARCHAR(512)";
    if(t.equals("J"))return "BIGINT";if(t.equals("I")||t.equals("S")||t.equals("B"))return "INT";
    if(t.equals("Z"))return "BIT(1)";if(t.equals("F"))return "FLOAT";if(t.equals("D"))return "DOUBLE";return null;
  }
  private Pair<String,String> parameterType(SQLVariantRefExpr parameter) {''');b=b.replace('    throw new IllegalArgumentException("Cannot infer positional parameter "+parameter.getIndex());','''    String recorded=recordedParameterSqlType(parameter.getIndex());
    if(recorded!=null)return Pair.of(parameter.toString(),recorded);
    throw new IllegalArgumentException("Cannot infer positional parameter "+parameter.getIndex());''');sources['webridge/wbridge/sql/ast/SQLAstVisitor.java']=(p,a,b)
p=I/'numeric-width/src/webridge/wbridge/storedprocedure/StoredProcedureManager.java';a=p.read_text();b=a.replace('final SQLAstVisitor visitor = new SQLAstVisitor(SQLUtils.formatMySql(concreteSQL));','''final SQLAstVisitor visitor = new SQLAstVisitor(SQLUtils.formatMySql(concreteSQL));
        java.util.List<String> recordedJavaTypes = new java.util.ArrayList<>();
        for(int parameterIndex=0;parameterIndex<parameterExprsJSON.size();parameterIndex++)
          recordedJavaTypes.add(parameterExprsJSON.getJSONObject(parameterIndex).getString("_java_type"));
        visitor.setRecordedParameterJavaTypes(recordedJavaTypes);''');sources['webridge/wbridge/storedprocedure/StoredProcedureManager.java']=(p,a,b)
paths=[];receipt={}
for name,(p,a,b)in sources.items():
 target=H/'src'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(b);paths.append(target);receipt[name]={'base':str(p),'base_sha256':hashlib.sha256(a.encode()).hexdigest(),'overlay_sha256':hashlib.sha256(b.encode()).hexdigest()};(H/(p.stem+'.diff')).write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=str(p),tofile=name)))
classes=H/'classes';classes.mkdir(exist_ok=True);cp=':'.join([str(classes),str(I/'json-type-compat/classes'),str(I/'numeric-width/classes'),m.CP]);subprocess.run([str(m.B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(classes),*map(str,paths)],check=True);(H/'provenance.json').write_text(json.dumps(receipt,indent=2)+'\n')
