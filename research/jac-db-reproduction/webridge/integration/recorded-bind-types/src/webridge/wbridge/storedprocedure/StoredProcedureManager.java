package webridge.wbridge.storedprocedure;

import static java.util.Objects.requireNonNull;

import com.alibaba.druid.sql.SQLUtils;
import com.alibaba.druid.util.JdbcConstants;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import webridge.wbridge.exception.NotImplementedException;
import webridge.wbridge.graph.SQLGraphManager;
import webridge.wbridge.graph.SQLNode;
import webridge.wbridge.graph.processor.SQLGraphSPDefBuilder;
import webridge.wbridge.hack.pc.BigDecimalHandler;
import webridge.wbridge.hack.pc.PathConditionPruner;
import webridge.wbridge.sql.SymbolicSQLTemplate;
import webridge.wbridge.sql.ast.SQLAstVisitor;
import webridge.wbridge.sql.ast.SqlVisitorUtils;
import webridge.wbridge.sql.types.SQLVarType;
import webridge.wbridge.storedprocedure.transformation.FunctionType;
import webridge.wbridge.storedprocedure.transformation.SemanticEqualTransformer;
import webridge.wbridge.storedprocedure.utils.SQLPCUtil;
import webridge.wbridge.symbc.Constants;
import webridge.wbridge.symbc.numeric.*;
import webridge.wbridge.symbc.numeric.Comparator;
import webridge.wbridge.symbc.string.*;
import webridge.wbridge.vm.Types;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import webridge.wbridge.sql.SQLStringResolver;

public class StoredProcedureManager {

  public static String TMP_JSON_PATH;
  public static String JPF_CNF;
  public static String DEFAULT_SCHEMA_PATH;

  private static final Logger logger = LoggerFactory.getLogger(StoredProcedureManager.class);

  static {
//            initBroadleafConfig();
//    initShopizerConfig();
  }

  private static void initBroadleafConfig() {
    initBroadleafItemDetails();
    //    initBroadleafAdd();
    //    initBroadleafCodPayment();
    DEFAULT_SCHEMA_PATH =
        "jpf-web/broadleaf-react-benchmark/api/src/main/resources/broadleaf.schema.sql";
  }

  private static void initBroadleafItemDetails() {
    //        TMP_JSON_PATH = "/tmp/ItemDetails-1005214439.json";
    TMP_JSON_PATH = "/tmp/ItemDetails-1634577094.json";

    JPF_CNF = "conf/item-details.jpf";
  }

  private static void initBroadleafAdd() {
    TMP_JSON_PATH = "/tmp/Add-864977073.json";
    TMP_JSON_PATH = "Add-864977073_prune_listmapset.json";
    JPF_CNF = "conf/add.jpf";
  }

  private static void initBroadleafCodPayment() {
    TMP_JSON_PATH = "/tmp/webridgeMngr.tmp.sp.string";
    TMP_JSON_PATH = "Codpayment_prune_setlistmap.json";
    JPF_CNF = "conf/codpayment.jpf";
  }

  private static void initShopizerConfig() {
    initShopizerViewProduct();
//    initShopizerAddCart();
    //    initShopizerPurchase();
    DEFAULT_SCHEMA_PATH = "shopizer/sm-shop/shopizer_schema.sql";
    SPConfig.addConfig(Constants.SCHEMA_DEF_FILE_KEY, DEFAULT_SCHEMA_PATH);
  }

  private static void initShopizerViewProduct() {
    //    TMP_JSON_PATH = "/tmp/ViewProduct.json";
    TMP_JSON_PATH = "ViewProduct_prune_setlistmap.json";
    JPF_CNF = "conf/view-product.jpf";
  }

  private static void initShopizerAddCart() {
    //    TMP_JSON_PATH = "/tmp/AddCart-1128134210.json";
    TMP_JSON_PATH = "AddCart_prune_setlistmap.json";

    JPF_CNF = "conf/add-cart.jpf";
  }

  private static void initShopizerPurchase() {
    TMP_JSON_PATH = "/tmp/Purchase.json";
    TMP_JSON_PATH = "Purchase_prune_setlistmap.json";

    JPF_CNF = "conf/purchase.jpf";
  }

  private static final Map<String, Comparator> str2comparator;
  private static final Map<String, Operator> str2operator;

  static {
    str2comparator =
        Arrays.stream(Comparator.values())
            .collect(
                Collectors.toMap(comparator -> comparator.toString().trim(), Function.identity()));
    str2operator =
        new HashMap<>(
            Arrays.stream(Operator.values())
                .collect(
                    Collectors.toMap(operator -> operator.toString().trim(), Function.identity())));
    str2operator.put(">>u", Operator.SHIFTUR);
    str2operator.put("@", Operator.DIV);
  }

