package webridge.wbridge.storedprocedure.transformation;

import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class TypeConverter {

  private static final Map<String, String> JAVA2SQL_TYPE_CONVERSION;
  private static final Map<String, String> SQL2JAVA_TYPE_CONVERSION;

  static {
    SQL2JAVA_TYPE_CONVERSION = new HashMap<>();
    SQL2JAVA_TYPE_CONVERSION.put("varchar", "String");
    SQL2JAVA_TYPE_CONVERSION.put("character varying", "String");
    // longtext should be handled separately from normal String type, to resolve MySQL ERROR 1406
    // (22001): Data too long
    SQL2JAVA_TYPE_CONVERSION.put("longtext", "longtext");
    SQL2JAVA_TYPE_CONVERSION.put("json", "longtext");
    SQL2JAVA_TYPE_CONVERSION.put("mediumtext", "mediumtext");
    SQL2JAVA_TYPE_CONVERSION.put("text", "String");
    SQL2JAVA_TYPE_CONVERSION.put("int", "int");
    SQL2JAVA_TYPE_CONVERSION.put("serial", "java.math.BigInteger");
    SQL2JAVA_TYPE_CONVERSION.put("char", "char");
    SQL2JAVA_TYPE_CONVERSION.put("double", "double");
    SQL2JAVA_TYPE_CONVERSION.put("float", "float");
    SQL2JAVA_TYPE_CONVERSION.put("integer", "int");
    SQL2JAVA_TYPE_CONVERSION.put("boolean", "boolean");
    SQL2JAVA_TYPE_CONVERSION.put("tinyint", "boolean");
    SQL2JAVA_TYPE_CONVERSION.put("bit", "boolean");
    SQL2JAVA_TYPE_CONVERSION.put("bigint", "long");
    SQL2JAVA_TYPE_CONVERSION.put("datetime", "java.sql.Timestamp");
    SQL2JAVA_TYPE_CONVERSION.put("timestamp", "java.sql.Timestamp");
    SQL2JAVA_TYPE_CONVERSION.put("date", "java.sql.Date");
    SQL2JAVA_TYPE_CONVERSION.put("decimal", "java.math.BigDecimal");
    SQL2JAVA_TYPE_CONVERSION.put("numeric", "java.math.BigDecimal");
    SQL2JAVA_TYPE_CONVERSION.put("blob", "String");
    SQL2JAVA_TYPE_CONVERSION.put("int unsigned" ,"int");

    JAVA2SQL_TYPE_CONVERSION = new HashMap<>();
    JAVA2SQL_TYPE_CONVERSION.put("int", "INT");
    JAVA2SQL_TYPE_CONVERSION.put("char", "CHAR");
    JAVA2SQL_TYPE_CONVERSION.put("float", "FLOAT");
    JAVA2SQL_TYPE_CONVERSION.put("double", "DOUBLE");
    JAVA2SQL_TYPE_CONVERSION.put("integer", "INT");
    JAVA2SQL_TYPE_CONVERSION.put("longtext", "LONGTEXT");
    JAVA2SQL_TYPE_CONVERSION.put("string", "VARCHAR(512)");
    JAVA2SQL_TYPE_CONVERSION.put("boolean", "BIT(1)");
    JAVA2SQL_TYPE_CONVERSION.put("long", "BIGINT");
    JAVA2SQL_TYPE_CONVERSION.put("java.sql.timestamp", "datetime");
    JAVA2SQL_TYPE_CONVERSION.put("java.math.bigdecimal", "VARCHAR(512)");
    // we convert java.math.bigDecimal to varchar instead of decimal because we cannot know the
    // precision and scale in sql definition.
    // Mysql will handle the type conversion between varchar and decimal
  }

  // remove the brackets of SQL type
  public static String removeTypeBrackets(String tp) {
    // if (tp.contains("(") && tp.endsWith(")")) return tp.substring(0, tp.indexOf('('));
    // WARN: Regex may not work well here
    if (tp.toLowerCase().startsWith("char(")) {
      // do not remote char type
      return tp;
    }
    String pattern = "\\([^()]*\\)";
    Pattern regex = Pattern.compile(pattern);
    Matcher matcher = regex.matcher(tp);
    while (matcher.find()) {
      tp = tp.replace(matcher.group(), "");
    }
    return tp;
  }

  public static String SQLToJava(String tp) {
    String type = tp.toLowerCase();

    // for fixed size chars, converting them into java String
    if (type.startsWith("char(") && type.endsWith(")"))
      return "String";

    if (!SQL2JAVA_TYPE_CONVERSION.containsKey(type)) {
      throw new RuntimeException("Unhandled SQL to Java Type Conversion: " + tp);
    }
    return SQL2JAVA_TYPE_CONVERSION.get(type);
  }

  public static String SQLToJava(String tp, boolean removeBrackets) {
    if (removeBrackets) return SQLToJava(removeTypeBrackets(tp));
    return SQLToJava(tp);
  }

  public static String JavaToSQL(String javaType) {
    String type = javaType.toLowerCase();
    if (!JAVA2SQL_TYPE_CONVERSION.containsKey(type)) {
      throw new RuntimeException("Unhandled Java to SQL Type Conversion: " + javaType);
    }
    return JAVA2SQL_TYPE_CONVERSION.get(type);
  }
}
