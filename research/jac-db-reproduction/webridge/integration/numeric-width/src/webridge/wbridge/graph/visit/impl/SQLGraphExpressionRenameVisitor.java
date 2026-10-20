package webridge.wbridge.graph.visit.impl;

import webridge.wbridge.exception.NotImplementedException;
import webridge.wbridge.graph.SQLCondition;
import webridge.wbridge.graph.SQLGraph;
import webridge.wbridge.graph.SQLGraphHelper;
import webridge.wbridge.graph.SQLNode;
import webridge.wbridge.graph.impl.SQLConditionImpl;
import webridge.wbridge.graph.visit.SQLGraphNoDuplicateVisitor;
import webridge.wbridge.storedprocedure.utils.SQLPCUtil;
import webridge.wbridge.symbc.arrays.ArrayExpression;
import webridge.wbridge.symbc.mixednumstrg.SpecialIntegerExpression;
import webridge.wbridge.symbc.numeric.*;
import webridge.wbridge.symbc.string.*;

import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

public class SQLGraphExpressionRenameVisitor extends SQLGraphNoDuplicateVisitor {

  private final Map<String, String> nameMapping;
  private final Map<Expression, Expression> expressionMapping = new HashMap<>();

  public SQLGraphExpressionRenameVisitor(Map<String, String> nameMapping) {
    this.nameMapping = nameMapping;
  }

  @Override
  public void visit(SQLNode node, SQLNode prev, SQLGraph graph) {
    super.visit(node, prev, graph);

    List<String> oldParamExprs = node.getParameterExprs();
    List<Expression> oldParamSymbolics = node.getParameterSymbolics();
    String oldRowCountVarName = node.getRowCountVarName();
    List<List<String>> oldRetSymNames = node.getRetSymbolicNames();
    List<SQLCondition> oldPcs = node.getAllSQLConditions();
    String oldSavePointName = node.getSavePointName();

    List<String> newParamExprs = new ArrayList<>(oldParamExprs);
    List<Expression> newParamSymbolics = new ArrayList<>(oldParamSymbolics);

    IntStream.range(0, oldParamExprs.size())
        .forEach(
            idx -> {
              Expression oldParamSymbolic = oldParamSymbolics.get(idx);

              Expression newParamSymbolic = renameExpression(oldParamSymbolic);
              if (oldParamSymbolic != null && !newParamSymbolic.equals(oldParamSymbolic)) {
                String newParamExpr = SQLPCUtil.expandExpression(newParamSymbolic);
                newParamExprs.set(idx, newParamExpr);
                newParamSymbolics.set(idx, newParamSymbolic);
              }
            });

    List<SQLCondition> newPcs = oldPcs.stream().map(this::renamePc).collect(Collectors.toList());

    String newRowCountVarName = nameMapping.getOrDefault(oldRowCountVarName, oldRowCountVarName);
    String newSavePointName = nameMapping.getOrDefault(oldSavePointName, oldSavePointName);
    List<List<String>> newRetSymNames =
        oldRetSymNames.stream()
            .map(
                oldRetSymNamesRow ->
                    oldRetSymNamesRow.stream()
                        .map(
                            oldRetSymName -> nameMapping.getOrDefault(oldRetSymName, oldRetSymName))
                        .collect(Collectors.toList()))
            .collect(Collectors.toList());

    node.setParameterExprs(newParamExprs);
    node.setParameterSymbolics(newParamSymbolics);
    node.setOriginalPc(newPcs);
    node.setRowCountVarName(newRowCountVarName);
    node.setRetSymNames(newRetSymNames);
    node.setSavePointName(newSavePointName);
  }

  private SQLCondition renamePc(SQLCondition oldPc) {
    Set<Constraint> oldNumericConstraints = SQLGraphHelper.unlinkConstraints(oldPc.getConstraint());
    Set<StringConstraint> oldStringConstraints =
        SQLGraphHelper.unlinkStringConstraints(oldPc.getStringConstraint());

    Set<Constraint> newNumericConstraints =
        oldNumericConstraints.stream().map(this::renameConstraint).collect(Collectors.toSet());
    Set<StringConstraint> newStringConstraints =
        oldStringConstraints.stream().map(this::renameStringConstraint).collect(Collectors.toSet());

    return new SQLConditionImpl(
        SQLGraphHelper.linkConstraints(new ArrayList<>(newNumericConstraints)),
        newNumericConstraints.size(),
        SQLGraphHelper.linkStringConstraints(new ArrayList<>(newStringConstraints)),
        newStringConstraints.size());
  }