  public static void main(String[] args) throws Exception {
    if (args.length == 2) {
      run(args[0], args[1]);
    } else {
      run(TMP_JSON_PATH, JPF_CNF);
    }
  }

  private static Expression parsePCJsonObjectExpression(JSONObject expression) {
    String expressionType = requireNonNull(expression.getString("_type"));
    switch (expressionType) {
      case "BinaryExpression":
        final String opStr = requireNonNull(expression.getString("_op"));
        final Operator op = str2operator.get(opStr);
        JSONObject left = expression.getJSONObject("_left");
        Expression leftExp = left == null ? null : parsePCJsonObjectExpression(left);
        Expression rightExp =
            parsePCJsonObjectExpression(requireNonNull(expression.getJSONObject("_right")));
        boolean isLeftInteger = leftExp instanceof IntegerExpression;
        boolean isLeftReal = leftExp instanceof RealExpression;
        boolean isRightInteger = rightExp instanceof IntegerExpression;
        boolean isRightReal = rightExp instanceof RealExpression;
        if (op == null) {
          throw new RuntimeException();
        }

        switch (op) {
          case PLUS:
            if (isLeftInteger && isRightInteger) {
              return ((IntegerExpression) leftExp)._plus((IntegerExpression) rightExp);
            }
            if (isLeftReal && isRightReal) {
              return ((RealExpression) leftExp)._plus(((RealExpression) rightExp));
            }
            if (isLeftInteger && isRightReal) {
              leftExp = new DerivedSymbolicReal(
                      leftExp, DerivedSymbolicReal.Type.CAST_TO_REAL
              );
              return ((RealExpression) leftExp)._plus((RealExpression) rightExp);
            }
            if (leftExp == null || rightExp == null) {
              return null;
            }
            throw new NotImplementedException(expression.toString());
          case MINUS:
            if (leftExp == null) {
              if (isRightInteger) {
                return ((IntegerExpression) rightExp)._neg();
              } else if (isRightReal) {
                return ((RealExpression) rightExp)._neg();
              } else {
                throw new NotImplementedException();
              }
            }

            if (isLeftInteger && isRightInteger) {
              return ((IntegerExpression) leftExp)._minus((IntegerExpression) rightExp);
            }
            if (isLeftReal && isRightReal) {
              return ((RealExpression) leftExp)._minus(((RealExpression) rightExp));
            }
            throw new NotImplementedException(op.toString());

          case MUL:
            if (isLeftInteger && isRightInteger) {
              return ((IntegerExpression) leftExp)._mul((IntegerExpression) rightExp);
            }
            if (isLeftReal && isRightReal) {
              return ((RealExpression) leftExp)._mul(((RealExpression) rightExp));
            }
            throw new NotImplementedException(op.toString());
          case OR:
            if (isLeftInteger && isRightInteger) {
              return ((IntegerExpression) leftExp)._or(((IntegerExpression) rightExp));
            }
            throw new NotImplementedException(op + " of non integer expressions");
          case SHIFTUR:
            if (isLeftInteger && isRightInteger) {
              return ((IntegerExpression) leftExp)._shiftUR(((IntegerExpression) rightExp));
            }
            throw new NotImplementedException(op + " of non integer expressions");
          case SHIFTR:
            if (isLeftInteger && isRightInteger) {
              return ((IntegerExpression) leftExp)._shiftR(((IntegerExpression) rightExp));
            }
            throw new NotImplementedException(op + " of non integer expressions");
          case SHIFTL:
            if (isLeftInteger && isRightInteger) {
              return ((IntegerExpression) leftExp)._shiftL(((IntegerExpression) rightExp));
            }
            throw new NotImplementedException(op + " of non integer expressions");
          case XOR:
            if (isLeftInteger && isRightInteger) {
              return ((IntegerExpression) leftExp)._xor(((IntegerExpression) rightExp));
            }
            throw new NotImplementedException(op + " of non integer expressions");
          case AND:
            if (isLeftReal) {
              leftExp = new DerivedSymbolicInteger(leftExp, DerivedSymbolicInteger.Type.CAST_TO_INTEGER);
            }
            if (isRightReal) {
              rightExp = new DerivedSymbolicInteger(rightExp, DerivedSymbolicInteger.Type.CAST_TO_INTEGER);
            }
            return ((IntegerExpression) leftExp)._and((IntegerExpression) rightExp);
          case DIV:
            if (isLeftInteger && isRightInteger) {
              return ((IntegerExpression) leftExp)._div(((IntegerExpression) rightExp));
            }
            if (isLeftReal && isRightReal) {
              return ((RealExpression) leftExp)._div(((RealExpression) rightExp));
            }
            throw new NotImplementedException(op.toString());
          case REM:
            if (isLeftInteger && isRightInteger) {
              return ((IntegerExpression) leftExp)._rem(((IntegerExpression) rightExp));
            }
            throw new NotImplementedException(op + " of non integer expressions");
          default:
            throw new NotImplementedException(op.toString());
        }
      case "SymbolExpression":
        {
          String javaType = requireNonNull(expression.getString("_java_type"));
          String expStr = normalize(requireNonNull(expression.getString("_exp")));
          if (javaType.isEmpty()) {
            if (expStr.equals("N")) {
              // NULL
              return null;
            }
            if (expStr.contains("scale" + BigDecimalHandler.DECIMAL_WRAPPER)) {
              javaType = "J";
            } else if (expStr.contains("intCompact" + BigDecimalHandler.DECIMAL_WRAPPER)) {
              javaType = "J";
            } else if (expStr.contains("#fastTime")) {
              javaType = "J";
            } else if (expStr.contains("#nanos")) {
              javaType = "I";
            } else {
              throw new IllegalArgumentException("No java type found:" + expression);
            }
          }
          switch (javaType) {
            case "B":
            case "C":
            case "I":
            case "S":
              return new SymbolicInteger(expStr);
            case "J":
              return new SymbolicInteger(expStr, Types.T_LONG);
            case "D":
            case "F":
              return new SymbolicReal(expStr);
            case "V":
              throw new RuntimeException("Unexpected void type expression");
            case "Z":
              return new SymbolicBoolean(expStr);
            case "java/lang/String":
              return new StringSymbolic(expStr);
            default:
              throw new IllegalArgumentException(javaType);
          }
        }
      case "ConstExpr":
      case "ConSymbolExp":
      case "ConStringSymbolExp":
        {
          String javaType = requireNonNull(expression.getString("_java_type"));
          String expStr = normalize(requireNonNull(expression.getString("_exp")));
          String[] elems = expStr.split("_");
          if (expStr.charAt(0) != 'Y') throw new IllegalArgumentException(expression.toString());
          expStr = expStr.substring(2);
          String value;
          if (expStr.startsWith("L")) {
            value = expStr.substring(2 + expStr.indexOf("__"));
          } else {
            value = expStr.substring(2);
          }

          switch (javaType) {
            case "B":
            case "C":
            case "I":
            case "S":
            case "Z":
              return new IntegerConstant(Integer.parseInt(value));
            case "J":
              return new LongConstant(Long.parseLong(value));
            case "D":
            case "F":
              return new RealConstant(Float.parseFloat(value));
            case "V":
              throw new RuntimeException("Unexpected void type expression");
            case "java/lang/String":
              return new StringConstant(value.replace("\n", "\\n").replace("\"", "\\\""));
            default:
              throw new IllegalArgumentException(javaType);
          }
        }
      case "MethodExpression":
        return null;
      case "PlaceholderExpression":
        //        System.out.println(expression);
        if (!requireNonNull(expression.getString("_place_holder_func"))
            .equals("currentTimeMills")) {
          throw new RuntimeException(expression.toString());
        }
        final SymbolicPlaceHolder symbHolder =
            new SymbolicPlaceHolder(
                SemanticEqualTransformer.getTransformedSpFunction(FunctionType.CURRENT_TIME), true);
        symbHolder.setConvertedRepresentation(
            SymbolicPlaceHolder.ND_FUNC_TEMPLATE_PREFIX
                + "currentTimeMs__"
                + 42 // TODO: check whether the hash need to be replaced
                + "__"
                + requireNonNull(expression.getInteger("_count")));
        return symbHolder;
      case "OpStrExpression":
        String opName = requireNonNull(expression.getString("_name"));
        JSONArray paramList = requireNonNull(expression.getJSONArray("_param_list"));
        switch (opName) {
          case "length":
            {
              if (paramList.size() != 1) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramJson = paramList.getJSONObject(0);
              StringExpression stringSymbolic =
                  (StringExpression) parsePCJsonObjectExpression(paramJson);
              if (stringSymbolic == null) return null;
              return requireNonNull(stringSymbolic)._length();
            }
          case "isEmpty":
            {
              if (paramList.size() != 1) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramJson = paramList.getJSONObject(0);
              StringExpression stringSymbolic = requireNonNull((StringExpression) parsePCJsonObjectExpression(paramJson));
              return stringSymbolic._isEmpty();
              // throw new NotImplementedException(opName + ":" + expression);
            }
          case "charAt":
            {
              if (paramList.size() != 2) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramJson = paramList.getJSONObject(0);
              StringExpression stringSymbolic =
                  (StringExpression) requireNonNull(parsePCJsonObjectExpression(paramJson));
              return stringSymbolic._charAt(
                  ((IntegerExpression) parsePCJsonObjectExpression(paramList.getJSONObject(1))));
            }
          case "intern":
            {
              if (paramList.size() != 1) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramJson = paramList.getJSONObject(0);
              StringExpression stringSymbolic =
                  (StringExpression) requireNonNull(parsePCJsonObjectExpression(paramJson));
              return stringSymbolic._intern();
            }
          case "hashCode":
            {
              if (paramList.size() != 1) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramJson = paramList.getJSONObject(0);
              StringExpression stringSymbolic =
                  (StringExpression) requireNonNull(parsePCJsonObjectExpression(paramJson));
              return stringSymbolic._hashCode();
            }
          case "concat":
            {
              if (paramList.size() != 2) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramJson = paramList.getJSONObject(0);
              StringExpression stringSymbolic =
                  (StringExpression) requireNonNull(parsePCJsonObjectExpression(paramJson));
              return stringSymbolic._concat(
                  (StringExpression)
                      requireNonNull(parsePCJsonObjectExpression(paramList.getJSONObject(1))));
            }
          case "toUpperCase":
            {
              if (paramList.size() != 1) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramJson = paramList.getJSONObject(0);
              StringExpression stringSymbolic =
                  (StringExpression) requireNonNull(parsePCJsonObjectExpression(paramJson));
              return stringSymbolic._toUpperCase();
            }
          case "toLowerCase":
            {
              if (paramList.size() != 1) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramJson = paramList.getJSONObject(0);
              StringExpression stringSymbolic =
                  (StringExpression) requireNonNull(parsePCJsonObjectExpression(paramJson));
              return stringSymbolic._toLowerCase();
            }
          case "valueOf":
            {
              if (paramList.size() != 1) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramJson = paramList.getJSONObject(0);
              Expression paramExpr = requireNonNull(parsePCJsonObjectExpression(paramJson));
              if (paramExpr instanceof IntegerExpression) {
                return StringExpression._valueOf((IntegerExpression) paramExpr);
              } else if (paramExpr instanceof RealExpression) {
                return StringExpression._valueOf((RealExpression) paramExpr);
              } else if (paramExpr instanceof StringExpression) {
                return StringExpression._valueOf((StringExpression) paramExpr);
              } else {
                throw new NotImplementedException(paramExpr.toString());
              }
            }
          case "toString":
            {
              if (paramList.size() != 1) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramJson = paramList.getJSONObject(0);
              Expression paramExpr = (parsePCJsonObjectExpression(paramJson));
              if (paramExpr instanceof StringExpression) {
                return paramExpr;
              } else if (paramExpr instanceof IntegerExpression) {
                return StringExpression._valueOf((IntegerExpression) paramExpr);
              } else if (paramExpr instanceof RealExpression) {
                return StringExpression._valueOf((RealExpression) paramExpr);
              } else {
                throw new NotImplementedException(paramJson.toString());
              }
            }
          case "trim":
            {
              // TODO: implement trim
              if (paramList.size() != 1) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramJson = paramList.getJSONObject(0);
              Expression paramExpr = requireNonNull(parsePCJsonObjectExpression(paramJson));
              if (paramExpr instanceof StringExpression) {
                return paramExpr;
              } else {
                throw new NotImplementedException(paramJson.toString());
              }
            }
          case "regionMatches":
            {
              // TODO: not handled
              return null;
            }
          case "indexOf":
            {
              // TODO: not handled
              return null;
            }
          case "substring":
          case "subSequence":
            {
              JSONObject paramJson = paramList.getJSONObject(0);
              Expression paramExpr = requireNonNull(parsePCJsonObjectExpression(paramJson));
              if (!(paramExpr instanceof StringExpression)) {
                throw new NotImplementedException(paramJson.toString());
              }

              switch (paramList.size()) {
                case 3:
                  {
                    final StringExpression strExp = (StringExpression) paramExpr;
                    return strExp._subString(
                        (IntegerExpression) parsePCJsonObjectExpression(paramList.getJSONObject(1)),
                        (IntegerExpression)
                            parsePCJsonObjectExpression(paramList.getJSONObject(2)));
                  }
                case 2:
                  {
                    final StringExpression strExp = (StringExpression) paramExpr;
                    return strExp._subString(
                        (IntegerExpression)
                            parsePCJsonObjectExpression(paramList.getJSONObject(1)));
                  }
                default:
                  throw new IllegalArgumentException(paramList.toString());
              }
            }
          case "lastIndexOf":
            {
              JSONObject paramStr = paramList.getJSONObject(0);
              Expression paramExpr = requireNonNull(parsePCJsonObjectExpression(paramStr));
              if (!(paramExpr instanceof StringExpression))
                throw new NotImplementedException(paramList.toString());

              Expression arg1 = parsePCJsonObjectExpression(paramList.getJSONObject(1));
              StringExpression strExp = (StringExpression) paramExpr;

              switch (paramList.size()) {
                case 2:
                  {
                    if (arg1 instanceof StringExpression) {
                      return strExp._lastIndexOf((StringExpression) arg1);
                    } else if (arg1 instanceof IntegerExpression) {
                      return strExp._lastIndexOf((IntegerExpression) arg1);
                    } else {
                      throw new IllegalArgumentException(paramList.toString());
                    }
                  }
                case 3:
                  {
                    Expression arg2 = parsePCJsonObjectExpression(paramList.getJSONObject(2));
                    if (!(arg2 instanceof IntegerExpression)) {
                      throw new IllegalArgumentException(paramList.toString());
                    }

                    if (arg1 instanceof StringExpression) {
                      return strExp._lastIndexOf((StringExpression) arg1, (IntegerExpression) arg2);
                    } else if (arg1 instanceof IntegerExpression) {
                      return strExp._lastIndexOf(
                          (IntegerExpression) arg1, (IntegerExpression) arg2);
                    } else {
                      throw new IllegalArgumentException(paramList.toString());
                    }
                  }
                default:
                  throw new IllegalArgumentException(paramList.toString());
              }
            }
          default:
            throw new NotImplementedException(opName + ":" + expression);
        }
      case "BigDecimalExpression":
        {
          JSONObject scaleJObj = requireNonNull(expression.getJSONObject("_scale"));
          JSONObject intCmpJObj = requireNonNull(expression.getJSONObject("_intCompact"));
          IntegerExpression scaleExp = (IntegerExpression) parsePCJsonObjectExpression(scaleJObj);
          IntegerExpression intCmpExp = (IntegerExpression) parsePCJsonObjectExpression(intCmpJObj);
          return new SymbolicDecimal(intCmpExp, scaleExp);
        }
      case "SymbolicFunction":
        {
          String funcType = requireNonNull(expression.getString("_func_type"));
          switch (funcType) {
            case "TO_TIMESTAMP":
              Expression paramExpr =
                  requireNonNull(parsePCJsonObjectExpression(expression.getJSONObject("_exp")));
              return new SymbolicFunction(FunctionType.TO_TIMESTAMP, paramExpr);
            default:
              throw new NotImplementedException(expression.toString());
          }
        }
      case "TypeCastExpression":
        {
          final String castType = expression.getString("_java_type");
          final Expression paramExpr =
              requireNonNull(parsePCJsonObjectExpression(expression.getJSONObject("_exp")));
          byte builtinType = Types.getBuiltinTypeFromSignature(castType);
          switch (builtinType) {
            case Types.T_DOUBLE:
            case Types.T_FLOAT:
              return new DerivedSymbolicReal(paramExpr, DerivedSymbolicReal.Type.CAST_TO_REAL);
            case Types.T_INT:
            case Types.T_LONG:
              return new DerivedSymbolicInteger(
                  paramExpr, DerivedSymbolicInteger.Type.CAST_TO_INTEGER);
            default:
              throw new NotImplementedException(expression.toString());
          }
        }
      default:
        throw new NotImplementedException(expressionType + ":" + expression);
    }
  }

