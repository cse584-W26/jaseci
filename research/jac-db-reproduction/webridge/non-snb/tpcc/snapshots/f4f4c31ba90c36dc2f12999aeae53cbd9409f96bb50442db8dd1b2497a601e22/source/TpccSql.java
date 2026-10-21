import java.sql.*;
import java.util.*;
import java.math.*;
import com.alibaba.fastjson2.*;

/** Conventional relational transactions with Jac's visible business semantics. */
public class TpccSql {
 static long calls;static LinkedHashMap<String,Long> categories=new LinkedHashMap<>();
 public interface Boundary {void enter(Connection c)throws Exception;void leave(Connection c)throws Exception;}
 static Boundary boundary=new Boundary(){public void enter(Connection c){}public void leave(Connection c){}};
 static void count(String k){calls++;categories.put(k,categories.getOrDefault(k,0L)+1);}
 static PreparedStatement prepare(Connection c,String k,String sql,Object...args)throws Exception{count(k);PreparedStatement p=c.prepareStatement(sql);for(int i=0;i<args.length;i++)p.setObject(i+1,args[i]);return p;}
 static List<List<String>> rows(Connection c,String k,int n,String sql,Object...args)throws Exception{try(PreparedStatement p=prepare(c,k,sql,args);ResultSet r=p.executeQuery()){List<List<String>> out=new ArrayList<>();while(r.next()){List<String> row=new ArrayList<>();for(int i=1;i<=n;i++)row.add(r.getString(i));out.add(row);}return out;}}
 static class PaymentCustomer {final int id;final String credit,data;PaymentCustomer(int i,String c,String d){id=i;credit=c;data=d;}}
 static List<PaymentCustomer> paymentCustomers(Connection c,String k,String sql,Object...args)throws Exception{try(PreparedStatement p=prepare(c,k,sql,args);ResultSet r=p.executeQuery()){List<PaymentCustomer> out=new ArrayList<>();while(r.next())out.add(new PaymentCustomer(r.getInt(1),r.getString(2),r.getString(3)));return out;}}
 static List<String> one(Connection c,String k,int n,String sql,Object...args)throws Exception{List<List<String>> rs=rows(c,k,n,sql,args);return rs.isEmpty()?null:rs.get(0);}
 static void update(Connection c,String k,String sql,Object...args)throws Exception{try(PreparedStatement p=prepare(c,k,sql,args)){p.executeUpdate();}}
 static void command(Connection c,String k,String sql)throws Exception{count(k);try(Statement s=c.createStatement()){s.execute(sql);}}
 // Python round(float,2) rounds the exact binary value, not its shortest decimal spelling.
 static double round(double v){return new BigDecimal(v).setScale(2,RoundingMode.HALF_EVEN).doubleValue();}
 static JSONObject obj(Object...a){JSONObject o=new JSONObject();for(int i=0;i<a.length;i+=2)o.put(a[i].toString(),a[i+1]);return o;}
 static double d(String s){return Double.parseDouble(s);}static int i(String s){return Integer.parseInt(s);}
 static class Abort extends Exception {Abort(String m){super(m);}}
 static JSONObject body(Connection c,JSONObject x)throws Exception{
  int w=x.getIntValue("w_id"),district=x.getIntValue("d_id");if(w==0)w=1;
  if(x.getString("kind").equals("new_order")){
   List<String> wh=one(c,"warehouse",1,"SELECT w_tax FROM warehouse WHERE w_id=?",w);
   List<String> dr=one(c,"district.lock",2,"SELECT d_tax,d_next_o_id FROM district WHERE d_w_id=? AND d_id=? FOR UPDATE",w,district);int order=i(dr.get(1));
   update(c,"district.update","UPDATE district SET d_next_o_id=d_next_o_id+1 WHERE d_w_id=? AND d_id=?",w,district);
   List<String> customer=one(c,"customer",1,"SELECT c_discount FROM customer WHERE c_w_id=? AND c_d_id=? AND c_id=?",w,district,x.getIntValue("c_id"));
   JSONArray lines=x.getJSONArray("lines");int local=1;for(Object l:lines)if(((JSONObject)l).getIntValue("supply_w_id")!=w)local=0;
   update(c,"order.insert","INSERT INTO orders(o_id,o_d_id,o_w_id,o_c_id,o_entry_d,o_carrier_id,o_ol_cnt,o_all_local)VALUES(?,?,?,?,?,NULL,?,?)",order,district,w,x.getIntValue("c_id"),x.getString("timestamp"),lines.size(),local);
   update(c,"new_order.insert","INSERT INTO new_order(no_o_id,no_d_id,no_w_id)VALUES(?,?,?)",order,district,w);
   double total=0;
   for(int num=0;num<lines.size();num++){
    JSONObject l=lines.getJSONObject(num);int item=l.getIntValue("i_id"),sw=l.getIntValue("supply_w_id"),qty=l.getIntValue("quantity");
    List<String> it=one(c,"item",1,"SELECT i_price FROM item WHERE i_id=?",item);if(it==null)throw new Abort("item not found");
    String dist=String.format("s_dist_%02d",district);
    List<String> st=one(c,"stock.lock",5,"SELECT s_quantity,s_ytd,s_order_cnt,s_remote_cnt,"+dist+" FROM stock WHERE s_w_id=? AND s_i_id=? FOR UPDATE",sw,item);if(st==null)throw new Abort("item not found");
    int nq=i(st.get(0))-qty;if(nq<10)nq+=91;
    update(c,"stock.update","UPDATE stock SET s_quantity=?,s_ytd=?,s_order_cnt=?,s_remote_cnt=? WHERE s_w_id=? AND s_i_id=?",nq,i(st.get(1))+qty,i(st.get(2))+1,i(st.get(3))+(sw==w?0:1),sw,item);
    double amount=round(qty*d(it.get(0)));total+=amount;
    update(c,"order_line.insert","INSERT INTO order_line(ol_o_id,ol_d_id,ol_w_id,ol_number,ol_i_id,ol_supply_w_id,ol_delivery_d,ol_quantity,ol_amount,ol_dist_info)VALUES(?,?,?,?,?,?,NULL,?,?,?)",order,district,w,num+1,item,sw,qty,amount,st.get(4));
   }
   return obj("success",true,"o_id",order,"total",round(total*(1-d(customer.get(0)))*(1+d(wh.get(0))+d(dr.get(0)))),"ol_cnt",lines.size());
  }
  if(x.getString("kind").equals("payment")){
   int cd=x.getIntValue("c_d_id");double amount=x.getDoubleValue("amount");
   List<String> wh=one(c,"warehouse.lock",1,"SELECT w_name FROM warehouse WHERE w_id=? FOR UPDATE",w);
   List<String> dr=one(c,"district.lock",1,"SELECT d_name FROM district WHERE d_w_id=? AND d_id=? FOR UPDATE",w,district);
   PaymentCustomer customer;
   if(x.get("c_id")!=null){List<PaymentCustomer> all=paymentCustomers(c,"customer.lock","SELECT c_id,c_credit,c_data FROM customer WHERE c_w_id=? AND c_d_id=? AND c_id=? FOR UPDATE",w,cd,x.getIntValue("c_id"));customer=all.isEmpty()?null:all.get(0);}
   else{List<PaymentCustomer> all=paymentCustomers(c,"customer.by_name","SELECT c_id,c_credit,c_data FROM customer WHERE c_w_id=? AND c_d_id=? AND c_last=? ORDER BY c_first",w,cd,x.getString("c_last"));customer=all.isEmpty()?null:all.get(all.size()/2);}
   if(customer==null)return obj("success",false,"error","customer not found");int cid=customer.id;
   update(c,"warehouse.update","UPDATE warehouse SET w_ytd=w_ytd+? WHERE w_id=?",amount,w);
   update(c,"district.update","UPDATE district SET d_ytd=d_ytd+? WHERE d_w_id=? AND d_id=?",amount,w,district);
   update(c,"customer.update","UPDATE customer SET c_balance=c_balance-?,c_ytd_payment=c_ytd_payment+?,c_payment_cnt=c_payment_cnt+1 WHERE c_w_id=? AND c_d_id=? AND c_id=?",amount,amount,w,cd,cid);
   if(customer.credit.equals("BC")){String text=cid+","+district+","+w+","+Double.toString(round(amount))+"|"+customer.data;if(text.length()>500)text=text.substring(0,500);update(c,"customer.bad_credit","UPDATE customer SET c_data=? WHERE c_w_id=? AND c_d_id=? AND c_id=?",text,w,cd,cid);}
   update(c,"history.insert","INSERT INTO history(h_c_id,h_c_d_id,h_c_w_id,h_d_id,h_w_id,h_date,h_amount,h_data)VALUES(?,?,?,?,?,?,?,?)",cid,cd,w,district,w,x.getString("timestamp"),amount,wh.get(0)+"    "+dr.get(0));
   return obj("success",true,"c_id",cid,"amount",amount);
  }
  throw new IllegalArgumentException("Unknown transaction "+x.getString("kind"));
 }
 static Connection open(java.nio.file.Path out)throws Exception{
  long start=System.nanoTime();Connection c=DriverManager.getConnection(System.getProperty("experiment.mysql.url"),"root","");JSONObject before=environment(c);
  try(Statement statement=c.createStatement()){
   if(!before.getString("session_sql_mode").contains("NO_UNSIGNED_SUBTRACTION"))statement.execute("SET SESSION sql_mode=CONCAT(@@session.sql_mode,',NO_UNSIGNED_SUBTRACTION')");
   statement.execute("SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE");
  }
  JSONObject after=environment(c);java.nio.file.Files.createDirectories(out);java.nio.file.Files.write(out.resolve("connection-environment.json"),obj("initial",before,"effective",after,"setup_ms",(System.nanoTime()-start)/1e6,"timing_boundary","Connection setup outside request timers; same direct and WeBridge session configuration","signedness_compatibility","NO_UNSIGNED_SUBTRACTION preserves Java signed subtraction in generated bitwise integer-parsing expressions").toJSONString().getBytes("UTF-8"));return c;
 }
 static JSONObject environment(Connection c)throws Exception{
  try(Statement statement=c.createStatement();ResultSet r=statement.executeQuery("SELECT @@session.sql_mode,@@global.sql_mode,@@session.tx_isolation,@@session.tx_read_only")){r.next();return obj("session_sql_mode",r.getString(1),"global_sql_mode",r.getString(2),"isolation",r.getString(3),"read_only",r.getString(4));}
 }
 static JSONObject request(Connection c,JSONObject x)throws Exception{
  calls=0;categories.clear();boolean graph="graph".equals(System.getProperty("experiment.program"));if(graph){TpccGraph.bootstrap(c);TpccGraph.prepareIds(x);command(c,"transaction.set","SET SESSION innodb_lock_wait_timeout=10");}
  boundary.enter(c);count("transaction.begin");c.setAutoCommit(false);
  try{JSONObject result=graph?TpccGraph.body(c,x):body(c,x);count("transaction.commit");c.setAutoCommit(true);boundary.leave(c);return result;}
  catch(Abort e){boundary.leave(c);count("transaction.rollback");c.rollback();count("transaction.connection_restore");c.setAutoCommit(true);return obj("success",false,"error",e.getMessage(),"rolled_back",true);}
  catch(Throwable e){try{count("transaction.rollback");c.rollback();}finally{c.setAutoCommit(true);}throw e;}
 }
}
