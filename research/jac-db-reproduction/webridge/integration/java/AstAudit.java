import java.nio.file.*;
import com.alibaba.fastjson2.*;
import com.alibaba.druid.sql.SQLUtils;
import com.alibaba.druid.util.JdbcConstants;
import webridge.wbridge.sql.ast.SQLAstVisitor;
import webridge.wbridge.sql.ast.SqlVisitorUtils;
/** Offline read-only audit of the original SQL frontend; no JDBC imports. */
public class AstAudit {
 public static void main(String[] args)throws Exception{
  JSONArray cases=JSON.parseArray(new String(Files.readAllBytes(Paths.get(args[0])),"UTF-8"));JSONArray rows=new JSONArray();
  for(Object obj:cases){JSONObject test=(JSONObject)obj;String sql=test.getString("sql");SQLAstVisitor visitor=new SQLAstVisitor(SQLUtils.formatMySql(sql));JSONObject row=new JSONObject();row.put("name",test.getString("name"));row.put("sql",sql);row.put("expected_return_columns",test.getIntValue("expected_return_columns"));
   try{SqlVisitorUtils.populateVisitorWithSchemaInfo(visitor,args[1]);SQLUtils.parseSingleStatement(sql,JdbcConstants.MYSQL).accept(visitor);row.put("visitor_returned",true);}catch(Throwable e){row.put("visitor_returned",false);row.put("error_class",e.getClass().getName());row.put("error",e.toString());}
   row.put("captured_return_columns",visitor.getRetValNameTypeMap());row.put("captured_parameter_types",visitor.getArgTypeLst());row.put("captured_parameter_expressions",visitor.getArgExprLst());rows.add(row);
  }
  Files.write(Paths.get(args[2]),rows.toJSONString().getBytes("UTF-8"));System.out.println(rows);
 }
}