  private static Constraint parsePCJsonObjectConstraint(JSONObject constraint) {
    String constraintType = requireNonNull(constraint.getString("_type"));
    switch (constraintType) {
      case "BinaryExpression":
        final Comparator op = str2comparator.get(requireNonNull(constraint.getString("_op")));
        if (op == null) {
          throw new RuntimeException(constraint.toString());
        }
        JSONObject leftObj = requireNonNull(constraint.getJSONObject("_left"));
        JSONObject rightObj = requireNonNull(constraint.getJSONObject("_right"));
        Expression leftExp = parsePCJsonObjectExpression(leftObj);
        Expression rightExp = parsePCJsonObjectExpression(rightObj);
        boolean isLeftInteger = leftExp instanceof IntegerExpression;
        boolean isRightInteger = rightExp instanceof IntegerExpression;
        boolean isLeftReal = leftExp instanceof RealExpression;
        boolean isRightReal = rightExp instanceof RealExpression;
        if (isLeftInteger && isRightInteger) {
          return new LinearIntegerConstraint(
              (IntegerExpression) leftExp, op, (IntegerExpression) rightExp);
        }
        if (isLeftReal && isRightReal) {
          return new RealConstraint(((RealExpression) leftExp), op, ((RealExpression) rightExp));
        }
        if (isLeftReal) {
          assert rightExp instanceof IntegerExpression;
          return new MixedConstraint(
              ((RealExpression) leftExp), op, ((IntegerExpression) rightExp));
        }

        if (leftExp == null || rightExp == null) {
          return null;
        }
        assert leftExp instanceof IntegerExpression;
        assert rightExp instanceof RealExpression;
        if (!(leftExp instanceof IntegerExpression) || !(rightExp instanceof RealExpression)) {
          logger.warn("Not implemented:" + leftExp + "[" + op + "]" + rightExp);
          return null;
        }
        return new MixedConstraint(((RealExpression) rightExp), op, ((IntegerExpression) leftExp));
      case "MethodExpression":
      case "_array_expr":
      case "array_init_expr":
        return null;
      case "OpStrExpression":
        return null; // string constraints handled in parsePCJsonObjectStringConstraint
      default:
        throw new RuntimeException(constraintType + ":" + constraint);
    }
  }