  private Constraint renameConstraint(Constraint oldConstraint) {
    if (oldConstraint.getClass().equals(LinearIntegerConstraint.class)) {
      return new LinearIntegerConstraint(
          (IntegerExpression) renameExpression(oldConstraint.getLeft()),
          oldConstraint.getComparator(),
          (IntegerExpression) renameExpression(oldConstraint.getRight()));
    } else if (oldConstraint.getClass().equals(NonLinearIntegerConstraint.class)) {
      return new NonLinearIntegerConstraint(
          (IntegerExpression) renameExpression(oldConstraint.getLeft()),
          oldConstraint.getComparator(),
          (IntegerExpression) renameExpression(oldConstraint.getRight()));
    } else if (oldConstraint instanceof MixedConstraint) {
      return new MixedConstraint(
          (RealExpression) renameExpression(oldConstraint.getLeft()),
          oldConstraint.getComparator(),
          (IntegerExpression) renameExpression(oldConstraint.getRight()));
    } else if (oldConstraint instanceof RealConstraint) {
      return new RealConstraint(
          (RealExpression) renameExpression(oldConstraint.getLeft()),
          oldConstraint.getComparator(),
          (RealExpression) renameExpression(oldConstraint.getRight()));
    } else {
      throw new NotImplementedException("rename constraint: " + oldConstraint.getClass());
    }
  }

  private StringConstraint renameStringConstraint(StringConstraint oldStringConstraint) {
    if (!(oldStringConstraint.getClass().equals(LogicalOrStringConstraints.class))) {
      return new StringConstraint(
          (StringExpression) renameExpression(oldStringConstraint.getLeft()),
          oldStringConstraint.getComparator(),
          (StringExpression) renameExpression(oldStringConstraint.getRight()));
    }
    throw new NotImplementedException();
  }

