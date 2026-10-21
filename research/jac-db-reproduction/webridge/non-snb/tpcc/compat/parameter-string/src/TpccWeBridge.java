import java.sql.*;
import java.nio.file.*;
import java.util.*;
import java.io.*;
import java.lang.reflect.*;
import com.alibaba.fastjson2.*;
import org.apache.commons.lang3.SerializationUtils;
import org.apache.commons.lang3.tuple.Pair;
import webridge.wbridge.sql.ResultSetHolder;
import webridge.wbridge.storedprocedure.SPConfig;
import webridge.wbridge.storedprocedure.StoredProcedureManager;
import webridge.wbridge.storedprocedure.invocation.SPInvokeManager;

/** Original WeBridge captures JDBC transaction controls and unchanged transaction bodies. */
public class TpccWeBridge extends AlignedWeBridge {
 static boolean concolic,recording,active;static JSONObject region=new JSONObject();
 static LinkedHashMap<String,Object> symbols=new LinkedHashMap<>();
 static void collect(Object value,String prefix){
  if(value instanceof JSONObject){JSONObject o=(JSONObject)value;for(String key:new TreeSet<>(o.keySet())){Object v=o.get(key);String name=prefix+key;if(v instanceof String){v=new String(((String)v).toCharArray());o.put(key,v);}if(v instanceof Integer){v=Long.valueOf(((Integer)v).longValue());o.put(key,v);}if(v instanceof java.math.BigDecimal){v=Double.valueOf(((Number)v).doubleValue());o.put(key,v);}if(v instanceof String||v instanceof Number)symbols.put(name,v);else if(v!=null)collect(v,name+"_");}}
  else if(value instanceof JSONArray){JSONArray a=(JSONArray)value;for(int i=0;i<a.size();i++){Object v=a.get(i);if(v instanceof String){v=new String(((String)v).toCharArray());a.set(i,v);}if(v instanceof String||v instanceof Number)symbols.put(prefix+i,v);else collect(v,prefix+i+"_");}}
 }
 static void buffer(){for(Map.Entry<String,Object> e:symbols.entrySet()){Object v=e.getValue();String n=e.getKey();SPInvokeManager.storeParam("REQUEST_PARAM_"+n,v);String alias=v instanceof String?"M_L_String__REQUEST_PARAM_"+n:v instanceof Double?"M_D_field_REQUEST_PARAM_"+n+"_java_lang_Double_value":"M_J_field_REQUEST_PARAM_"+n+"_java_lang_Long_value";SPInvokeManager.storeParam(alias,v);}}
 static void cleanup()throws Exception{if(concolic){nativeCall("endConcolic",new Class<?>[]{});concolic=false;}SPInvokeManager.setUsingRecordedRs(false);ResultSetHolder.setInitialized(false);if(recording){SPInvokeManager.endRecording();recording=false;}if(active){SPInvokeManager.endApi();active=false;}}
 static void execute(String[]args)throws Exception{
  Files.createDirectories(out);String mode=args[0];if(mode.equals("synth")){StoredProcedureManager.run(args[1],home.resolve("aligned.conf").toString());return;}
  SPConfig.addConfig(home.resolve("aligned.conf").toFile());System.setProperty("spDefDir",home.resolve("generated/sql").toString());
  JSONObject x=JSON.parseObject(new String(Files.readAllBytes(Paths.get(System.getProperty("experiment.input"))),"UTF-8"));collect(x,"");save("symbol-inputs.json",symbols);
  try(Connection c=TpccSql.open(out)){
   save("connection-id.json",TpccSql.obj("connection_id",c.getClass().getMethod("getId").invoke(c)));
   TpccSql.boundary=new TpccSql.Boundary(){
    public void enter(Connection connection)throws Exception{
     symbols.clear();collect(x,"");region.put("calls_before",TpccSql.calls);
     if(mode.equals("record")){SPInvokeManager.startRecording();recording=true;}
     if(mode.equals("optimized")){SPInvokeManager.beginApi(api);active=true;SPInvokeManager.setInvokingSp(true);buffer();region.put("sp_enabled_at_start",SPInvokeManager.isInvokingSp());}
     if(mode.equals("replay")){region.put("started_wall_ms",System.currentTimeMillis());ResultSetHolder.initialize(Files.readAllBytes(home.resolve("record.bin")));ResultSetHolder.setInitialized(true);SPInvokeManager.setUsingRecordedRs(true);nativeCall("startConcolic",new Class<?>[]{});concolic=true;for(Map.Entry<String,Object> e:symbols.entrySet())nativeCall("symbolize",new Class<?>[]{Object.class,String.class},e.getValue(),"REQUEST_PARAM_"+e.getKey());}
    }
    public void leave(Connection connection)throws Exception{
     long count=TpccSql.calls-region.getLongValue("calls_before");region.put("source_calls",count);
     if(mode.equals("record")){List<Pair<String,Object>> records=SPInvokeManager.getRecordedSqlAndResultSets();if(records==null||records.size()!=count)throw new IllegalStateException("Recorder/source count differs");Files.write(home.resolve("record.bin"),SerializationUtils.serialize((Serializable)records));JSONArray sql=new JSONArray();for(Pair<String,Object> p:records)sql.add(p.getLeft());save("recorded-sql.json",sql);SPInvokeManager.endRecording();recording=false;}
     if(mode.equals("replay")){System.class.getMethod("weBridgeAnalysis",ClassLoader.class).invoke(null,TpccWeBridge.class.getClassLoader());nativeCall("endConcolic",new Class<?>[]{});concolic=false;Path graph=Paths.get("/tmp/webridgeMngr.tmp.sp.string");if(Files.getLastModifiedTime(graph).toMillis()<region.getLongValue("started_wall_ms"))throw new IllegalStateException("Stale native graph");Files.copy(graph,out.resolve("graph.json"));Field f=ResultSetHolder.class.getDeclaredField("nextRsId");f.setAccessible(true);region.put("recorded_results_consumed",f.getInt(null));if(f.getInt(null)!=count)throw new IllegalStateException("Replay/source count differs");SPInvokeManager.setUsingRecordedRs(false);ResultSetHolder.setInitialized(false);}
     if(mode.equals("optimized")){region.put("sp_enabled_at_end",SPInvokeManager.isInvokingSp());SPInvokeManager.endApi();active=false;}
    }
   };
   Map<String,Long> before=status(c);save("request-active.json",TpccSql.obj("start_wall_ms",System.currentTimeMillis(),"phase",mode,"iteration",0,"warmup",false,"api",api));long start=System.nanoTime();JSONObject result=TpccSql.request(c,x);double ms=(System.nanoTime()-start)/1e6;Files.delete(out.resolve("request-active.json"));Map<String,Long> after=status(c);JSONObject report=TpccSql.obj("mode",mode,"result",result,"ms",ms,"jdbc_calls",TpccSql.calls,"categories",TpccSql.categories,"region",region,"session_status_delta",delta(before,after),"server_questions",after.get("Questions")-before.get("Questions")-1);save("report.json",report);System.out.println(report);
   if(!mode.equals("optimized")&&!mode.equals("replay")&&report.getLongValue("server_questions")!=TpccSql.calls)throw new IllegalStateException("Independent SQL count mismatch");
  }finally{cleanup();}
 }
 public static void main(String[]args){try{execute(args);System.exit(0);}catch(Throwable e){e.printStackTrace();try{cleanup();save("error.json",TpccSql.obj("type",e.getClass().getName(),"message",e.toString()));}catch(Throwable x){e.addSuppressed(x);}System.exit(1);}}
}