  private static StringConstraint parsePCJsonObjectStringConstraint(JSONObject constraint) {
    String constraintType = requireNonNull(constraint.getString("_type"));
    switch (constraintType) {
      case "OpStrExpression":
        final String opName = requireNonNull(constraint.getString("_name"));
        final JSONArray paramList = requireNonNull(constraint.getJSONArray("_param_list"));
        Boolean is_not = constraint.getBoolean("_is_not");
        if (is_not == null) is_not = false; // FIXME: regenerate json
        final Boolean isNot = requireNonNull(is_not, constraint.toString());
        switch (opName) {
          case "equals":
            {
              if (paramList.size() != 2) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramLeft = paramList.getJSONObject(0);
              JSONObject paramRight = paramList.getJSONObject(1);
              return new StringConstraint(
                  requireNonNull(((StringExpression) parsePCJsonObjectExpression(paramLeft))),
                  isNot ? StringComparator.EQUALS.not() : StringComparator.EQUALS,
                  ((StringExpression) requireNonNull(parsePCJsonObjectExpression(paramRight))));
            }
          case "equalsIgnoreCase":
          {
            if (paramList.size() != 2) {
              throw new IllegalArgumentException(paramList.toString());
            }
            JSONObject paramLeft = paramList.getJSONObject(0);
            JSONObject paramRight = paramList.getJSONObject(1);
            return new StringConstraint(
                    requireNonNull(((StringExpression) parsePCJsonObjectExpression(paramLeft))),
                    isNot ? StringComparator.EQUALSIGNORECASE.not() : StringComparator.EQUALSIGNORECASE,
                    ((StringExpression) requireNonNull(parsePCJsonObjectExpression(paramRight))));
          }
          case "contains":
            {
              if (paramList.size() != 2) {
                throw new IllegalArgumentException(paramList.toString());
              }
              JSONObject paramLeft = paramList.getJSONObject(0);
              JSONObject paramRight = paramList.getJSONObject(1);
              return new StringConstraint(
                  requireNonNull(((StringExpression) parsePCJsonObjectExpression(paramLeft))),
                  isNot ? StringComparator.CONTAINS.not() : StringComparator.CONTAINS,
                  ((StringExpression) requireNonNull(parsePCJsonObjectExpression(paramRight))));
            }
          case "regionMatches":
            {
              return null;
            }
          case "startsWith":
            {
              //              if (paramList.size() != 2) {
              //                throw new IllegalArgumentException(paramList.toString());
              //              }
              // TODO: handle more parameters (boolean startsWith(String prefix, int toffset))
              final JSONObject paramLeft = paramList.getJSONObject(0);
              final JSONObject paramRight = paramList.getJSONObject(1);

              return new StringConstraint(
                  requireNonNull(((StringExpression) parsePCJsonObjectExpression(paramLeft))),
                  isNot ? StringComparator.STARTSWITH.not() : StringComparator.STARTSWITH,
                  ((StringExpression) requireNonNull(parsePCJsonObjectExpression(paramRight))));
            }
          case "matches":
            {
              return null;
              //            if (paramList.size() != 2) {
              //              throw new IllegalArgumentException(paramList.toString());
              //            }
              //            final JSONObject paramLeft = paramList.getJSONObject(0);
              //            final JSONObject paramRight = paramList.getJSONObject(1);
              //
              //            return new StringConstraint(
              //                requireNonNull(((StringExpression)
              // parsePCJsonObjectExpression(paramLeft))),
              //                StringComparator.MATCHES,
              //                ((StringExpression)
              // requireNonNull(parsePCJsonObjectExpression(paramRight))));
            }
          case "endsWith":
            {
              if (paramList.size() != 2) {
                throw new IllegalArgumentException(paramList.toString());
              }
              final JSONObject paramLeft = paramList.getJSONObject(0);
              final JSONObject paramRight = paramList.getJSONObject(1);

              return new StringConstraint(
                  requireNonNull(((StringExpression) parsePCJsonObjectExpression(paramLeft))),
                  isNot ? StringComparator.ENDSWITH.not() : StringComparator.ENDSWITH,
                  ((StringExpression) requireNonNull(parsePCJsonObjectExpression(paramRight))));
            }
          case "isEmpty":
          {
            if (paramList.size() != 1) {
              throw new IllegalArgumentException(paramList.toString());
            }
            final JSONObject param = paramList.getJSONObject(0);
            return new StringConstraint(
                    StringComparator.EMPTY,
                    requireNonNull((StringExpression) parsePCJsonObjectExpression(param))
            );
          }
          default:
            throw new NotImplementedException(opName + ":" + constraint);
        }
      default:
        return null;
    }
  }

