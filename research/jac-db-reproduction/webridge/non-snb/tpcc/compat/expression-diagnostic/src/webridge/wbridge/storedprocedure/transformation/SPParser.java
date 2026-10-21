package webridge.wbridge.storedprocedure.transformation;

import static webridge.wbridge.graph.processor.utils.CommonPcExtractor.*;
import static webridge.wbridge.graph.processor.utils.CommonPcExtractor.commonPcVarDeclareStatement;

import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.google.common.base.Joiner;
import webridge.wbridge.graph.processor.utils.CommonPcExtractor;
import webridge.wbridge.hack.pc.BigDecimalHandler;
import webridge.wbridge.sql.types.SQLVarType;
import webridge.wbridge.sql.types.SqlType;
import webridge.wbridge.storedprocedure.SPConfig;
import webridge.wbridge.storedprocedure.SPContext;
import webridge.wbridge.storedprocedure.utils.SQLPCUtil;
import webridge.wbridge.symbc.numeric.PathCondition;
import webridge.wbridge.symbc.numeric.SymbolicPlaceHolder;
import java.util.*;
import java.util.regex.Matcher;
import java.util.stream.Collectors;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.tuple.Pair;

public class SPParser {

  private static final String PARAMETER_CODE_TEMPLATE =
      "class MAIN { void METHOD() { TARGET = %s; }}";
  private static final String PC_CODE_TEMPLATE = "class MAIN { void METHOD() { if (%s) {}}}";

  private static final String SP_TEMPLATE =
      "DROP PROCEDURE IF EXISTS `%s`;\n"
          + "DELIMITER $$\nCREATE PROCEDURE %s (%s)\n" // parameters
          + "BEGIN\n\n"
          + "%s\n" // declaration
          + "%s" // sql statements
          + "END $$\nDELIMITER ;";
  private static final String DELIMITER = ";\n";
  private static final String INPUT_TEMPLATE = "IN %s %s, ";
  private static final String DECLARE_TEMPLATE = "DECLARE %s %s DEFAULT NULL;\n";
  private static final String DECLARE_TEMPLATE_WITH_DEFAULT = "DECLARE %s %s DEFAULT %s;\n";
  private static final String DEFINE_TEMPLATE = "SET %s = %s;\n";
  private static final String UPDATE_ROW_COUNT_TEMPLATE = "SET %s = ROW_COUNT();\n";
  private static final String SELECT_ROW_COUNT_TEMPLATE = "SET %s = FOUND_ROWS();\n";
  private static final String SAVEPOINT_TEMPLATE = "SAVEPOINT %s;\n";
  private static final String IF_TEMPLATE = "IF %s " + "THEN\n" + "%s" + "END IF;\n";
  private static final String CURSOR_TEMPLATE =
      "SET %s = 0;\n" // indicator
          + "SET %s = 0;\n" // counter
          + "BEGIN\n" // counter
          + "DECLARE %s CURSOR FOR %s;\n"
          + "DECLARE CONTINUE HANDLER FOR NOT FOUND SET %s = 1;\n"
          + "OPEN %s;\n"
          + "%s: LOOP\n"
          + "%s"
          + "IF %s=1 THEN CLOSE %s; LEAVE %s; END IF;\n"
          + "SET %s = %s + 1;\n"
          + "%s"
          + "END LOOP %s;\n"
          + "END;\n"
          + "SET %s = FOUND_ROWS();\n"
          + "SELECT %s;\n" // query the flatten result set
          + "SET %s = %s;\n";
  private static final String QUERY_ID_TEMPLATE = "QUERY_ID_%d";
  private static final String TXN_CONTROL_QUERY_ID_TEMPLATE = "QUERY_ID_%d_TXN";
  private static final String SET_QUERY_ID_TEMPLATE = "SET " + QUERY_ID_TEMPLATE + " = %d;\n";
  private static final String SET_TXN_CONTROL_QUERY_ID_TEMPLATE =
      "SET " + TXN_CONTROL_QUERY_ID_TEMPLATE + " = %d;\n";

