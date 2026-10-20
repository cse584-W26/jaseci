import java.lang.reflect.*;import java.util.*;import java.nio.file.*;import com.alibaba.fastjson2.*;
import webridge.wbridge.storedprocedure.StoredProcedureManager;import webridge.wbridge.storedprocedure.utils.SQLPCUtil;import webridge.wbridge.symbc.numeric.Expression;import webridge.wbridge.sql.types.SQLVarType;
public class WidthAudit {
 public static void main(String[] args)throws Exception{
  Method parse=StoredProcedureManager.class.getDeclaredMethod("parsePCJsonObjectExpression",JSONObject.class);parse.setAccessible(true);JSONArray rows=new JSONArray();
  for(String type:new String[]{"I","J"}){JSONObject obj=new JSONObject();obj.put("_type","SymbolExpression");obj.put("_java_type",type);obj.put("_exp","M_"+type+"_field_REQUEST_PARAM_test_value");Expression exp=(Expression)parse.invoke(null,obj);Map<String,SQLVarType> vars=new TreeMap<>();SQLPCUtil.collectExpressionVariable(exp,vars);String expected=type.equals("J")?"BIGINT":"INT";if(!vars.values().iterator().next().name().equals(expected))throw new AssertionError(vars);JSONObject row=new JSONObject();row.put("java_descriptor",type);row.put("sql_type",vars.values().iterator().next().name());row.put("declared_value_boundaries",type.equals("J")?Arrays.asList(Long.MIN_VALUE,-2147483649L,-2147483648L,2147483647L,2147483648L,1348704000000L,Long.MAX_VALUE):Arrays.asList(Integer.MIN_VALUE,Integer.MAX_VALUE));rows.add(row);}
  Files.write(Paths.get(args[0]),rows.toJSONString().getBytes("UTF-8"));System.out.println(rows);
 }
}