  private static List<SymbolicSQLTemplate> parseFromRecordedJSON(final String content) {
    resetSpGenerationStatus();
    List<SymbolicSQLTemplate> result = new ArrayList<>();
    JSONArray templateLists = JSON.parseArray(content);
    int qid = 1;

    for (int index = 0; index < templateLists.size(); index++) {
      JSONObject stmtObj = templateLists.getJSONObject(index);
      JSONArray parameterExprsJSON = stmtObj.getJSONArray("parameterExprs");

      String concreteSQL = stmtObj.getString("sqlTemplate");
      if (concreteSQL.isEmpty() || concreteSQL.toLowerCase(Locale.ROOT).equals("select 1") ||
      concreteSQL.toLowerCase(Locale.ROOT).endsWith("select 1")) continue;
      //      System.out.println(concreteSQL);
      Boolean isTxnControl = stmtObj.getBoolean("isTxnControl");
      int connNo = ConnectionIdStore.get(stmtObj.getInteger("connNo"));
      Integer sqlId = stmtObj.getInteger("sqlId");

      SymbolicSQLTemplate symbolicSQLTemplate;
      if (!isTxnControl) {
        final SQLAstVisitor visitor = new SQLAstVisitor(SQLUtils.formatMySql(concreteSQL));
        java.util.List<String> recordedJavaTypes = new java.util.ArrayList<>();
        for(int parameterIndex=0;parameterIndex<parameterExprsJSON.size();parameterIndex++)
          recordedJavaTypes.add(parameterExprsJSON.getJSONObject(parameterIndex).getString("_java_type"));
        visitor.setRecordedParameterJavaTypes(recordedJavaTypes);
        SqlVisitorUtils.populateVisitorWithSchemaInfo(visitor, SPConfig.getConfig().getString(
                Constants.SCHEMA_DEF_FILE_KEY, DEFAULT_SCHEMA_PATH
        ));
        SQLUtils.parseSingleStatement(concreteSQL, JdbcConstants.MYSQL).accept(visitor);
        // path condition
        PathCondition pc = parsePathCondition(stmtObj);
//        PathCondition pc = new PathCondition();
        //        if (pc.toString().contains("STRING_STRING_CONST_CN")) {
        //          System.out.println("HERE");
        //          try {
        //            Files.write(Paths.get("/tmp/hehe"),
        // pc.toString().getBytes(StandardCharsets.UTF_8));
        //          } catch (IOException e) {
        //            throw new RuntimeException(e);
        //          }
        //          throw new RuntimeException();
        //        }
        symbolicSQLTemplate = SQLStringResolver.buildSymbolicSQLTemplate(visitor, pc);
        //        System.out.printf("Building SYM template used %d ms%n", System.currentTimeMillis()
        // - pcEnd);
        boolean isWriteSql = visitor.getSqlType().isWriteSql();
        if (!isWriteSql) {
          // returned ResultSet attribute names
          Integer rowCount = stmtObj.getInteger("rowCount");
          List<SQLVarType> retValTypes = symbolicSQLTemplate.getRetValTypes();
          int colCount = retValTypes.size();
          for (int rowIndex = 1; rowIndex <= rowCount; rowIndex++) {
            final List<String> retSymbNames = new ArrayList<>();
            symbolicSQLTemplate.addRetSymbolicNames(retSymbNames);
            for (int colIndex = 1; colIndex <= colCount; colIndex++) {
              String formatStr = String.format("RS_q%d_r%d_%s", sqlId, rowIndex, "col" + colIndex);
              retSymbNames.add(formatStr);
            }
          }
        }
      } else {
        final String stmtStr = concreteSQL.toLowerCase(Locale.ROOT).trim();
        if ("set autocommit=false".equals(stmtStr)) {
          symbolicSQLTemplate = SymbolicSQLTemplate.getTxnBeginSQLTemplate(connNo);
        } else if ("set autocommit=true".equals(stmtStr)) {
          symbolicSQLTemplate = SymbolicSQLTemplate.getEnableAutoCommitSQLTemplate(connNo);
        } else {
          if (!stmtStr.equals("commit")) {
            throw new RuntimeException(stmtStr);
          }
          symbolicSQLTemplate = SymbolicSQLTemplate.getCommitSQLTemplate(connNo);
        }
        PathCondition pc = parsePathCondition(stmtObj);
//        PathCondition pc = new PathCondition();

        symbolicSQLTemplate.setPc(PathConditionPruner.prunePcByRules(pc.computeNoRedundantPC()));
      }
      symbolicSQLTemplate.setSqlNo(qid++);
      symbolicSQLTemplate.setConnNo(connNo);

      // parameters
      //      long beginParam = System.currentTimeMillis();
      int size = symbolicSQLTemplate.getParamSqlTypes().size();
      //      System.out.println("Param size:" + size);
      for (int param_index = 0; param_index < size; param_index++) {
        if (parameterExprsJSON.isEmpty()) {
          // FIXME: inconsistent
          symbolicSQLTemplate.getParamSqlTypes().clear();
          symbolicSQLTemplate.getParameterJavaTypes().clear();
          symbolicSQLTemplate.getParameterExprs().clear();
          symbolicSQLTemplate.getParameterSymbolics().clear();
          break;
        }
        JSONObject expressionJSON = parameterExprsJSON.getJSONObject(param_index);
        Expression paramExpr = parsePCJsonObjectExpression(expressionJSON);
        symbolicSQLTemplate.setParamSymbolicAt(param_index, paramExpr);
        symbolicSQLTemplate.setParamExprAt(
            param_index, paramExpr == null ? "NULL" : SQLPCUtil.expandExpression(paramExpr));
        //        System.out.printf(
        //            "Param[%d] used %d ms%n", param_index, (System.currentTimeMillis() -
        // beginParam));
      }

//      long txnCtlBegin = System.currentTimeMillis();
      if (!isTxnControl) {
        symbolicSQLTemplate.setRowCountVarName(
            requireNonNull(
                    parsePCJsonObjectExpression(
                        requireNonNull(stmtObj.getJSONObject("rowCountExp"))))
                .toString());
      }
      //      System.out.printf("Row count used %d ms%n", System.currentTimeMillis() - txnCtlBegin);
      SQLGraphManager.addSQLNodeToCurrentGraph(SQLNode.of(symbolicSQLTemplate));
      result.add(symbolicSQLTemplate);
    }
    return result;
  }

