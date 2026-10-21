#!/usr/bin/env python3
"""Isolated DML positional-parameter metadata repair; business SQL remains unchanged."""
import pathlib,hashlib,json,difflib,sys,subprocess,importlib.util,time
H=pathlib.Path(__file__).resolve().parent;L=H.parents[1];W=L.parents[1];I=W/'integration';s=importlib.util.spec_from_file_location('c',I/'control.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c);sys.path.insert(0,str(L.parent));from measurement_lease import lease
base=I/'recorded-bind-types/src/webridge/wbridge/sql/ast/SQLAstVisitor.java';old=base.read_text();text=old
for kind,nextmethod,typ in [('Delete','  @Override\n  public void endVisit(MySqlInsertStatement x)','DELETE'),('Insert','  private void handleInsertItem(','INSERT'),('Update','  private void handleUpdateSetItem(','UPDATE')]:
 start=text.index('  @Override\n  public void endVisit(MySql'+kind+'Statement x)');end=text.index(nextmethod,start)
 text=text[:start]+'''  @Override
  public void endVisit(MySqlKINDStatement x) {
    super.endVisit(x);
    registerDmlParameters(x, SqlType.TYPE);
  }

'''.replace('KIND',kind).replace('TYPE',typ)+text[end:]
# A SELECT nested in INSERT supplies no JDBC ResultSet of its own.
text=text.replace('    super.endVisit(statement);\n    retValNameTypeMap.clear();','    super.endVisit(statement);\n    for(SQLObject parent=statement.getParent();parent!=null;parent=parent.getParent())if(parent instanceof SQLInsertStatement)return;\n    retValNameTypeMap.clear();')
helper='''
  private String dmlColumnType(SQLExpr expression) {
    SQLColumnDefinition column=null;
    if(expression instanceof SQLIdentifierExpr)column=((SQLIdentifierExpr)expression).getResolvedColumn();
    if(expression instanceof SQLPropertyExpr)column=((SQLPropertyExpr)expression).getResolvedColumn();
    if(column==null)return null;
    String type=normalType(column.getDataType().toString());
    if(type.equalsIgnoreCase("NUMERIC"))return "DECIMAL";
    if(type.toUpperCase().startsWith("NUMERIC("))return "DECIMAL"+type.substring(7);
    return type;
  }
  private String dmlParameterType(SQLVariantRefExpr parameter) {
    for(SQLObject parent=parameter.getParent();parent!=null;parent=parent.getParent()) {
      if(parent instanceof SQLUpdateSetItem){String t=dmlColumnType(((SQLUpdateSetItem)parent).getColumn());if(t!=null)return t;}
      if(parent instanceof SQLBinaryOpExpr){SQLBinaryOpExpr b=(SQLBinaryOpExpr)parent;if(b.getOperator()==SQLBinaryOperator.BooleanAnd||b.getOperator()==SQLBinaryOperator.BooleanOr)continue;String t=dmlColumnType(contains(b.getLeft(),parameter)?b.getRight():b.getLeft());if(t!=null)return t;}
      if(parent instanceof SQLInsertStatement.ValuesClause){SQLInsertStatement.ValuesClause v=(SQLInsertStatement.ValuesClause)parent;SQLObject owner=parent.getParent();if(owner instanceof SQLInsertStatement){List<SQLExpr>cols=((SQLInsertStatement)owner).getColumns();for(int i=0;i<v.getValues().size()&&i<cols.size();i++)if(contains(v.getValues().get(i),parameter)){String t=dmlColumnType(cols.get(i));if(t!=null)return t;}}}
    }
    String recorded=recordedParameterSqlType(parameter.getIndex());
    if(recorded==null)throw new IllegalArgumentException("DML parameter requires resolved column or recorded JDBC type: "+parameter.getIndex());
    // JDBC String has no 512-character limit. LONGTEXT preserves JSON/long content.
    return recorded.equals("VARCHAR(512)")?"LONGTEXT":recorded;
  }
  private void registerDmlParameters(SQLStatement statement,SqlType kind) {
    argExprLst.clear();argTypeLst.clear();argParentExprLst.clear();retValNameTypeMap.clear();retValNameAliasMap.clear();
    final TreeMap<Integer,SQLVariantRefExpr> ordered=new TreeMap<>();
    statement.accept(new com.alibaba.druid.sql.dialect.mysql.visitor.MySqlASTVisitorAdapter(){@Override public boolean visit(SQLVariantRefExpr p){if(!PLACE_HOLDER.equals(p.getName()))return true;if(p.getIndex()<0||ordered.put(p.getIndex(),p)!=null)throw new IllegalArgumentException("Nonunique DML placeholder index");return true;}});
    int expected=0;for(Map.Entry<Integer,SQLVariantRefExpr>entry:ordered.entrySet()){if(entry.getKey()!=expected++)throw new IllegalArgumentException("Noncontiguous DML placeholder index");SQLVariantRefExpr p=entry.getValue();argExprLst.add(Pair.of("parameter_"+p.getIndex(),PLACE_HOLDER));argTypeLst.add(SQLVarType.of(dmlParameterType(p)));}
    sqlType=kind;
  }
'''
text=text.replace('  private String normalType(String type) {',helper+'\n  private String normalType(String type) {');digest=hashlib.sha256(text.encode()).hexdigest();out=H/digest;out.mkdir(exist_ok=True);src=out/'src/webridge/wbridge/sql/ast/SQLAstVisitor.java';src.parent.mkdir(parents=True,exist_ok=True)
if src.exists():assert src.read_text()==text
else:src.write_text(text)
(out/'overlay.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile=str(base),tofile=str(src))));(out/'provenance.json').write_text(json.dumps({'base':str(base),'base_sha256':hashlib.sha256(old.encode()).hexdigest(),'overlay_sha256':digest,'scope':'DML ordered parameter metadata and nested INSERT SELECT result scope; SQL AST unchanged; recorded JDBC type fallback'},indent=2)+'\n');classes=out/'classes';classes.mkdir(exist_ok=True);cp=str(classes)+':'+str(I/'recorded-bind-types/classes')+':'+c.CP
with lease('littlex isolated DML frontend build/test',out/('build-'+str(time.time_ns())+'.lease.json')):
 cmd=['taskset','-c','9,19',str(c.B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(classes),str(src),str(H/'DmlTest.java')];r=subprocess.run(cmd,capture_output=True);(out/'build.stdout').write_bytes(r.stdout);(out/'build.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr.decode()
 cmd=['taskset','-c','9,19',str(c.SERVER/'bin/java'),'-cp',cp,'DmlTest',str(L/'fixtures/t20/mysql-schema.sql'),str(out/'tests.json')];r=subprocess.run(cmd,capture_output=True);(out/'test.stdout').write_bytes(r.stdout);(out/'test.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr.decode()
 (out/'class-sha256.json').write_text(json.dumps({str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest()for f in classes.rglob('*.class')},indent=2))
print(out)
