import java.sql.*;import java.nio.file.*;import java.util.*;import com.alibaba.fastjson2.*;import org.apache.commons.lang3.tuple.Pair;import webridge.wbridge.storedprocedure.SPConfig;import webridge.wbridge.storedprocedure.invocation.SPInvokeManager;
public class TransactionCaptureProbe{
 public static void main(String[]args)throws Exception{SPConfig.addConfig(Paths.get(args[0]).toFile());JSONArray reports=new JSONArray();for(boolean jdbc:new boolean[]{false,true})try(Connection c=DriverManager.getConnection("jdbc:mysql://127.0.0.1:55337/jac_tpcc_conventional?useSSL=false&useLocalSessionState=true","root","")){
  JSONObject r=new JSONObject();r.put("dialect",jdbc?"JDBC setAutoCommit false/true":"Statement BEGIN/COMMIT");try(Statement s=c.createStatement();ResultSet rs=s.executeQuery("SELECT @@session.sql_mode,@@global.sql_mode")){rs.next();r.put("session_sql_mode",rs.getString(1));r.put("global_sql_mode",rs.getString(2));}
  SPInvokeManager.startRecording();if(jdbc)c.setAutoCommit(false);else try(Statement s=c.createStatement()){s.execute("BEGIN");}
  try(PreparedStatement s=c.prepareStatement("SELECT w_name FROM warehouse WHERE w_id=?")){s.setLong(1,1);try(ResultSet rs=s.executeQuery()){rs.next();r.put("name",rs.getString(1));}}
  if(jdbc)c.setAutoCommit(true);else try(Statement s=c.createStatement()){s.execute("COMMIT");}
  List<Pair<String,Object>> records=SPInvokeManager.getRecordedSqlAndResultSets();JSONArray sql=new JSONArray();for(Pair<String,Object> p:records)sql.add(p.getLeft());r.put("recorded_sql",sql);r.put("record_count",records.size());SPInvokeManager.endRecording();reports.add(r);
 }Files.write(Paths.get(args[1]),reports.toJSONString().getBytes("UTF-8"));System.out.println(reports);}
}