  private static void resetSpGenerationStatus() {
    SQLGraphManager.reset();
    ConnectionIdStore.reset();
    EntryPoint.initApiName();
    SQLGraphSPDefBuilder.reset();
  }

  private static PathCondition parsePathCondition(JSONObject stmtObj) {
    PathCondition pc = new PathCondition();
    JSONArray pcArray = stmtObj.getJSONArray("pathCondition");
    for (int pcIndex = 0; pcIndex < pcArray.size(); pcIndex++) {
      //      if (true) break;
      JSONObject pcObj = pcArray.getJSONObject(pcIndex);
      Constraint constraint = parsePCJsonObjectConstraint(pcObj);
      StringConstraint stringConstraint = parsePCJsonObjectStringConstraint(pcObj);
      if (constraint != null && !constraint.isNull()) {
        if (constraint.getComparator().equals(Comparator.LE)) {
          Expression left = constraint.getLeft();
          Expression right = constraint.getRight();
          if (left instanceof IntegerConstant && right instanceof IntegerConstant) {
            IntegerConstant icl = (IntegerConstant) left;
            IntegerConstant icr = (IntegerConstant) right;
            if (icl.value() == 1 && icr.value() == 0) {
              continue;
            }
          }
        }
        pc.prependIfAbsent(constraint);
      }
      if (stringConstraint != null) {
        pc.spc.addConstraint(stringConstraint);
      }
    }

    return pc;
  }

