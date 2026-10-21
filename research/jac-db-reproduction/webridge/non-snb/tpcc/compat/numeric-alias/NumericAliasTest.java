import webridge.wbridge.sql.types.SQLVarType;
import webridge.wbridge.storedprocedure.transformation.TypeConverter;
public class NumericAliasTest {
 public static void main(String[]args){
  for(SQLVarType value:SQLVarType.values())if(SQLVarType.of(value.name())!=value)throw new AssertionError(value);
  for(String name:new String[]{"numeric","NUMERIC","numeric(12,2)","NUMERIC(10,4)"}){
   if(SQLVarType.of(name)!=SQLVarType.DECIMAL)throw new AssertionError(name);
   if(!TypeConverter.SQLToJava(name,true).equals(TypeConverter.SQLToJava("decimal",true)))throw new AssertionError(name);
  }
  System.out.println("PASS all existing enum mappings, NUMERIC/DECIMAL aliases and parameterized precision");
 }
}
