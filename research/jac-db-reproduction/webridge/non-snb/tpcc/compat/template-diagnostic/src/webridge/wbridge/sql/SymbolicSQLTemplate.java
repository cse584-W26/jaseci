package webridge.wbridge.sql;

import webridge.wbridge.hack.pc.PathConditionPruner;
import webridge.wbridge.sql.ast.SQLAstVisitor;
import webridge.wbridge.sql.types.SQLVarType;
import webridge.wbridge.sql.types.SqlType;
import webridge.wbridge.storedprocedure.BreakInfo;
import webridge.wbridge.storedprocedure.transformation.TypeConverter;
import webridge.wbridge.storedprocedure.utils.SQLPCUtil;
import webridge.wbridge.symbc.numeric.Expression;
import webridge.wbridge.symbc.numeric.PathCondition;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

public class SymbolicSQLTemplate implements Serializable, Cloneable, SymSQL {

  public static SymbolicSQLTemplate getTxnBeginSQLTemplate(int connId) {
    SymbolicSQLTemplate sqlTemplate =
        new SymbolicSQLTemplate(
            SqlType.DISABLE_AUTO_COMMIT,
            "set autocommit=0",
            Collections.emptyList(),
            Collections.emptyList(),
            Collections.emptyList(),
            Collections.emptyList(),
            Collections.emptyList(),
                new PathCondition());
    sqlTemplate.setConnNo(connId);
    return sqlTemplate;
  }

  public static SymbolicSQLTemplate getEnableAutoCommitSQLTemplate(int connId) {
    SymbolicSQLTemplate sqlTemplate =
        new SymbolicSQLTemplate(
            SqlType.ENABLE_AUTO_COMMIT,
            "set autocommit=1",
            Collections.emptyList(),
            Collections.emptyList(),
            Collections.emptyList(),
            Collections.emptyList(),
            Collections.emptyList(),
                new PathCondition());
    sqlTemplate.setConnNo(connId);
    return sqlTemplate;
  }

  public static SymbolicSQLTemplate getCommitSQLTemplate(int connId) {
    SymbolicSQLTemplate sqlTemplate =
        new SymbolicSQLTemplate(
            SqlType.COMMIT,
            "commit",
            Collections.emptyList(),
            Collections.emptyList(),
            Collections.emptyList(),
            Collections.emptyList(),
            Collections.emptyList(),
                new PathCondition());
    sqlTemplate.setConnNo(connId);
    return sqlTemplate;
  }

  private int sqlNo = -1;
  private int connNo = -1;
  private String rowCountVarName;
  private BreakInfo nonDeterministic = BreakInfo.NOT_BREAK;
  private int writeSqlConcreteRetCnt;

  private final SqlType sqlType;
  private final String sqlTemplate;
  private final List<String> retValJavaTypes;
  private final List<SQLVarType> retValSqlTypes;
  private final List<String> retValNames; // names in the sql statement
  private final List<String> retValAlias; // alias in the sql statement
  private final List<List<String>> retSymbolicNames =
      new ArrayList<>(); // returned symbolic variable names of multiple rows

  private final List<String> concreteParameters;
  private final List<String> parameterExprs;
  private final List<Expression> parameterSymbolics;
  private final List<String> parameterJavaTypes;
  private final List<SQLVarType> paramSqlTypes;
  private String pathConditionStr;
  private PathCondition pc;
  // contains the mapping from offset of setParamExpr to index in parameterExprs
  private final List<Integer> placeHolderMapping;

  public void setPathConditionStr(String pathConditionStr) {
    this.pathConditionStr = pathConditionStr;
  }

  public void setPc(PathCondition pc) {
    this.pc = pc;
  }

  public SymbolicSQLTemplate(
      SqlType sqlType,
      String sqlTemplate,
      List<String> retValTypes,
      List<String> retValNames,
      List<String> retValAlias,
      List<String> parameterExprs,
      List<String> parameterTypes,
      PathCondition pc) {
    this.sqlType = sqlType;
    this.sqlTemplate = sqlTemplate.replace("\n", " ").replace("\t", "");
    this.retValJavaTypes =
        retValTypes.stream()
            .map(TypeConverter::removeTypeBrackets)
            .map(TypeConverter::SQLToJava)
            .collect(Collectors.toList());
    this.retValSqlTypes =
        retValTypes.stream()
            .map(TypeConverter::removeTypeBrackets)
            .map(SQLVarType::of)
            .collect(Collectors.toList());
    this.retValNames = new ArrayList<>(retValNames);
    this.retValAlias = new ArrayList<>(retValAlias);
    this.parameterExprs = new ArrayList<>(parameterExprs);
    this.parameterSymbolics = new ArrayList<>();
    for (int i = 0; i < parameterExprs.size(); ++i) parameterSymbolics.add(null);
    this.concreteParameters = new ArrayList<>(parameterExprs);
    this.parameterJavaTypes =
        parameterTypes.stream().map(TypeConverter::SQLToJava).collect(Collectors.toList());
    this.paramSqlTypes = parameterTypes.stream().map(SQLVarType::of).collect(Collectors.toList());
    this.pc = PathConditionPruner.prunePcByRules(pc.computeNoRedundantPC());
    this.pathConditionStr = SQLPCUtil.simplifyPathCondition(this.pc);
    this.placeHolderMapping = new ArrayList<>();
    IntStream.range(0, parameterExprs.size())
        .forEach(
            idx -> {
              if (parameterExprs.get(idx).equals(SQLAstVisitor.PLACE_HOLDER)) {
                placeHolderMapping.add(idx);
              }
            });
  }

