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

/** Original WeBridge around a transaction body; BEGIN/COMMIT/ROLLBACK stay outside. */
public class LittleXWeBridge extends AlignedWeBridge {
 static Class<?> implementation;static boolean selected;static long sourceCalls;static boolean concolic,recording,active;static JSONObject region=new JSONObject();
 static LinkedHashMap<String,Object> symbols=new LinkedHashMap<>();
 static void collect(Object value,String prefix){
  if(value instanceof JSONObject){JSONObject o=(JSONObject)value;for(String key:new TreeSet<>(o.keySet())){Object v=o.get(key);String name=prefix+key;if(v instanceof Integer){v=Long.valueOf(((Integer)v).longValue());o.put(key,v);}if(v instanceof java.math.BigDecimal){v=Double.valueOf(((Number)v).doubleValue());o.put(key,v);}if(v instanceof String||v instanceof Number)symbols.put(name,v);else if(v!=null)collect(v,name+"_");}}
  else if(value instanceof JSONArray){JSONArray a=(JSONArray)value;for(int i=0;i<a.size();i++)collect(a.get(i),prefix+i+"_");}
 }
 static void buffer(){for(Map.Entry<String,Object> e:symbols.entrySet()){Object v=e.getValue();String n=e.getKey();SPInvokeManager.storeParam("REQUEST_PARAM_"+n,v);String alias=v instanceof String?"M_L_String__REQUEST_PARAM_"+n:v instanceof Double?"M_D_field_REQUEST_PARAM_"+n+"_java_lang_Double_value":"M_J_field_REQUEST_PARAM_"+n+"_java_lang_Long_value";SPInvokeManager.storeParam(alias,v);}}
 static void cleanup()throws Exception{if(concolic){nativeCall("endConcolic",new Class<?>[]{});concolic=false;}SPInvokeManager.setUsingRecordedRs(false);ResultSetHolder.setInitialized(false);if(recording){SPInvokeManager.endRecording();recording=false;}if(active){SPInvokeManager.endApi();active=false;}}
 static long calls()throws Exception{return implementation.getField("commands").getLong(null);}
 static void execute(String[]args)throws Exception{
  Files.createDirectories(out);String mode=args[0];if(mode.equals("synth")){StoredProcedureManager.run(args[1],home.resolve("aligned.conf").toString());return;}
  SPConfig.addConfig(home.resolve("aligned.conf").toFile());System.setProperty("spDefDir",home.resolve("generated/sql").toString());
  implementation=Class.forName(System.getProperty("littlex.implementation","LittleXSql"));
  JSONObject x=JSON.parseObject(new String(Files.readAllBytes(Paths.get(System.getProperty("experiment.input"))),"UTF-8"));collect(x,"");save("symbol-inputs.json",symbols);
  try(Connection c=DriverManager.getConnection(System.getProperty("experiment.mysql.url"),"root","")){
   save("sql-mode.json",LittleXSql.configureConnection(c));
   save("connection-id.json",LittleXSql.obj("connection_id",c.getClass().getMethod("getId").invoke(c)));
   implementation.getField("boundary").set(null,new LittleXSql.Boundary(){
    public void enter(Connection connection)throws Exception{
     String wanted=System.getProperty("littlex.region","");String current="";try{current=(String)implementation.getField("region").get(null);}catch(NoSuchFieldException ignored){}selected=wanted.isEmpty()||wanted.equals(current);if(!selected)return;region.put("selected_region",current);region.put("calls_before",calls());
     if(mode.equals("record")){SPInvokeManager.startRecording();recording=true;}
     if(mode.equals("optimized")){SPInvokeManager.beginApi(api);active=true;SPInvokeManager.setInvokingSp(true);buffer();region.put("sp_enabled_at_start",SPInvokeManager.isInvokingSp());}
     if(mode.equals("replay")){region.put("started_wall_ms",System.currentTimeMillis());ResultSetHolder.initialize(Files.readAllBytes(home.resolve("record.bin")));ResultSetHolder.setInitialized(true);SPInvokeManager.setUsingRecordedRs(true);nativeCall("startConcolic",new Class<?>[]{});concolic=true;for(Map.Entry<String,Object> e:symbols.entrySet())nativeCall("symbolize",new Class<?>[]{Object.class,String.class},e.getValue(),"REQUEST_PARAM_"+e.getKey());}
    }
    public void leave(Connection connection)throws Exception{
     if(!selected)return;long count=calls()-region.getLongValue("calls_before");region.put("source_calls",count);
     if(mode.equals("record")){List<Pair<String,Object>> records=SPInvokeManager.getRecordedSqlAndResultSets();if(records==null||records.size()!=count)throw new IllegalStateException("Recorder/source count differs");Files.write(home.resolve("record.bin"),SerializationUtils.serialize((Serializable)records));JSONArray sql=new JSONArray();for(Pair<String,Object> p:records)sql.add(p.getLeft());save("recorded-sql.json",sql);SPInvokeManager.endRecording();recording=false;}
     if(mode.equals("replay")){System.class.getMethod("weBridgeAnalysis",ClassLoader.class).invoke(null,LittleXWeBridge.class.getClassLoader());nativeCall("endConcolic",new Class<?>[]{});concolic=false;Path graph=Paths.get("/tmp/webridgeMngr.tmp.sp.string");if(Files.getLastModifiedTime(graph).toMillis()<region.getLongValue("started_wall_ms"))throw new IllegalStateException("Stale native graph");Files.copy(graph,out.resolve("graph.json"));Field f=ResultSetHolder.class.getDeclaredField("nextRsId");f.setAccessible(true);region.put("recorded_results_consumed",f.getInt(null));if(f.getInt(null)!=count)throw new IllegalStateException("Replay/source count differs");SPInvokeManager.setUsingRecordedRs(false);ResultSetHolder.setInitialized(false);}
     if(mode.equals("optimized")){region.put("sp_enabled_at_end",SPInvokeManager.isInvokingSp());SPInvokeManager.endApi();active=false;}
    }
   });
   Map<String,Long> before=status(c);long start=System.nanoTime();save("request-active.json",LittleXSql.obj("start_wall_ms",System.currentTimeMillis(),"phase",mode));JSONObject result=(JSONObject)implementation.getMethod("request",Connection.class,JSONObject.class).invoke(null,c,x);Files.deleteIfExists(out.resolve("request-active.json"));double ms=(System.nanoTime()-start)/1e6;Map<String,Long> after=status(c);JSONObject report=LittleXSql.obj("mode",mode,"result",result,"ms",ms,"jdbc_calls",calls(),"categories",implementation.getField("sqlLog").get(null),"region",region,"session_status_delta",delta(before,after),"server_questions",after.get("Questions")-before.get("Questions")-1);save("report.json",report);System.out.println(report);
   if(!mode.equals("optimized")&&!mode.equals("replay")&&report.getLongValue("server_questions")!=calls())throw new IllegalStateException("Independent SQL count mismatch");
  }finally{cleanup();}
 }
 public static void main(String[]args){try{execute(args);System.exit(0);}catch(Throwable e){e.printStackTrace();try{cleanup();save("error.json",LittleXSql.obj("type",e.getClass().getName(),"message",e.toString()));}catch(Throwable x){e.addSuppressed(x);}System.exit(1);}}
}