  private Expression renameExpression(Expression oldExpression) {
    if (oldExpression == null) return null;

    if (oldExpression.getClass().equals(StringSymbolic.class)) {
      if (!nameMapping.containsKey(oldExpression.toString())) {
        return oldExpression;
      }
      StringSymbolic newExpression = (StringSymbolic) expressionMapping.get(oldExpression);
      if (newExpression == null) {
        newExpression = new StringSymbolic(nameMapping.get(oldExpression.toString()));
        expressionMapping.put(oldExpression, newExpression);
      }
      return newExpression;
    } else if (oldExpression.getClass().equals(DerivedStringExpression.class)) {
      if (((DerivedStringExpression) oldExpression).getOprlist() != null) {
        return new DerivedStringExpression(
            ((DerivedStringExpression) oldExpression).getOp(),
            Arrays.stream(((DerivedStringExpression) oldExpression).oprlist)
                .map(this::renameExpression)
                .toArray(Expression[]::new));
      } else {
        return new DerivedStringExpression(
            (StringExpression)
                renameExpression(((DerivedStringExpression) oldExpression).getLeft()),
            ((DerivedStringExpression) oldExpression).getOp(),
            (StringExpression)
                renameExpression(((DerivedStringExpression) oldExpression).getRight()));
      }
    } else if (oldExpression instanceof SymbolicReal) {
      if (!nameMapping.containsKey(trimName(oldExpression.toString()))) {
        return oldExpression;
      }
      SymbolicReal newExpression = (SymbolicReal) expressionMapping.get(oldExpression);
      if (newExpression == null) {
        final String oldName = oldExpression.toString();
        final String newName = getNewName(oldName);
        newExpression = new SymbolicReal(newName);
        expressionMapping.put(oldExpression, newExpression);
      }
      return newExpression;
    } else if (oldExpression.getClass().equals(SymbolicInteger.class)) {
      if (!nameMapping.containsKey(trimName(oldExpression.toString()))) {
        return oldExpression;
      }
      SymbolicInteger newExpression = (SymbolicInteger) expressionMapping.get(oldExpression);
      if (newExpression == null) {
        final String oldName = oldExpression.toString();
        final String newName = getNewName(oldName);
        newExpression = new SymbolicInteger(newName, ((SymbolicInteger) oldExpression)._min, ((SymbolicInteger) oldExpression)._max, ((SymbolicInteger) oldExpression).getTypeCode());
        expressionMapping.put(oldExpression, newExpression);
      }
      return newExpression;
    } else if (oldExpression.getClass().equals(SymbolicBoolean.class)) {
      if (!nameMapping.containsKey(trimName(oldExpression.toString()))) {
        return oldExpression;
      }
      SymbolicBoolean newExpression = (SymbolicBoolean) expressionMapping.get(oldExpression);
      if (newExpression == null) {
        final String oldName = oldExpression.toString();
        final String newName = getNewName(oldName);
        newExpression = new SymbolicBoolean(newName);
        expressionMapping.put(oldExpression, newExpression);
      }
      return newExpression;
    } else if (oldExpression.getClass().equals(BinaryLinearIntegerExpression.class)) {
      return new BinaryLinearIntegerExpression(
          (IntegerExpression)
              renameExpression(((BinaryLinearIntegerExpression) oldExpression).getLeft()),
          ((BinaryLinearIntegerExpression) oldExpression).getOp(),
          (IntegerExpression)
              renameExpression(((BinaryLinearIntegerExpression) oldExpression).getRight()));
    } else if (oldExpression.getClass().equals(BinaryNonLinearIntegerExpression.class)) {
      return new BinaryNonLinearIntegerExpression(
          (IntegerExpression)
              renameExpression(((BinaryNonLinearIntegerExpression) oldExpression).getLeft()),
          ((BinaryNonLinearIntegerExpression) oldExpression).getOp(),
          (IntegerExpression)
              renameExpression(((BinaryNonLinearIntegerExpression) oldExpression).getRight()));
    } else if (oldExpression instanceof BinaryRealExpression) {
      return new BinaryRealExpression(
          (RealExpression) renameExpression(((BinaryRealExpression) oldExpression).getLeft()),
          ((BinaryRealExpression) oldExpression).getOp(),
          (RealExpression) renameExpression(((BinaryRealExpression) oldExpression).getRight()));
    } else if (oldExpression.getClass().equals(SymbolicLengthInteger.class)) {
      return new SymbolicLengthInteger(
          ((SymbolicLengthInteger) oldExpression).getName(),
          (int) ((SymbolicLengthInteger) oldExpression).getMin(),
          (int) ((SymbolicLengthInteger) oldExpression).getMax(),
          (StringExpression)
              renameExpression(((SymbolicLengthInteger) oldExpression).getExpression()));
    } else if (oldExpression.getClass().equals(SymbolicCharAtInteger.class)) {
      return new SymbolicCharAtInteger(
          ((SymbolicCharAtInteger) oldExpression).getName(),
          (int) ((SymbolicCharAtInteger) oldExpression).getMin(),
          (int) ((SymbolicCharAtInteger) oldExpression).getMax(),
          (StringExpression)
              renameExpression(((SymbolicCharAtInteger) oldExpression).getExpression()),
          (IntegerExpression) renameExpression(((SymbolicCharAtInteger) oldExpression).getIndex()),
          ((SymbolicCharAtInteger) oldExpression).isConstant());
    } else if (oldExpression.getClass().equals(SymbolicLastIndexOfChar2Integer.class)) {
      return new SymbolicLastIndexOfChar2Integer(
          ((SymbolicLastIndexOfChar2Integer) oldExpression).getName(),
          (int) ((SymbolicLastIndexOfChar2Integer) oldExpression).getMin(),
          (int) ((SymbolicLastIndexOfChar2Integer) oldExpression).getMax(),
          (StringExpression)
              renameExpression(((SymbolicLastIndexOfChar2Integer) oldExpression).getSource()),
          (IntegerExpression)
              renameExpression(((SymbolicLastIndexOfChar2Integer) oldExpression).getExpression()),
          (IntegerExpression)
              renameExpression(((SymbolicLastIndexOfChar2Integer) oldExpression).getMinDist()));
    } else if (oldExpression.getClass().equals(SymbolicIndexOfInteger.class)) {
      return new SymbolicIndexOfInteger(
          ((SymbolicIndexOfInteger) oldExpression).getName(),
          (int) ((SymbolicIndexOfInteger) oldExpression).getMin(),
          (int) ((SymbolicIndexOfInteger) oldExpression).getMax(),
          (StringExpression) renameExpression(((SymbolicIndexOfInteger) oldExpression).getSource()),
          (StringExpression)
              renameExpression((((SymbolicIndexOfInteger) oldExpression).getExpression())));
    } else if (oldExpression.getClass().equals(SymbolicIsEmptyInteger.class)) {
      return new SymbolicIsEmptyInteger(
          ((SymbolicIsEmptyInteger) oldExpression).getName(),
          (int) ((SymbolicIsEmptyInteger) oldExpression).getMin(),
          (int) ((SymbolicIsEmptyInteger) oldExpression).getMax(),
          (StringExpression)
              renameExpression(((SymbolicIsEmptyInteger) oldExpression).getExpression()));
    } else if (oldExpression.getClass().equals(SymbolicFunction.class)) {
      return new SymbolicFunction(
          ((SymbolicFunction) oldExpression).getFunctionType(),
          renameExpression(((SymbolicFunction) oldExpression).getParameterExpr()));
    } else if (oldExpression.getClass().equals(SymbolicDecimal.class)) {
      return new SymbolicDecimal(
          (IntegerExpression)
              renameExpression(((SymbolicDecimal) oldExpression).getSymbolicIntCompact()),
          (IntegerExpression)
              renameExpression(((SymbolicDecimal) oldExpression).getSymbolicScale()));
    } else if (oldExpression.getClass().equals(SpecialIntegerExpression.class)) {
      return new SpecialIntegerExpression(
          (StringExpression) renameExpression(((SpecialIntegerExpression) oldExpression).opr),
          ((SpecialIntegerExpression) oldExpression).op);
    } else if (oldExpression.getClass().equals(SymbolicLastIndexOfCharInteger.class)) {
      return new SymbolicLastIndexOfCharInteger(
          ((SymbolicLastIndexOfCharInteger) oldExpression).getName(),
          (int) ((SymbolicLastIndexOfCharInteger) oldExpression).getMin(),
          (int) ((SymbolicLastIndexOfCharInteger) oldExpression).getMax(),
          (StringExpression)
              renameExpression(((SymbolicLastIndexOfCharInteger) oldExpression).getSource()),
          (IntegerExpression)
              renameExpression(((SymbolicLastIndexOfCharInteger) oldExpression).getExpression()));
    } else if (oldExpression.getClass().equals(ArrayExpression.class)) {
      return new ArrayExpression(
          ((ArrayExpression) oldExpression).getName(),
          ((ArrayExpression) oldExpression).getElemType(),
          (SymbolicInteger) renameExpression(((ArrayExpression) oldExpression).lengthExpr));
    } else if (oldExpression.getClass().equals(IntegerConstant.class)
        || oldExpression.getClass().equals(LongConstant.class)
        || oldExpression.getClass().equals(StringConstant.class)
        || oldExpression.getClass().equals(SymbolicRef.class)
        || oldExpression.getClass().equals(RealConstant.class)
        || oldExpression.getClass().equals(SymbolicPlaceHolder.class)) {
      return oldExpression;
    } else if (oldExpression.getClass().equals(DerivedSymbolicInteger.class)) {
      return new DerivedSymbolicInteger(
          ((DerivedSymbolicInteger) oldExpression).getDerivedExp(),
          ((DerivedSymbolicInteger) oldExpression).getName(),
          ((DerivedSymbolicInteger) oldExpression).getType());
    } else {
      throw new NotImplementedException("rename expression: " + oldExpression.getClass());
    }
  }

  private String trimName(String name) {
    return name.replace("#value", "")
        .replace("$BIG_DECIMAL$", "")
        .replace("#intCompact", "")
        .replace("#scale", "")
        .replace("#nanos", "")
        .replace("#fastTime", "");
  }

  private String getNewName(String oldName) {
    final String trimmed = nameMapping.get(trimName(oldName));
    if (oldName.contains("#value")) {
      return trimmed + "#value";
    } else if (oldName.contains("#nanos")) {
      return trimmed + "#nanos";
    } else if (oldName.contains("#fastTime")) {
      return trimmed + "#fastTime";
    } else if (oldName.matches("\\$BIG_DECIMAL\\$.*?#intCompact\\$BIG_DECIMAL\\$")) {
      return "$BIG_DECIMAL$" + trimmed + "#intCompact$BIG_DECIMAL$";
    } else if (oldName.matches("\\$BIG_DECIMAL\\$.*?#scale\\$BIG_DECIMAL\\$")) {
      return "$BIG_DECIMAL$" + trimmed + "#scale$BIG_DECIMAL$";
    } else {
      return trimmed;
    }
  }
}