  private static String assembleCursorSql(
      String cursorName,
      String indicatorName,
      String counterName,
      String selectStm,
      String loopName,
      String loopBodyBefore,
      String loopBodyAfter,
      String rowCountVarName,
      List<String> retVarNameList) {
    return String.format(
        CURSOR_TEMPLATE,
        indicatorName,
        counterName,
        cursorName,
        selectStm,
        indicatorName,
        cursorName,
        loopName,
        loopBodyBefore,
        indicatorName,
        cursorName,
        loopName,
        counterName,
        counterName,
        loopBodyAfter,
        loopName,
        counterName,
        Joiner.on(",").join(retVarNameList),
        rowCountVarName,
        counterName);
  }

  static class SingleParsedSQLInfo {
    SingleParsedSQLInfo() {
      this.declareStatements = new ArrayList<>();
      this.preDefineStatementsBeforePcCheck = new ArrayList<>();
      this.preDefineStatementsAfterPcCheck = new ArrayList<>();
      this.sqlStatements = new ArrayList<>();
      this.debugSqlStatements = new ArrayList<>();
      this.postDefineStatements = new ArrayList<>();
      this.inputVars = new ArrayList<>();
      this.preCondition = null;
      this.condition = null;
    }

    List<String> declareStatements;
    List<String> preDefineStatementsAfterPcCheck;
    List<String> preDefineStatementsBeforePcCheck;
    List<String> sqlStatements;
    List<String> debugSqlStatements;
    List<String> inputVars;
    List<String> postDefineStatements; // define statements after execution of sql
    String preCondition; // added during sp generation
    String condition; // converted from path condition
  }

  public static String getStoredProcedureStatement(String spName, SPContext SpCtx) {
    final SPMetaInfo spInfo = SPMetaInfoBuilder.of(SpCtx).build();
    if (spInfo.sqlInfos.isEmpty()) return null;
    return new SPParser(spName, spInfo).parseToStoredProcedure();
  }

  private final String spName;
  private final SPMetaInfo spInfo;
  private final Map<String, SQLVarType>
      allDeclaredVar; // all declared vars. used to validate correctness

  private final StringBuilder inputBuilder;
  private final StringBuilder declareBuilder;
  private final StringBuilder sqlBlockBuilder;

  private SPParser(String spName, SPMetaInfo spInfo) {
    this.spName = spName;
    this.spInfo = spInfo;
    this.allDeclaredVar = new HashMap<>();
    this.inputBuilder = new StringBuilder();
    this.declareBuilder = new StringBuilder();
    this.sqlBlockBuilder = new StringBuilder();
  }

  public String parseToStoredProcedure() {
    // 0. build input parameters
    buildInputStatement();
    allDeclaredVar.putAll(spInfo.spInputVariable);

    // 1. premised variables
    spInfo.premisedVariables.forEach(
        varMeta -> {
          declareBuilder.append(String.format(DECLARE_TEMPLATE, varMeta.varName, varMeta.varType));
          sqlBlockBuilder.append(
              String.format(
                  DEFINE_TEMPLATE, varMeta.varName, parseParamExprToSqlSyntax(varMeta.remark)));
        });

    // 2. parse each sql statements
    List<SingleParsedSQLInfo> parsedSQLInfos = new ArrayList<>();
    spInfo.sqlInfos.forEach(s -> parsedSQLInfos.add(parseSingleSql(s, spInfo)));

    // 3. declare statements of all SQLs
    final Set<String> declaredStmts = new HashSet<>();
    parsedSQLInfos.forEach(
        parsedSql ->
            parsedSql.declareStatements.forEach(
                s -> {
                  if (declaredStmts.contains(s)) return;
                  declareBuilder.append(s);
                  declaredStmts.add(s);
                }));

    // 4. construct sql blocks (define + sql + post define)
    constructSqlBlocks(parsedSQLInfos);

    // 5. construct sql parameter selection
    final List<String> parametersAndQueryId = new ArrayList<>();
    parsedSQLInfos.forEach(parsedSql -> parametersAndQueryId.addAll(parsedSql.inputVars));
    if (!parametersAndQueryId.isEmpty()) {
      sqlBlockBuilder
          .append(String.format("SELECT %s", Joiner.on(",").join(parametersAndQueryId)))
          .append(DELIMITER)
          .append("\n");
    }

    return String.format(
        SP_TEMPLATE,
        spName,
        spName,
        inputBuilder.toString(),
        declareBuilder.toString(),
        sqlBlockBuilder.toString());
  }

