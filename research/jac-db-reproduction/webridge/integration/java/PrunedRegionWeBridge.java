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
public class PrunedRegionWeBridge extends AlignedWeBridge {
 static boolean concolic=false,recording=false,apiActive=false;
 static JSONObject body=new JSONObject();
 static JSONObject currentState(){JSONObject s=new JSONObject();s.put("schemaReady",RegionCompatiblePrunedIc5.schemaReady);s.put("knownTypes",new ArrayList<>(new TreeSet<>(RegionCompatiblePrunedIc5.knownTypes)));s.put("clientRootContext",new TreeMap<>(RegionCompatiblePrunedIc5.clientRootContext));return s;}
 static void restoreState(JSONObject s){RegionCompatiblePrunedIc5.schemaReady=s.getBooleanValue("schemaReady");RegionCompatiblePrunedIc5.knownTypes.clear();for(Object v:s.getJSONArray("knownTypes"))RegionCompatiblePrunedIc5.knownTypes.add(v.toString());RegionCompatiblePrunedIc5.clientRootContext.clear();JSONObject m=s.getJSONObject("clientRootContext");for(String k:m.keySet())RegionCompatiblePrunedIc5.clientRootContext.put(k,m.getString(k));}
 static JSONObject details(String mode,int idx,List<List<Object>> result,double ms,Map<String,Long> a,Map<String,Long>b)throws Exception{JSONObject j=info();j.put("program","pruned-explicit-body-region");j.put("mode",mode);j.put("idx",idx);j.put("source_jdbc_calls",RegionCompatiblePrunedIc5.calls);j.put("source_categories",new LinkedHashMap<>(RegionCompatiblePrunedIc5.kinds));j.put("session_status_delta",delta(a,b));j.put("server_questions_excluding_final_observer",b.get("Questions")-a.get("Questions")-1);j.put("full_request_ms",ms);j.put("body",body);j.put("result",result);j.put("oracle_ok",true);j.put("compiled_region","After SET and before COMMIT; setup/identity/txn SQL retained outside");return j;}
 static void cleanup()throws Exception{if(concolic){nativeCall("endConcolic",new Class<?>[]{});concolic=false;}SPInvokeManager.setUsingRecordedRs(false);ResultSetHolder.setInitialized(false);if(recording){SPInvokeManager.endRecording();recording=false;}if(apiActive){SPInvokeManager.endApi();apiActive=false;}}
 static void execute(String[] args)throws Exception{
  Files.createDirectories(out);final String mode=args[0];if(mode.equals("synth")){StoredProcedureManager.run(args[1],home.resolve("aligned.conf").toString());return;}
  SPConfig.addConfig(home.resolve("aligned.conf").toFile());System.setProperty("spDefDir",home.resolve("generated/sql").toString());RegionCompatiblePrunedIc5.configure(Paths.get(System.getProperty("alignment.dir")));
  JSONArray all=JSON.parseArray(new String(Files.readAllBytes(Paths.get(System.getProperty("alignment.dir")).resolve("graph-fixture/inputs.json")),"UTF-8"));final int idx=Integer.parseInt(args[1]);final JSONObject x=all.getJSONObject(idx);final String person=x.getString("person_jid");final Long date=x.getLong("min_date");x.put("person_jid",person);x.put("min_date",date);if(x.getString("person_jid")!=person||x.getLong("min_date")!=date)throw new IllegalStateException("Input symbol identity mismatch");
  JSONObject symbols=new JSONObject();symbols.put("obtained_before_startConcolic",true);symbols.put("getter_identity_preserved",true);symbols.put("symbol_names",Arrays.asList("REQUEST_PARAM_person_jid","REQUEST_PARAM_min_date"));symbols.put("sp_buffer_names",Arrays.asList("M_L_String__REQUEST_PARAM_person_jid","M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value"));symbols.put("service_context","Fixed upstream-authenticated fixture service identity");save("input-symbol-audit.json",symbols);
  try(Connection c=DriverManager.getConnection(RegionCompatiblePrunedIc5.url,"root","")){
   save("connection-id.json",c.getClass().getMethod("getId").invoke(c));
   if(mode.equals("replay"))restoreState(JSON.parseObject(new String(Files.readAllBytes(home.resolve("state-before-"+suffix(idx)+".json")),"UTF-8")));
   else if(scope.equals("warm"))RegionCompatiblePrunedIc5.request(c,x);
   JSONObject stateBefore=currentState();save("state-before.json",stateBefore);if(mode.equals("record"))Files.write(home.resolve("state-before-"+suffix(idx)+".json"),stateBefore.toJSONString().getBytes("UTF-8"));
   RegionCompatiblePrunedIc5.regionBoundary=new RegionCompatiblePrunedIc5.RegionBoundary(){
    public void enter(Connection connection)throws Exception{
     body=new JSONObject();body.put("source_calls_before",RegionCompatiblePrunedIc5.calls);
     if(mode.equals("record")){SPInvokeManager.startRecording();recording=true;}
     if(mode.equals("optimized")){SPInvokeManager.beginApi(api);apiActive=true;SPInvokeManager.setInvokingSp(true);paramBuffer(x);body.put("sp_enabled_at_start",SPInvokeManager.isInvokingSp());}
     if(mode.equals("replay")){ResultSetHolder.initialize(Files.readAllBytes(home.resolve("record-"+suffix(idx)+".bin")));ResultSetHolder.setInitialized(true);SPInvokeManager.setUsingRecordedRs(true);nativeCall("startConcolic",new Class<?>[]{});concolic=true;nativeCall("symbolize",new Class<?>[]{Object.class,String.class},person,"REQUEST_PARAM_person_jid");nativeCall("symbolize",new Class<?>[]{Object.class,String.class},date,"REQUEST_PARAM_min_date");}
    }
    public void leave(Connection connection)throws Exception{
     body.put("body_source_calls",RegionCompatiblePrunedIc5.calls-body.getLongValue("source_calls_before"));
     if(mode.equals("record")){List<Pair<String,Object>> rec=SPInvokeManager.getRecordedSqlAndResultSets();if(rec==null)throw new IllegalStateException("No original body records");Files.write(home.resolve("record-"+suffix(idx)+".bin"),SerializationUtils.serialize((Serializable)rec));JSONArray qs=new JSONArray();for(Pair<String,Object> p:rec)qs.add(p.getLeft());save("recorded-sql.json",qs);body.put("recorded_items",rec.size());SPInvokeManager.endRecording();recording=false;}
     if(mode.equals("optimized")){body.put("sp_enabled_at_end",SPInvokeManager.isInvokingSp());SPInvokeManager.endApi();apiActive=false;}
     if(mode.equals("replay")){
      String returned=(String)System.class.getMethod("weBridgeAnalysis",ClassLoader.class).invoke(null,PrunedRegionWeBridge.class.getClassLoader());nativeCall("endConcolic",new Class<?>[]{});concolic=false;
      Path graph=Paths.get("/tmp/webridgeMngr.tmp.sp.string");Files.copy(graph,out.resolve("graph.json"));body.put("graph_bytes",Files.size(graph));body.put("analysis_return_chars",returned==null?0:returned.length());Field f=ResultSetHolder.class.getDeclaredField("nextRsId");f.setAccessible(true);body.put("recorded_results_consumed",f.getInt(null));SPInvokeManager.setUsingRecordedRs(false);ResultSetHolder.setInitialized(false);
     }
    }
   };
   int repeats=args.length>2?Integer.parseInt(args[2]):1;
   for(int i=0;i<repeats;i++){Map<String,Long> before=status(c);RegionCompatiblePrunedIc5.calls=0;RegionCompatiblePrunedIc5.kinds.clear();long t=System.nanoTime();List<List<Object>> result=RegionCompatiblePrunedIc5.request(c,x);double elapsed=(System.nanoTime()-t)/1e6;parity(result,x);JSONObject report=details(mode,idx,result,elapsed,before,status(c));report.put("iteration",i);save("report-"+i+".json",report);System.out.println(report);if(!mode.equals("optimized")&&!mode.equals("replay")&&report.getLongValue("server_questions_excluding_final_observer")!=RegionCompatiblePrunedIc5.calls)throw new IllegalStateException("Full request independent SQL-count mismatch");}
  }finally{cleanup();}
 }
 public static void main(String[] args){try{execute(args);if(args[0].equals("optimized"))System.exit(0);}catch(Throwable e){e.printStackTrace();try{cleanup();JSONObject error=new JSONObject();error.put("type",e.getClass().getName());error.put("message",e.toString());save("error.json",error);}catch(Throwable suppressed){e.addSuppressed(suppressed);}System.exit(1);}}
}
