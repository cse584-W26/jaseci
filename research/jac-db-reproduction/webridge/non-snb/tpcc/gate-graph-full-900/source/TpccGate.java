import java.sql.*;
import java.nio.file.*;
import java.util.*;
import java.io.*;
import java.math.*;
import java.security.*;
import com.alibaba.fastjson2.*;

/** Full state snapshots live outside request spans, in normalized business-key order. */
public class TpccGate {
 static void state(Connection c,Path out)throws Exception{state(c,out,null);}
 static void state(Connection c,Path out,JSONObject input)throws Exception{
  Files.createDirectories(out);Map<String,String> sql=new LinkedHashMap<>();
  sql.put("warehouse","SELECT w_id,w_ytd FROM warehouse ORDER BY w_id");
  sql.put("district","SELECT d_w_id,d_id,d_ytd,d_next_o_id FROM district ORDER BY d_w_id,d_id");
  sql.put("customer","SELECT c_w_id,c_d_id,c_id,c_balance,c_ytd_payment,c_payment_cnt,c_data FROM customer ORDER BY c_w_id,c_d_id,c_id");
  sql.put("stock","SELECT s_w_id,s_i_id,s_quantity,s_ytd,s_order_cnt,s_remote_cnt FROM stock ORDER BY s_w_id,s_i_id");
  sql.put("orders","SELECT o_w_id,o_d_id,o_id,o_c_id,COALESCE(o_carrier_id,0),o_ol_cnt,o_all_local FROM orders ORDER BY o_w_id,o_d_id,o_id");
  sql.put("new_order","SELECT no_w_id,no_d_id,no_o_id FROM new_order ORDER BY no_w_id,no_d_id,no_o_id");
  sql.put("order_line","SELECT ol_w_id,ol_d_id,ol_o_id,ol_number,ol_i_id,ol_supply_w_id,ol_quantity,ol_amount,ol_dist_info FROM order_line ORDER BY ol_w_id,ol_d_id,ol_o_id,ol_number");
  sql.put("history","SELECT h_c_w_id,h_c_d_id,h_c_id,h_w_id,h_d_id,h_amount,h_data FROM history ORDER BY h_c_w_id,h_c_d_id,h_c_id,h_w_id,h_d_id,h_amount,h_data");
  if(input!=null){
   int district=input.getIntValue("d_id"),cd=input.getString("kind").equals("payment")?input.getIntValue("c_d_id"):district;Map<String,String> predicates=new HashMap<>();predicates.put("district","d_id IN("+district+","+cd+")");predicates.put("customer","c_d_id="+cd);predicates.put("orders","o_d_id="+district+" AND o_id>=3001");predicates.put("new_order","no_d_id="+district+" AND no_o_id>=3001");predicates.put("order_line","ol_d_id="+district+" AND ol_o_id>=3001");predicates.put("history","h_d_id="+district);
   List<String> items=new ArrayList<>();if(input.getJSONArray("lines")!=null)for(Object obj:input.getJSONArray("lines")){int item=((JSONObject)obj).getIntValue("i_id");if(item>0)items.add(Integer.toString(item));}predicates.put("stock",items.isEmpty()?"1=0":"s_i_id IN("+String.join(",",items)+")");
   for(String table:new ArrayList<>(sql.keySet()))if(predicates.containsKey(table))sql.put(table,sql.get(table).replace(" ORDER BY "," WHERE "+predicates.get(table)+" ORDER BY "));
   JSONObject counts=new JSONObject();for(String table:sql.keySet())try(Statement st=c.createStatement();ResultSet rs=st.executeQuery("SELECT COUNT(*)FROM "+table)){rs.next();counts.put(table,rs.getLong(1));}Files.write(out.resolve("global-counts.json"),counts.toJSONString().getBytes("UTF-8"));Files.write(out.resolve("scope.json"),TpccSql.obj("scope","Targeted mutable customer/district/item footprint, new orders/lines, paying-district histories, plus all global entity counts; full eight-table gates are retained separately").toJSONString().getBytes("UTF-8"));
  }
  JSONObject manifest=new JSONObject();
  for(Map.Entry<String,String> e:sql.entrySet()){
   long count=0;Path f=out.resolve(e.getKey()+".jsonl");MessageDigest md=MessageDigest.getInstance("SHA-256");
   try(Statement s=c.createStatement();ResultSet r=s.executeQuery(e.getValue());OutputStream stream=Files.newOutputStream(f)){
    ResultSetMetaData m=r.getMetaData();while(r.next()){
     JSONArray row=new JSONArray();for(int n=1;n<=m.getColumnCount();n++){String v=r.getString(n);int type=m.getColumnType(n);if(v!=null&&(type==Types.DECIMAL||type==Types.NUMERIC))v=new BigDecimal(v).stripTrailingZeros().toPlainString();row.add(v);}
     byte[] line=(row.toJSONString()+"\n").getBytes("UTF-8");stream.write(line);md.update(line);count++;
    }
   }
   StringBuilder hash=new StringBuilder();for(byte b:md.digest())hash.append(String.format("%02x",b&255));manifest.put(e.getKey(),TpccSql.obj("rows",count,"sha256",hash.toString(),"path",f.toString(),"sql",e.getValue()));
  }
  if("jac_tpcc_graph".equals(c.getCatalog())){try(Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT id,arch_type,props,row_version,seq FROM anchors WHERE row_version='java-dirty' ORDER BY id");BufferedWriter log=Files.newBufferedWriter(out.resolve("raw-mutated-anchors.jsonl"))){while(r.next()){JSONArray row=new JSONArray();for(int n=1;n<=5;n++)row.add(r.getString(n));log.write(row.toJSONString());log.newLine();}}}
  Files.write(out.resolve("manifest.json"),manifest.toJSONString().getBytes("UTF-8"));
 }
 public static void main(String[]args)throws Exception{
  Path out=Paths.get(args[1]);Files.createDirectories(out);JSONArray plan=JSON.parseArray(new String(Files.readAllBytes(Paths.get(args[0])),"UTF-8"));
  try(Connection c=DriverManager.getConnection(System.getProperty("experiment.mysql.url"),"root","")){
   state(c,out.resolve("before"));
   try(BufferedWriter log=Files.newBufferedWriter(out.resolve("requests.jsonl"))){
    for(int i=0;i<plan.size();i++){
     JSONObject x=plan.getJSONObject(i);x.put("timestamp","2026-01-02T00:00:00Z");long start=System.nanoTime();JSONObject result=TpccSql.request(c,x);double elapsed=(System.nanoTime()-start)/1e6;
     boolean expectedAbort=x.getBooleanValue("invalid");if(expectedAbort==result.getBooleanValue("success"))throw new IllegalStateException("Transaction outcome differs at"+i);
     log.write(TpccSql.obj("idx",i,"input",x,"result",result,"ms",elapsed,"jdbc_calls",TpccSql.calls,"categories",new LinkedHashMap<>(TpccSql.categories)).toJSONString());log.newLine();log.flush();
    }
   }
   state(c,out.resolve("after"));
  }
 }
}