  // returns false if error
  private static boolean recordNestingInnerPc(
      List<Pair<String, String>> pcAndNestedPc, String pathCondition) {
    if (pcAndNestedPc.isEmpty()) {
      pcAndNestedPc.add(Pair.of(pathCondition, pathCondition));
    }

    final Pair<String, String> lastLevelPcPair = pcAndNestedPc.get(pcAndNestedPc.size() - 1);
    // same pc
    if (lastLevelPcPair.getKey().equalsIgnoreCase(pathCondition)) return true;

    if (!isPrefixPc(pathCondition, lastLevelPcPair.getKey())) return false;

    // add +2 offset to skip &&
    pcAndNestedPc.add(
        Pair.of(pathCondition, removePrefix(pathCondition, lastLevelPcPair.getKey())));

    return true;
  }

  private static String removePrefix(String pcLong, String pcShort) {
    final String[] pcLongSplit = pcLong.split("&&");
    final String[] pcShortSpilt = pcShort.split("&&");
    final List<String> remainingPc = new ArrayList<>();
    for (String longPcElement : pcLongSplit) {
      boolean match = false;
      for (String shortPcElement : pcShortSpilt) {
        if (shortPcElement.equalsIgnoreCase(longPcElement)) {
          match = true;
          break;
        }
      }
      if (!match) remainingPc.add(longPcElement);
    }
    return Joiner.on("&&").join(remainingPc);
  }

  private static boolean isPrefixPc(String pcLong, String pcShort) {
    if (pcLong.equalsIgnoreCase(pcShort)) return true;
    final String[] splits = pcShort.split("&&");
    for (String split : splits) {
      if (!pcLong.contains(split)) return false;
    }
    return true;
  }

  public void constructSqlBlocks(List<SingleParsedSQLInfo> parsedSQLInfos) {
    parsedSQLInfos.forEach(rootSqlInfo -> sqlBlockBuilder.append(printSQL(rootSqlInfo)));
  }

  public String printSQL(SingleParsedSQLInfo sqlInfo) {
    // 1. add condition
    final String condition = sqlInfo.condition;

    // 2. construct sqlstr (preDefine + sql + postDefine)
    final StringBuilder thisSqlStrBuilder = new StringBuilder();
    sqlInfo.preDefineStatementsAfterPcCheck.forEach(thisSqlStrBuilder::append);
    sqlInfo.sqlStatements.forEach(thisSqlStrBuilder::append);
    sqlInfo.postDefineStatements.forEach(thisSqlStrBuilder::append);
    final String thisSqlStr = thisSqlStrBuilder.toString();
    // 3. path condition debug info
    final StringBuilder debugSqlStrBuilder = new StringBuilder();
    sqlInfo.debugSqlStatements.forEach(debugSqlStrBuilder::append);
    final String debugSqlStr = debugSqlStrBuilder.toString();

    // 4. add precondition
    final String sqlWithPrePc =
        (StringUtils.isEmpty(sqlInfo.preCondition)
            ? thisSqlStr
            : String.format(IF_TEMPLATE, sqlInfo.preCondition, thisSqlStr));

    // 5. wrap with pre-defined statement before pc check
    final StringBuilder preDefStmtsBuilder = new StringBuilder();
    sqlInfo.preDefineStatementsBeforePcCheck.forEach(preDefStmtsBuilder::append);

    return debugSqlStr
        + (sqlInfo.preDefineStatementsBeforePcCheck.isEmpty() ? "" : preDefStmtsBuilder.toString())
        + (condition.isEmpty()
            ? sqlWithPrePc
            : String.format(IF_TEMPLATE, condition, sqlWithPrePc));
  }

