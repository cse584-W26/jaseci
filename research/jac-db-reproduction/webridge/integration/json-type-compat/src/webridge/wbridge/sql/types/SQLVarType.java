package webridge.wbridge.sql.types;

import webridge.wbridge.storedprocedure.transformation.TypeConverter;

public enum SQLVarType {
  INT,
  INTEGER,
  BOOLEAN,
  BIT,
  BLOB,
  TINYINT,
  CHAR,
  FLOAT,
  DOUBLE,
  TEXT,
  LONGTEXT,
  MEDIUMTEXT,
  BIGINT,
  VARCHAR,
  DATETIME,
  DECIMAL,
  DATE,
  SERIAL,
  TIMESTAMP;

  public static SQLVarType of(String tp) {
    if (tp.equalsIgnoreCase("JSON")) return SQLVarType.LONGTEXT;
    if (tp.toLowerCase().startsWith("char(")) {
      // TODO: support fixed length characters
      return SQLVarType.VARCHAR;
    }
    if (tp.indexOf('(') >= 0) tp = tp.substring(0, tp.indexOf('('));
    for (SQLVarType type : SQLVarType.values()) {
      if (type.name().equalsIgnoreCase(tp)) return type;
    }
    if (tp.equalsIgnoreCase("CHARACTER VARYING")) return SQLVarType.VARCHAR;
    if (tp.equalsIgnoreCase("INT UNSIGNED")) return SQLVarType.INT;
    throw new RuntimeException("not expected type: " + tp);
  }

  public static SQLVarType ofJavaType(String javaTp) {
    String tp = TypeConverter.JavaToSQL(javaTp);
    if (tp.indexOf('(') >= 0) tp = tp.substring(0, tp.indexOf('('));
    for (SQLVarType type : SQLVarType.values()) {
      if (type.name().equalsIgnoreCase(tp)) return type;
    }
    throw new RuntimeException("not expected type: " + tp);
  }

  @Override
  public String toString() {
    if (name().equalsIgnoreCase("varchar")) {
      return "VARCHAR(512)";
    } else if (name().equalsIgnoreCase("bit")) {
      return "BIT(1)";
    } else if (name().equalsIgnoreCase("decimal")) {
      // we convert java.math.bigDecimal to varchar instead of decimal because we cannot know the
      // precision and scale in sql definition.
      // Mysql will handle the type conversion between varchar and decimal
      return "VARCHAR(512)";
    }
    return super.toString();
  }
}
