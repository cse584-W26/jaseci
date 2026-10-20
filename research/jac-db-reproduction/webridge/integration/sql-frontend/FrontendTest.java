import java.nio.file.*;
import java.util.*;
import com.alibaba.fastjson2.*;
import com.alibaba.druid.sql.SQLUtils;
import com.alibaba.druid.sql.ast.SQLStatement;
import com.alibaba.druid.util.JdbcConstants;
import webridge.wbridge.sql.ast.SQLAstVisitor;
import webridge.wbridge.sql.ast.SqlVisitorUtils;
public class FrontendTest {
 public static void main(String[]args)throws Exception{
  JSONArray cases=JSON.parseArray(new String(Files.readAllBytes(Paths.get(args[0])),"UTF-8"));JSONArray result=new JSONArray();
  for(Object o:cases){JSONObject t=(JSONObject)o;String sql=t.getString("sql");SQLStatement ast=SQLUtils.parseSingleStatement(sql,JdbcConstants.MYSQL);String before=ast.toString();SQLAstVisitor v=new SQLAstVisitor(SQLUtils.formatMySql(sql));SqlVisitorUtils.populateVisitorWithSchemaInfo(v,args[1]);ast.accept(v);
   if(!before.equals(ast.toString()))throw new AssertionError("SQL AST modified:"+t.getString("name"));
   if(v.getRetValNameTypeMap().size()!=t.getIntValue("expected_return_columns"))throw new AssertionError("Wrong result scope:"+t.getString("name")+v.getRetValNameTypeMap());
   List<String> types=new ArrayList<>();v.getArgTypeLst().forEach(x->types.add(x.name()));
   if(t.containsKey("expected_parameter_types")&&!types.equals(t.getJSONArray("expected_parameter_types").toJavaList(String.class)))throw new AssertionError("Wrong ordered parameter types:"+t.getString("name")+types);
   List<String> columns=new ArrayList<>();v.getArgExprLst().forEach(x->columns.add(x.getLeft()));
   if(t.containsKey("expected_parameter_columns")&&!columns.equals(t.getJSONArray("expected_parameter_columns").toJavaList(String.class)))throw new AssertionError("Wrong ordered parameters:"+t.getString("name")+columns);
   JSONObject row=new JSONObject();row.put("name",t.getString("name"));row.put("parameter_types",types);row.put("parameter_columns",columns);row.put("returns",v.getRetValNameTypeMap());row.put("sql_unchanged",true);row.put("pass",true);result.add(row);
  }
  Files.write(Paths.get(args[2]),result.toJSONString().getBytes("UTF-8"));System.out.println("PASS "+result.size()+" SQL frontend cases");
 }
}