  private static boolean containsNonTrivialPc(SingleParsedSQLInfo parsedSql) {
    return !StringUtils.isEmpty(parsedSql.condition)
        && !parsedSql.condition.equalsIgnoreCase("TRUE");
  }

  private void buildInputStatement() {
    spInfo.spInputVariable.forEach(
        (k, v) -> inputBuilder.append(String.format(INPUT_TEMPLATE, k, v)));
    if (inputBuilder.length() > 0) { // remove tail ', '
      inputBuilder.delete(inputBuilder.length() - 2, inputBuilder.length());
    }
  }

  private SingleParsedSQLInfo parseSingleSql(SQLMetaInfo sqlMetaInfo, SPMetaInfo spMetaInfo) {
    final SingleParsedSQLInfo parsedSQLInfo = new SingleParsedSQLInfo();
    final List<String> inputVars = new ArrayList<>();
    final List<String> outputVars = new ArrayList<>();

    // 0. some prologue variables
    parseAuxVars(
        parsedSQLInfo, sqlMetaInfo.prologueVars, parsedSQLInfo.preDefineStatementsAfterPcCheck);

    // 1. declare and define all input variable
    resolveInputVars(sqlMetaInfo, parsedSQLInfo, inputVars);
    // 1.1 declare query id
    resolveQueryId(sqlMetaInfo, parsedSQLInfo);

    // 2. find all output variables that need declare
    resolveOutputVarsToDeclare(sqlMetaInfo, parsedSQLInfo, outputVars);

    // 3. conditions
    // 3.1 parse path condition
    parsePathCondition(spMetaInfo, sqlMetaInfo, parsedSQLInfo);

    // 3.2 precondition (e.g., result #rows related)
    parsePreCondition(sqlMetaInfo, parsedSQLInfo);

    // 4. build sql blocks
    // 4.1 set the query index to not-null value to indicate whether the query is executed
    parseSetQueryId(sqlMetaInfo, parsedSQLInfo, inputVars);

    // 4.2 core sql
    parseCoreSql(sqlMetaInfo, parsedSQLInfo, inputVars);

    // 5. some epilogue variables
    parseAuxVars(parsedSQLInfo, sqlMetaInfo.epilogueVars, parsedSQLInfo.postDefineStatements);

    // 6. function invocation result variables
    handleFunctionInvocationResult(sqlMetaInfo, parsedSQLInfo);

    return parsedSQLInfo;
  }

  private void parseAuxVars(
      SingleParsedSQLInfo parsedSQLInfo,
      List<VarMetaInfo> prologueVars,
      List<String> definitionStatements) {
    prologueVars.forEach(
        varMeta -> {
          String vExpr = varMeta.remark;
          parsedSQLInfo.declareStatements.add(
              String.format(DECLARE_TEMPLATE, varMeta.varName, varMeta.varType));
          definitionStatements.add(String.format(DEFINE_TEMPLATE, varMeta.varName, vExpr));
        });
  }

  private void resolveInputVars(
      SQLMetaInfo sqlMetaInfo, SingleParsedSQLInfo parsedSQLInfo, List<String> inputVars) {
    sqlMetaInfo.parameters.forEach(
        varMeta -> {
          String vName = varMeta.varName, vExpr = varMeta.remark;
          SQLVarType vType = varMeta.varType;
          if (allDeclaredVar.put(vName, vType) != null) {
            throw new RuntimeException("Duplicate variable name!" + vName + " :" + vType);
          }
          parsedSQLInfo.declareStatements.add(String.format(DECLARE_TEMPLATE, vName, vType));
          inputVars.add(vName);

          // initialize those input variable with input expression
          parsedSQLInfo.preDefineStatementsAfterPcCheck.add(
              String.format(DEFINE_TEMPLATE, vName, parseParamExprToSqlSyntax(vExpr)));
        });
  }

