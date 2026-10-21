import java.sql.*;
import java.nio.file.*;
import java.util.*;
import java.io.*;
import com.alibaba.fastjson2.*;
import webridge.wbridge.storedprocedure.SPConfig;
import webridge.wbridge.storedprocedure.invocation.SPInvokeManager;

/** Whole original plan: selected genuine compiled shapes plus explicit source fallback. */
public class TpccMixed extends AlignedWeBridge {
 static void execute(String[]args)throws Exception{
  Files.createDirectories(out);JSONArray plan=JSON.parseArray(new String(Files.readAllBytes(Paths.get(args[0])),"UTF-8"));JSONObject cases=JSON.parseObject(new String(Files.readAllBytes(Paths.get(args[1])),"UTF-8"));
  for(String key:cases.keySet()){Path home=Paths.get(cases.getString(key));SPConfig.addConfig(home.resolve("aligned.conf").toFile());}
  try(Connection c=DriverManager.getConnection(System.getProperty("experiment.mysql.url"),"root","")){
   save("connection-id.json",TpccSql.obj("connection_id",c.getClass().getMethod("getId").invoke(c)));TpccGate.state(c,out.resolve("before"));
   try(BufferedWriter log=Files.newBufferedWriter(out.resolve("requests.jsonl"))){
    for(int n=0;n<plan.size();n++){
     JSONObject x=plan.getJSONObject(n);x.put("timestamp","2026-01-02T00:00:00Z");String shape;
     if(x.getString("kind").equals("new_order"))shape=x.getBooleanValue("invalid")?"new_order_rollback":"new_order_"+x.getJSONArray("lines").size();
     else shape=x.get("c_id")==null?"payment_name_GC":"payment_id_GC";
     Path selected=cases.getString(shape)==null?null:Paths.get(cases.getString(shape));
     if(selected!=null&&shape.equals("new_order_rollback")){
      JSONObject exemplar=JSON.parseObject(new String(Files.readAllBytes(Paths.get(JSON.parseObject(new String(Files.readAllBytes(selected.resolve("metadata.json")),"UTF-8")).getString("snapshot")).resolve("input.json")),"UTF-8"));if(exemplar.getJSONArray("lines").size()!=x.getJSONArray("lines").size())selected=null;
     }
     final JSONObject metadata=selected==null?null:JSON.parseObject(new String(Files.readAllBytes(selected.resolve("metadata.json")),"UTF-8"));final Path selectedCase=selected;final boolean[] enabled={false,false};
     TpccSql.boundary=new TpccSql.Boundary(){public void enter(Connection connection)throws Exception{if(metadata!=null){TpccWeBridge.symbols.clear();TpccWeBridge.collect(x,"");System.setProperty("spDefDir",selectedCase.resolve("generated/sql").toString());SPInvokeManager.beginApi(metadata.getString("api"));SPInvokeManager.setInvokingSp(true);TpccWeBridge.buffer();enabled[0]=SPInvokeManager.isInvokingSp();}}public void leave(Connection connection)throws Exception{if(metadata!=null){enabled[1]=SPInvokeManager.isInvokingSp();SPInvokeManager.endApi();}}};
     Map<String,Long> before=status(c);save("request-active.json",TpccSql.obj("start_wall_ms",System.currentTimeMillis(),"phase","mixed","iteration",n,"warmup",n<100,"api",metadata==null?null:metadata.getString("api")));long start=System.nanoTime();JSONObject result=TpccSql.request(c,x);double ms=(System.nanoTime()-start)/1e6;Files.delete(out.resolve("request-active.json"));Map<String,Long> after=status(c);long calls=after.get("Com_call_procedure")-before.get("Com_call_procedure");
     JSONObject row=TpccSql.obj("idx",n,"warmup",n<100,"shape",shape,"selected_case",selected==null?null:selected.toString(),"result",result,"ms",ms,"jdbc_calls",TpccSql.calls,"questions",after.get("Questions")-before.get("Questions")-1,"call_procedure",calls,"sp_enabled_start",enabled[0],"sp_enabled_end",enabled[1],"execution",selected==null?"source fallback: no compiled shape":enabled[1]&&calls==1?"generated procedure active":"source fallback: original WeBridge runtime disabled compiled path","categories",new LinkedHashMap<>(TpccSql.categories));log.write(row.toJSONString());log.newLine();log.flush();if(x.getBooleanValue("invalid")==result.getBooleanValue("success"))throw new IllegalStateException("Transaction outcome differs at"+n);
    }
   }
   TpccGate.state(c,out.resolve("after"));
  }
 }
 public static void main(String[]args){try{execute(args);System.exit(0);}catch(Throwable e){e.printStackTrace();System.exit(1);}}
}