  public void setParamExprAt(int offset, String value) {
    assert offset < placeHolderMapping.size() && offset >= 0;
    parameterExprs.set(placeHolderMapping.get(offset), value);
  }

  public void setParamSymbolicAt(int offset, Object attr) {
    assert offset < placeHolderMapping.size() && offset >= 0;
    if (attr == null) {
      this.parameterSymbolics.set(offset, null);
      return;
    }
    assert attr instanceof Expression;
    this.parameterSymbolics.set(offset, (Expression) attr);
  }

  public void setConcreteParamAt(int offset, String value) {
    assert offset < placeHolderMapping.size() && offset >= 0;
    assert !value.equalsIgnoreCase("true") && !value.equalsIgnoreCase("false")
        : "check check whether the type information is correct";
    concreteParameters.set(placeHolderMapping.get(offset), value);
  }

  public void setSqlNo(int sqlNo) {
    assert this.sqlNo == -1;
    this.sqlNo = sqlNo;
  }

  public int getSqlNo() {
    return sqlNo;
  }

  public int getConnNo() {
    return connNo;
  }

  public void setConnNo(int connNo) {
//    assert this.connNo == -1;
    this.connNo = connNo;
  }

  @Override
  public String getConcreteSql() {
    try { return String.format(sqlTemplate.replace("?", "%s"), concreteParameters.toArray()); } catch (java.util.MissingFormatArgumentException e) { System.err.println("TEMPLATE_DIAGNOSTIC sql="+sqlTemplate+" concrete="+concreteParameters+" symbolic="+parameterExprs); throw e; }
  }

  @Override
  public String getSqlTemplate() {
    return sqlTemplate;
  }

  @Override
  public List<String> getParameterExprs() {
    return parameterExprs;
  }

  @Override
  public List<SQLVarType> getParameterTypes() {
    return paramSqlTypes;
  }

  public String getPathConditionStr() {
    return pathConditionStr;
  }

  @Override
  public List<SQLVarType> getRetValTypes() {
    return retValSqlTypes;
  }

  @Override
  public List<String> getRetValNames() {
    return Collections.unmodifiableList(retValNames);
  }

  @Override
  public List<String> getRetValAlias() {
    return Collections.unmodifiableList(retValAlias);
  }

  public void setRetValName(String name, int idx) {
    retValNames.set(idx, name);
  }

  @Override
  public List<List<String>> getRetSymbolicNames() {
    return Collections.unmodifiableList(retSymbolicNames);
  }

  public void addRetSymbolicNames(List<String> retSymNames) {
    retSymbolicNames.add(retSymNames);
  }

  @Override
  public SqlType getSqlType() {
    return sqlType;
  }

  public List<Expression> getParameterSymbolics() {
    return parameterSymbolics;
  }

  @Override
  public String getRowCountVarName() {
    return rowCountVarName;
  }

  public List<SQLVarType> getParamSqlTypes() {
    return paramSqlTypes;
  }

  public List<String> getParameterJavaTypes() {
    return parameterJavaTypes;
  }

  public void setRowCountVarName(String rowCountVarName) {
    this.rowCountVarName = rowCountVarName;
  }

  public PathCondition getOriginalPc() {
    return pc;
  }

  public boolean isNonDeterministic() {
    return nonDeterministic.equals(BreakInfo.ND_FUNC_IN_PARAM)
        || nonDeterministic.equals(BreakInfo.ND_FUNC_IN_PC);
  }

  public BreakInfo nonDeterministicType() {
    return nonDeterministic;
  }

  public void setNonDeterministic(BreakInfo nonDeterministic) {
    this.nonDeterministic = nonDeterministic;
  }

  public void setWriteSqlConcreteRetCnt(int writeSqlConcreteRetCnt) {
    this.writeSqlConcreteRetCnt = writeSqlConcreteRetCnt;
  }

  public int getWriteSqlConcreteRetCnt() {
    return writeSqlConcreteRetCnt;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;
    SymbolicSQLTemplate that = (SymbolicSQLTemplate) o;
    return sqlTemplate.equals(that.sqlTemplate) && pathConditionStr.equals(that.pathConditionStr);
  }

  @Override
  public int hashCode() {
    return Objects.hash(sqlTemplate, pathConditionStr);
  }

  @Override
  public String toString() {
    final StringBuilder paramPrintStr = new StringBuilder();
    printOutLst(paramPrintStr, parameterExprs, parameterJavaTypes);

    final StringBuilder retValsPrintStr = new StringBuilder();
    printOutLst(retValsPrintStr, retValNames, retValJavaTypes);

    return "SymbolicSQLTemplate {\n"
        + "    sqlNo="
        + sqlNo
        + ",\n    sqlTemplate='"
        + sqlTemplate
        + '\''
        + ",\n    concreteSql='"
        + getConcreteSql()
        + '\''
        + ",\n    retVals="
        + retValsPrintStr
        + ",\n    parameters="
        + paramPrintStr
        + ",\n    path_condition='"
        + pathConditionStr
        + '\''
        + "\n}\n";
  }

  private void printOutLst(StringBuilder printStr, List<String> names, List<String> types) {
    printStr.append("{");
    for (int i = 0; i < names.size(); i++) {
      final String retValName = names.get(i);
      final String retValTp = types.get(i);
      printStr.append(retValName).append(":").append(retValTp);
      if (i != names.size() - 1) printStr.append(", ");
    }
    printStr.append("}");
  }
}