  private void resolveQueryId(SQLMetaInfo sqlMetaInfo, SingleParsedSQLInfo parsedSQLInfo) {
    if (sqlMetaInfo.sqlIdx != -1) {
      // -1 indicates a commit sql
      final String queryIdVar =
          sqlMetaInfo.sqlType.isTxnControl()
              ? String.format(TXN_CONTROL_QUERY_ID_TEMPLATE, sqlMetaInfo.sqlIdx)
              : String.format(QUERY_ID_TEMPLATE, sqlMetaInfo.sqlIdx);
      if (allDeclaredVar.put(queryIdVar, SQLVarType.INT) != null) {
        throw new RuntimeException("Duplicate variable name!" + queryIdVar + " :int");
      }
      parsedSQLInfo.declareStatements.add(
          String.format(DECLARE_TEMPLATE, queryIdVar, SQLVarType.INT));
    }
  }

  private void resolveOutputVarsToDeclare(
      SQLMetaInfo sqlMetaInfo, SingleParsedSQLInfo parsedSQLInfo, List<String> outputVars) {
    if (!sqlMetaInfo.dependedUpdates.isEmpty() || !sqlMetaInfo.dependedSelects.isEmpty()) {
      sqlMetaInfo.returnValues.forEach(
          varMetaInfos ->
              varMetaInfos.forEach(
                  varMeta -> {
                    if (allDeclaredVar.put(varMeta.varName, varMeta.varType) != null) {
                      throw new RuntimeException(
                          "Duplicate variable name!" + varMeta.varName + " :" + varMeta.varType);
                    }
                    parsedSQLInfo.declareStatements.add(
                        String.format(DECLARE_TEMPLATE, varMeta.varName, varMeta.varType));
                    outputVars.add(varMeta.varName);
                  }));
      // if no following queries depends on this query, no need to declare the variables
    }
    // row counter of select/update/delete/insert, not for txn-control
    if (sqlMetaInfo.rowCntVar != null) {
      VarMetaInfo cntVar = sqlMetaInfo.rowCntVar;
      if (allDeclaredVar.put(cntVar.varName, cntVar.varType) != null) {
        throw new RuntimeException(
            "Duplicate variable name!:" + cntVar.varName + " :" + cntVar.varType);
      }
      parsedSQLInfo.declareStatements.add(
          String.format(DECLARE_TEMPLATE, cntVar.varName, cntVar.varType));
    }
    // cursor counter of select
    if (sqlMetaInfo.cursorCntVar != null) {
      VarMetaInfo cntVar = sqlMetaInfo.cursorCntVar;
      if (allDeclaredVar.put(cntVar.varName, cntVar.varType) != null) {
        throw new RuntimeException(
            "Duplicate variable name!" + cntVar.varName + " :" + cntVar.varType);
      }
      parsedSQLInfo.declareStatements.add(
          String.format(DECLARE_TEMPLATE, cntVar.varName, cntVar.varType));
    }
  }

  private void parsePreCondition(SQLMetaInfo sqlMetaInfo, SingleParsedSQLInfo parsedSQLInfo) {
    if (sqlMetaInfo.dependOnSelectAtRow.size() > 0) {
      StringBuilder preCondBuilder = new StringBuilder();
      sqlMetaInfo.dependOnSelectAtRow.forEach(
          dependOnRow -> {
            int dependOnSqlIdx = dependOnRow.getLeft(), dependOnRowIdx = dependOnRow.getRight();
            // currently, we only care about those selects that result more than one row
            SQLMetaInfo dependOnSql = spInfo.sqlInfos.get(dependOnSqlIdx);
            String cntName = Objects.requireNonNull(dependOnSql.cursorCntVar).varName;
            preCondBuilder.append(cntName).append(" > ").append(dependOnRowIdx).append(" AND ");
          });
      if (preCondBuilder.length() > 0) { // remove tail ' AND '
        preCondBuilder.delete(preCondBuilder.length() - 5, preCondBuilder.length());
      }
      parsedSQLInfo.preCondition = preCondBuilder.toString();
    }
  }

