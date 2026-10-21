import java.sql.*;
import java.nio.file.*;
import java.util.*;
import java.io.*;
import java.math.*;
import java.security.*;
import com.alibaba.fastjson2.*;

/** Oracle only: one graph scan, explicit parent dependencies, canonical business sorting. */
public class TpccGraphState {
 static String value(JSONObject p,String key){return p.getString(key);}
 static String money(JSONObject p,String key){return new BigDecimal(p.getString(key)).setScale(2,RoundingMode.HALF_UP).stripTrailingZeros().toPlainString();}
 static String[] row(String... values){return values;}
 static void state(Connection c,Path out)throws Exception{
  Files.createDirectories(out);long start=System.nanoTime();Map<String,String> parents=new HashMap<>();Map<String,String[]> customers=new HashMap<>(),orders=new HashMap<>(),districts=new HashMap<>();Map<String,String[]> deferredLines=new HashMap<>(),deferredHistories=new HashMap<>();Map<String,List<String[]>> tables=new LinkedHashMap<>();for(String name:new String[]{"warehouse","district","customer","stock","orders","new_order","order_line","history"})tables.put(name,new ArrayList<String[]>());
  long scanned=0;String query="SELECT id,arch_type,props,src,dst,src_type,dst_type FROM anchors WHERE arch_type IN('Warehouse','District','Customer','Stock','Order','OrderLine','History','GenericEdge')";
  try(Statement s=c.createStatement(ResultSet.TYPE_FORWARD_ONLY,ResultSet.CONCUR_READ_ONLY)){
   s.setFetchSize(Integer.MIN_VALUE);try(ResultSet rs=s.executeQuery(query)){while(rs.next()){
    scanned++;String id=rs.getString(1),type=rs.getString(2);if(type.equals("GenericEdge")){String src=rs.getString(6),dst=rs.getString(7);if(("District".equals(src)&&"Customer".equals(dst))||("Order".equals(src)&&"OrderLine".equals(dst))||("Customer".equals(src)&&"History".equals(dst)))parents.put(rs.getString(5),rs.getString(4));continue;}JSONObject p=JSON.parseObject(rs.getString(3)).getJSONObject("archetype");String[] r;
    switch(type){
     case "Warehouse":tables.get("warehouse").add(row(value(p,"w_id"),money(p,"w_ytd")));break;
     case "District":r=row("1",value(p,"d_id"),money(p,"d_ytd"),value(p,"d_next_o_id"));districts.put(id,r);tables.get("district").add(r);break;
     case "Customer":r=row("1",null,value(p,"c_id"),money(p,"c_balance"),money(p,"c_ytd_payment"),value(p,"c_payment_cnt"),value(p,"c_data"));customers.put(id,r);tables.get("customer").add(r);break;
     case "Stock":tables.get("stock").add(row("1",value(p,"s_i_id"),value(p,"s_quantity"),value(p,"s_ytd"),value(p,"s_order_cnt"),value(p,"s_remote_cnt")));break;
     case "Order":r=row("1",value(p,"o_d_id"),value(p,"o_id"),value(p,"o_c_id"),p.get("o_carrier_id")==null?"0":value(p,"o_carrier_id"),value(p,"o_ol_cnt"),value(p,"o_all_local"));orders.put(id,r);tables.get("orders").add(r);if(p.getBooleanValue("new_order"))tables.get("new_order").add(row("1",r[1],r[2]));break;
     case "OrderLine":deferredLines.put(id,row("1",null,null,value(p,"ol_number"),value(p,"ol_i_id"),value(p,"ol_supply_w_id"),value(p,"ol_quantity"),money(p,"ol_amount"),value(p,"ol_dist_info")));break;
     case "History":deferredHistories.put(id,row("1",null,null,value(p,"h_w_id"),value(p,"h_d_id"),money(p,"h_amount"),value(p,"h_data")));break;
    }
   }}}
  long scanNanos=System.nanoTime()-start;
  for(Map.Entry<String,String[]> e:customers.entrySet()){String[] parent=districts.get(parents.get(e.getKey()));if(parent==null)throw new IllegalStateException("Missing Customer District "+e.getKey());e.getValue()[1]=parent[1];}
  for(Map.Entry<String,String[]> e:deferredLines.entrySet()){String[] parent=orders.get(parents.get(e.getKey()));if(parent==null)throw new IllegalStateException("Missing OrderLine Order "+e.getKey());String[] r=e.getValue();r[1]=parent[1];r[2]=parent[2];tables.get("order_line").add(r);}
  for(Map.Entry<String,String[]> e:deferredHistories.entrySet()){String[] parent=customers.get(parents.get(e.getKey()));if(parent==null)throw new IllegalStateException("Missing History Customer "+e.getKey());String[] r=e.getValue();r[1]=parent[1];r[2]=parent[2];tables.get("history").add(r);}
  JSONObject manifest=new JSONObject(),timing=new JSONObject();int[] keys={1,2,3,2,3,3,4,7};int index=0;
  for(Map.Entry<String,List<String[]>> entry:tables.entrySet()){
   long began=System.nanoTime();final String table=entry.getKey();final int count=keys[index++];Collections.sort(entry.getValue(),new Comparator<String[]>(){public int compare(String[]a,String[]b){for(int i=0;i<count;i++){int n=table.equals("history")&&i==6?a[i].compareTo(b[i]):new BigDecimal(a[i]).compareTo(new BigDecimal(b[i]));if(n!=0)return n;}return 0;}});
   Path f=out.resolve(table+".jsonl");MessageDigest digest=MessageDigest.getInstance("SHA-256");try(OutputStream stream=Files.newOutputStream(f)){for(String[]r:entry.getValue()){byte[]line=(JSON.toJSONString(r)+"\n").getBytes("UTF-8");stream.write(line);digest.update(line);}}
   StringBuilder hash=new StringBuilder();for(byte b:digest.digest())hash.append(String.format("%02x",b&255));manifest.put(table,TpccSql.obj("rows",entry.getValue().size(),"sha256",hash.toString(),"path",f.toString(),"sql",query));timing.put(table,(System.nanoTime()-began)/1e6);
  }
  Files.write(out.resolve("manifest.json"),manifest.toJSONString().getBytes("UTF-8"));Files.write(out.resolve("streaming-oracle-timing.json"),TpccSql.obj("scan_rows",scanned,"scan_ms",scanNanos/1e6,"total_ms",(System.nanoTime()-start)/1e6,"projection_sort_write_ms",timing,"scope","Full eight mutable relations, all original business fields and dependencies").toJSONString().getBytes("UTF-8"));
 }
 public static void main(String[]args)throws Exception{try(Connection c=DriverManager.getConnection(System.getProperty("experiment.mysql.url"),"root","")){state(c,Paths.get(args[0]));}}
}