  public static void run(String collectedSqlPath, String configPath) throws Exception {
    final Path filePath = Paths.get(collectedSqlPath);
    initConfig(configPath);

    String content = new String(Files.readAllBytes(filePath));
    generateStoredProcedure(content);
  }

  private static void initConfig(String configPath) {
    SPConfig.addConfig(new File(configPath));
  }

  public static void generateStoredProcedure(String content) {
    long begin = System.currentTimeMillis();
    List<SymbolicSQLTemplate> symbolicSQLTemplates = parseFromRecordedJSON(content);
    logger.info(String.format("Finished parsing using %d ms", System.currentTimeMillis() - begin));
    SQLGraphManager.generateStoredProcedure(SQLGraphManager.getCurrentGraph());
   logger.info("[WeBridge] Received SymbolicSQLs size:" + symbolicSQLTemplates.size());
  }

  private static String normalize(String str) {
    if (str == null || str.isEmpty()) return str;
    if (str.contains("_RS_q")) {
      str = str.substring(str.indexOf("RS_q"));
    }
    return str.replace("'", "_");
  }

  /**
   * Currently, WeBridge assumes connection id incremented from a same number (e.g., 1) in different
   * traces. Thus, we reset the connection ids to be incremented from 1.
   */
  private static class ConnectionIdStore {
    private static final Map<Integer, Integer> store = new HashMap<>();
    private static Integer counter = 0;

    public static int get(int originalId) {
      return store.compute(
          originalId,
          (ignored, transformedId) -> {
            if (transformedId == null) transformedId = counter++;
            return transformedId;
          });
    }

    public static void reset() {
      store.clear();
      counter = 0;
    }
  }
}