  private void processConcentrated(
      SPMetaInfo spMetaInfo, SQLMetaInfo sqlMetaInfo, SingleParsedSQLInfo parsedSQLInfo) {
    if (spMetaInfo.concentratedPcs.isEmpty()) {
      return;
    }

    final String pcStr = sqlMetaInfo.pathCondition;
    if (!startsWithCommonPcVarName(pcStr)) {
      return;
    }

    final String var = parseLeadingCommonPcVarName(pcStr);
    final PathCondition concretedPc = spMetaInfo.concentratedPcs.get(var);
    if (concretedPc == null) return;
    parsedSQLInfo.declareStatements.add(commonPcVarDeclareStatement(var));
    final List<String> preDefineStatements = parsedSQLInfo.preDefineStatementsBeforePcCheck;
    // need to remove decimal wrapper
    final String actualPc =
        SQLPCUtil.simplifyPathCondition(concretedPc).replace(BigDecimalHandler.DECIMAL_WRAPPER, "");
    if (CommonPcExtractor.INTER_PROCEDURE) {
      // declare variables from previous procedures
      parseAllCommonPcVarNames(actualPc)
          .forEach(s -> parsedSQLInfo.declareStatements.add(commonPcVarDeclareStatement(s)));
    }
    preDefineStatements.add(
        String.format("SET %s=%s;\n", var, parseConditionExprToSqlSyntax(actualPc)));
    // after setting VarName = pc, there's no need to set it twice in the following block
    spMetaInfo.concentratedPcs.remove(var);
  }

  private void parsePathCondition(
      SPMetaInfo spMetaInfo, SQLMetaInfo sqlMetaInfo, SingleParsedSQLInfo parsedSQLInfo) {
    if (!StringUtils.isEmpty(sqlMetaInfo.pathCondition)) {
      processConcentrated(spMetaInfo, sqlMetaInfo, parsedSQLInfo);
      String pcSqlStr = parseConditionExprToSqlSyntax(sqlMetaInfo.pathCondition);
      parsedSQLInfo.condition = pcSqlStr;
      if (SPConfig.SP_DEBUG) {
        String errFlagVarName = "pc_err_flag_" + sqlMetaInfo.sqlIdx;
        parsedSQLInfo.declareStatements.add(String.format(DECLARE_TEMPLATE, errFlagVarName, "INT"));
        String[] subPc = pcSqlStr.split("&&");
        for (int i = 0; i < subPc.length; ++i) {
          String debugFormat =
              "SET %s = 1;\n"
                  + "IF %s THEN\n"
                  + "SET %s = 0;\n"
                  + "END IF;\n"
                  + "IF %s = 1 THEN\n"
                  + "%s"
                  + "END IF;\n";
          String errHint = String.format("SELECT 'ERROR in SQL%d PC%d';\n", sqlMetaInfo.sqlIdx, i);
          String debugStmt =
              String.format(
                  debugFormat, errFlagVarName, subPc[i], errFlagVarName, errFlagVarName, errHint);
          parsedSQLInfo.debugSqlStatements.add(debugStmt);
        }
      }
    }
  }

