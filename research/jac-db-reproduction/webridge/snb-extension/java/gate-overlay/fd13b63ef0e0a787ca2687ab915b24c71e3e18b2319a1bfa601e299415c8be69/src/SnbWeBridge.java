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

/** Explicit frontend API region; all transaction and setup SQL executes normally. */
public class SnbWeBridge extends AlignedWeBridge {
 static boolean concolic=false,recording=false,apiActive=false;
 static JSONObject body=new JSONObject();
 static JSONObject info()throws Exception{JSONObject j=AlignedWeBridge.info();JSONObject origins=j.getJSONObject("classOrigins");origins.remove("AlignedIc5");for(Class<?> cls:new Class<?>[]{SnbAccess.class,SnbWeBridge.class})origins.put(cls.getName(),cls.getProtectionDomain().getCodeSource().getLocation().toString());return j;}
 static JSONObject currentState(){JSONObject s=new JSONObject();s.put("schemaReady",SnbAccess.schemaReady);s.put("knownTypes",new ArrayList<>(new TreeSet<>(SnbAccess.knownTypes)));s.put("clientRootContext",new TreeMap<>(SnbAccess.clientRootContext));return s;}
 static void restoreState(JSONObject s){SnbAccess.schemaReady=s.getBooleanValue("schemaReady");SnbAccess.knownTypes.clear();for(Object v:s.getJSONArray("knownTypes"))SnbAccess.knownTypes.add(v.toString());SnbAccess.clientRootContext.clear();JSONObject m=s.getJSONObject("clientRootContext");for(String k:m.keySet())SnbAccess.clientRootContext.put(k,m.getString(k));}
 static JSONObject details(String mode,int idx,JSONObject result,double ms,Map<String,Long> a,Map<String,Long>b)throws Exception{JSONObject j=info();j.put("program","explicit-body-region");j.put("mode",mode);j.put("idx",idx);j.put("source_jdbc_calls",SnbAccess.calls);j.put("source_categories",new LinkedHashMap<>(SnbAccess.kinds));j.put("session_status_delta",delta(a,b));j.put("server_questions_excluding_final_observer",b.get("Questions")-a.get("Questions")-1);j.put("full_request_ms",ms);j.put("body",body);j.put("result",result);j.put("oracle_ok",true);j.put("compiled_region","After SET and before COMMIT; setup/identity/txn SQL retained outside");return j;}
 static void cleanup()throws Exception{if(concolic){nativeCall("endConcolic",new Class<?>[]{});concolic=false;}SPInvokeManager.setUsingRecordedRs(false);ResultSetHolder.setInitialized(false);if(recording){SPInvokeManager.endRecording();recording=false;}if(apiActive){SPInvokeManager.endApi();apiActive=false;}}
 static void parity(JSONObject result,JSONObject x)throws Exception{if(!SnbAccess.parity(result,x))throw new IllegalStateException("Oracle mismatch: "+result);}
 static void paramBuffer(JSONObject x){for(String key:Arrays.asList("person_jid","person1_jid","person2_jid","first_name","max_date"))if(x.containsKey(key)){Object value=x.get(key);SPInvokeManager.storeParam("REQUEST_PARAM_"+key,value);SPInvokeManager.storeParam((value instanceof Long?"M_J_field_REQUEST_PARAM_"+key+"_java_lang_Long_value":"M_L_String__REQUEST_PARAM_"+key),value);}}
 static void execute(String[] args)throws Exception{
  Files.createDirectories(out);final String mode=args[0];if(mode.equals("synth")){StoredProcedureManager.run(args[1],home.resolve("aligned.conf").toString());return;}
  SPConfig.addConfig(home.resolve("aligned.conf").toFile());System.setProperty("spDefDir",home.resolve("generated/sql").toString());SnbAccess.configure(Paths.get(System.getProperty("alignment.dir")));
  SnbAccess.url=System.getProperty("experiment.mysql.url",SnbAccess.url);
  JSONArray all=JSON.parseArray(new String(Files.readAllBytes(Paths.get(System.getProperty("experiment.inputs"))),"UTF-8"));final int idx=Integer.parseInt(args[1]);final JSONObject x=all.getJSONObject(idx);final Map<String,Object> symbolic=new LinkedHashMap<>();
  for(String key:Arrays.asList("person_jid","person1_jid","person2_jid","first_name","max_date")){if(x.containsKey(key)){Object value=key.equals("max_date")?x.getLong(key):x.getString(key);x.put(key,value);symbolic.put(key,value);}}
  save("input-symbol-audit.json",symbolic);
  try(Connection c=DriverManager.getConnection(SnbAccess.url,"root","")){
   save("connection-id.json",Collections.singletonMap("connection_id",c.getClass().getMethod("getId").invoke(c)));
   if(mode.equals("replay"))restoreState(JSON.parseObject(new String(Files.readAllBytes(home.resolve("state-before-"+suffix(idx)+".json")),"UTF-8")));
   else if(scope.equals("warm"))SnbAccess.request(c,x);
   JSONObject stateBefore=currentState();save("state-before.json",stateBefore);if(mode.equals("record"))Files.write(home.resolve("state-before-"+suffix(idx)+".json"),stateBefore.toJSONString().getBytes("UTF-8"));
   SnbAccess.regionBoundary=new SnbAccess.RegionBoundary(){
    public void enter(Connection connection)throws Exception{
     body=new JSONObject();body.put("source_calls_before",SnbAccess.calls);
     if(mode.equals("record")){SPInvokeManager.startRecording();recording=true;}
     if(mode.equals("optimized")){SPInvokeManager.beginApi(api);apiActive=true;SPInvokeManager.setInvokingSp(true);paramBuffer(x);body.put("sp_enabled_at_start",SPInvokeManager.isInvokingSp());}
     if(mode.equals("replay")){body.put("native_started_wall_ms",System.currentTimeMillis());ResultSetHolder.initialize(Files.readAllBytes(home.resolve("record-"+suffix(idx)+".bin")));ResultSetHolder.setInitialized(true);SPInvokeManager.setUsingRecordedRs(true);nativeCall("startConcolic",new Class<?>[]{});concolic=true;for(Map.Entry<String,Object> entry:symbolic.entrySet())nativeCall("symbolize",new Class<?>[]{Object.class,String.class},entry.getValue(),"REQUEST_PARAM_"+entry.getKey());}
    }
    public void leave(Connection connection)throws Exception{
     body.put("body_source_calls",SnbAccess.calls-body.getLongValue("source_calls_before"));
     if(mode.equals("record")){List<Pair<String,Object>> rec=SPInvokeManager.getRecordedSqlAndResultSets();if(rec==null)throw new IllegalStateException("No original body records");if(rec.size()!=body.getLongValue("body_source_calls"))throw new IllegalStateException("Recorder/source body count mismatch");Files.write(home.resolve("record-"+suffix(idx)+".bin"),SerializationUtils.serialize((Serializable)rec));JSONArray qs=new JSONArray();for(Pair<String,Object> p:rec)qs.add(p.getLeft());save("recorded-sql.json",qs);body.put("recorded_items",rec.size());SPInvokeManager.endRecording();recording=false;}
     if(mode.equals("optimized")){body.put("sp_enabled_at_end",SPInvokeManager.isInvokingSp());SPInvokeManager.endApi();apiActive=false;}
     if(mode.equals("replay")){
      String returned=(String)System.class.getMethod("weBridgeAnalysis",ClassLoader.class).invoke(null,SnbWeBridge.class.getClassLoader());nativeCall("endConcolic",new Class<?>[]{});concolic=false;
      Path graph=Paths.get("/tmp/webridgeMngr.tmp.sp.string");if(Files.getLastModifiedTime(graph).toMillis()<body.getLongValue("native_started_wall_ms"))throw new IllegalStateException("Native graph not refreshed");Files.copy(graph,out.resolve("graph.json"));body.put("graph_bytes",Files.size(graph));body.put("analysis_return_chars",returned==null?0:returned.length());Field f=ResultSetHolder.class.getDeclaredField("nextRsId");f.setAccessible(true);body.put("recorded_results_consumed",f.getInt(null));if(f.getInt(null)!=body.getLongValue("body_source_calls"))throw new IllegalStateException("Replay/source body count mismatch");SPInvokeManager.setUsingRecordedRs(false);ResultSetHolder.setInitialized(false);
     }
    }
   };
   int repeats=args.length>2?Integer.parseInt(args[2]):1;
   for(int i=0;i<repeats;i++){Map<String,Long> before=status(c);SnbAccess.calls=0;SnbAccess.kinds.clear();Path requestMarker=out.resolve("request-active.json");JSONObject active=new JSONObject();active.put("start_mono_ns",System.nanoTime());active.put("start_wall_ms",System.currentTimeMillis());active.put("phase",mode);active.put("iteration",i);active.put("warmup",false);active.put("api",api);Files.write(requestMarker,active.toJSONString().getBytes("UTF-8"));long t=System.nanoTime();JSONObject result=SnbAccess.request(c,x);double elapsed=(System.nanoTime()-t)/1e6;Files.deleteIfExists(requestMarker);parity(result,x);JSONObject report=details(mode,idx,result,elapsed,before,status(c));report.put("iteration",i);save("report-"+i+".json",report);System.out.println(report);if(!mode.equals("optimized")&&!mode.equals("replay")&&report.getLongValue("server_questions_excluding_final_observer")!=SnbAccess.calls)throw new IllegalStateException("Full request independent SQL-count mismatch");}
  }finally{cleanup();}
 }
 public static void main(String[] args){try{execute(args);if(args[0].equals("optimized"))System.exit(0);}catch(Throwable e){e.printStackTrace();try{cleanup();JSONObject error=new JSONObject();error.put("type",e.getClass().getName());error.put("message",e.toString());save("error.json",error);}catch(Throwable suppressed){e.addSuppressed(suppressed);}System.exit(1);}}
}