  private static void parseCoreSql(
      SQLMetaInfo sqlMetaInfo, SingleParsedSQLInfo parsedSQLInfo, List<String> inputVars) {
    // add savepoint statement only for write sql statement
    if (!StringUtils.isEmpty(sqlMetaInfo.savePointName) && sqlMetaInfo.sqlType.isWriteSql()) {
      parsedSQLInfo.sqlStatements.add(String.format(SAVEPOINT_TEMPLATE, sqlMetaInfo.savePointName));
    }

    if (sqlMetaInfo.sqlType == SqlType.SELECT) {
      String coreSql = String.format(sqlMetaInfo.sqlTemplate, inputVars.toArray()) + DELIMITER;
      String rowCntSql =
          String.format(
              SELECT_ROW_COUNT_TEMPLATE, Objects.requireNonNull(sqlMetaInfo.rowCntVar).varName);

      // if no query depends on result of this query, no need to use select into cursor
      boolean hasQueryDependsOn =
          !sqlMetaInfo.dependedSelects.isEmpty() || !sqlMetaInfo.dependedUpdates.isEmpty();
      if (sqlMetaInfo.returnValues.size() > 0 && hasQueryDependsOn) {
        // && (sqlMetaInfo.dependedSelects.size() > 0 || sqlMetaInfo.dependedUpdates.size() > 0)) {
        // select result into local variables using CURSOR
        String cursorName = "cursor_" + sqlMetaInfo.sqlIdx;
        String indicatorName = "indicator_" + sqlMetaInfo.sqlIdx;
        String counterName = Objects.requireNonNull(sqlMetaInfo.cursorCntVar).varName;
        String loopName = "loop_" + sqlMetaInfo.sqlIdx;
        parsedSQLInfo.declareStatements.add(String.format(DECLARE_TEMPLATE, cursorName, "int"));
        parsedSQLInfo.declareStatements.add(String.format(DECLARE_TEMPLATE, indicatorName, "int"));

        final StringBuilder loopBody = new StringBuilder();
        final List<String> flattenResultSet = new ArrayList<>();
        flattenResultSet.add(counterName);
        int rowIdx = 0;
        for (; rowIdx < sqlMetaInfo.returnValues.size(); ++rowIdx) {
          final StringBuilder fetchStmtBuilder =
              new StringBuilder().append("FETCH ").append(cursorName).append(" INTO ");
          final List<String> rowReturnVarNames =
              sqlMetaInfo.returnValues.get(rowIdx).stream()
                  .map(varMetaInfo -> varMetaInfo.varName)
                  .collect(Collectors.toList());

          fetchStmtBuilder.append(Joiner.on(", ").join(rowReturnVarNames)).append(DELIMITER);
          flattenResultSet.addAll(rowReturnVarNames);

          loopBody.append(
              String.format(IF_TEMPLATE, counterName + "=" + rowIdx, fetchStmtBuilder.toString()));
        }

        // break if counter is larger the max row number
        loopBody.append(
            String.format(
                IF_TEMPLATE,
                counterName + ">=" + rowIdx,
                "CLOSE " + cursorName + "; LEAVE " + loopName + ";"));

        String sqlStmt = String.format(sqlMetaInfo.sqlTemplate, inputVars.toArray());
        parsedSQLInfo.sqlStatements.add(
            assembleCursorSql(
                cursorName,
                indicatorName,
                counterName,
                sqlStmt,
                loopName,
                loopBody.toString(),
                "",
                sqlMetaInfo.rowCntVar.varName,
                flattenResultSet));
      } else {
        parsedSQLInfo.sqlStatements.add(coreSql);
        parsedSQLInfo.sqlStatements.add(rowCntSql);
      }
    } else if (sqlMetaInfo.sqlType.isTxnControl()) {
      parsedSQLInfo.sqlStatements.add(sqlMetaInfo.sqlTemplate + DELIMITER);
    } else { // update, insert, delete statements
      String coreSql = String.format(sqlMetaInfo.sqlTemplate, inputVars.toArray()) + DELIMITER;
      String rowCntSql =
          String.format(
              UPDATE_ROW_COUNT_TEMPLATE, Objects.requireNonNull(sqlMetaInfo.rowCntVar).varName);
      String retCntSql = "SELECT " + sqlMetaInfo.rowCntVar.varName + DELIMITER;
      // only consider those
      if (SPConfig.ENABLE_DEFER_EXECUTION) {
        throw new RuntimeException(
            "enable defer execution need to uncomment following code snippet, which need to add extra info in SQLMetaInfo.");
        /*
          && sqlMetaInfo.breakInfo.equals(BreakInfo.ND_FUNC_IN_PARAM)) {
        parsedSQLInfo.sqlStatements.add(
            String.format(
                "SELECT %d AS %s;\n",
                sqlMetaInfo.writeSqlConcreteRet,
                Objects.requireNonNull(sqlMetaInfo.rowCntVar).varName));
        parsedSQLInfo.sqlStatements.add(
            String.format(
                "SET %s = %d;\n",
                Objects.requireNonNull(sqlMetaInfo.rowCntVar).varName,
                sqlMetaInfo.writeSqlConcreteRet));
        parsedSQLInfo.preDefineStatements.clear();*/
      } else {
        parsedSQLInfo.sqlStatements.add(coreSql);
        parsedSQLInfo.sqlStatements.add(rowCntSql);
        parsedSQLInfo.sqlStatements.add(retCntSql);
      }
    }
  }

  private static void parseSetQueryId(
      SQLMetaInfo sqlMetaInfo, SingleParsedSQLInfo parsedSQLInfo, List<String> inputVars) {
    if (sqlMetaInfo.sqlType.isTxnControl()) {
      // sqlMetaInfo.sqlIdx == -1 indicates a commit sql
      if (sqlMetaInfo.sqlIdx != -1) {
        parsedSQLInfo.inputVars.add(
            String.format(TXN_CONTROL_QUERY_ID_TEMPLATE, sqlMetaInfo.sqlIdx));
        parsedSQLInfo.inputVars.addAll(inputVars);
        parsedSQLInfo.sqlStatements.add(
            String.format(
                SET_TXN_CONTROL_QUERY_ID_TEMPLATE, sqlMetaInfo.sqlIdx, sqlMetaInfo.sqlIdx));
      }
    } else {
      // record the input parameters for further use
      parsedSQLInfo.inputVars.add(String.format(QUERY_ID_TEMPLATE, sqlMetaInfo.sqlIdx));
      parsedSQLInfo.inputVars.addAll(inputVars);
      parsedSQLInfo.sqlStatements.add(
          String.format(SET_QUERY_ID_TEMPLATE, sqlMetaInfo.sqlIdx, sqlMetaInfo.sqlIdx));
    }
  }

  private void handleFunctionInvocationResult(
      SQLMetaInfo sqlMetaInfo, SingleParsedSQLInfo parsedSQLInfo) {
    final Map<String, String> variables = new HashMap<>();
    // extract from pc
    doExtractInvocationFromString(sqlMetaInfo.pathCondition, variables);
    // extract from parameters
    sqlMetaInfo.parameters.forEach(p -> doExtractInvocationFromString(p.remark, variables));
    variables.forEach(
        (variableName, funcName) -> {
          final SQLVarType varType =
              SemanticEqualTransformer.resolvePlaceHolderFuncRetType(funcName);
          if (allDeclaredVar.put(variableName, varType) != null) return;
          final String resolvePlaceHolderFuncName =
              SemanticEqualTransformer.resolvePlaceHolderFuncName(funcName);
          parsedSQLInfo.declareStatements.add(
              String.format(
                  DECLARE_TEMPLATE_WITH_DEFAULT,
                  variableName,
                  varType,
                  resolvePlaceHolderFuncName));
        });
  }

  private void doExtractInvocationFromString(String str, Map<String, String> variables) {
    final Matcher matcherPc = SymbolicPlaceHolder.getPattern().matcher(str);
    while (matcherPc.find()) {
      final String fullName = SymbolicPlaceHolder.fullName(matcherPc);
      final String invokingFuncName = SymbolicPlaceHolder.invokingFuncName(matcherPc);
      variables.put(fullName, invokingFuncName);
    }
  }

  private String parseConditionExprToSqlSyntax(String condition) {
    assert !StringUtils.isEmpty(condition);
    String code = String.format(PC_CODE_TEMPLATE, condition);
    return parseExpressionToSqlSyntax(code);
  }

  private String parseParamExprToSqlSyntax(String expr) {
    assert !StringUtils.isEmpty(expr);
    String code = String.format(PARAMETER_CODE_TEMPLATE, expr);
    return parseExpressionToSqlSyntax(code);
  }

  private String parseExpressionToSqlSyntax(String code) {
    final CompilationUnit cu; try { cu = StaticJavaParser.parse(code); } catch (RuntimeException failure) { System.err.println("EXPRESSION_DIAGNOSTIC " + code); throw failure; }
    ConversionVisitor conversionVisitor = new ConversionVisitor();
    cu.accept(conversionVisitor, null);
    return conversionVisitor.getSqlExpr();
  }
}
