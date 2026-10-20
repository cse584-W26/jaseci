import java.sql.*;
import java.util.*;
import java.nio.file.*;
import java.io.*;
import java.lang.reflect.*;
import java.security.MessageDigest;
import com.alibaba.fastjson2.*;
import org.apache.commons.lang3.SerializationUtils;
import org.apache.commons.lang3.tuple.Pair;
import webridge.wbridge.storedprocedure.SPConfig;
import webridge.wbridge.storedprocedure.StoredProcedureManager;
import webridge.wbridge.storedprocedure.invocation.SPInvokeManager;
import webridge.wbridge.sql.ResultSetHolder;

/** Original WeBridge lifecycle around the independently validated ReplayCompatibleAlignedIc5.request. */
public class CompatibleWeBridge {
 static Path home=Paths.get(System.getProperty("integration.dir"));
 static Path out=Paths.get(System.getProperty("execution.dir"));
 static String scope=System.getProperty("integration.scope","cold");
 static String api=System.getProperty("integration.api");
 static String fingerprint(Path p)throws Exception{
  if(!Files.exists(p))return null;byte[] bytes=MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p));StringBuilder s=new StringBuilder();for(byte b:bytes)s.append(String.format("%02x",b&255));return s.toString();
 }
 static void save(String file,Object value)throws Exception{Files.write(out.resolve(file),JSON.toJSONString(value).getBytes("UTF-8"));}
 static JSONObject state(){JSONObject s=new JSONObject();s.put("schemaReady",ReplayCompatibleAlignedIc5.schemaReady);s.put("knownTypes",new ArrayList<>(new TreeSet<>(ReplayCompatibleAlignedIc5.knownTypes)));s.put("clientRootContext",new TreeMap<>(ReplayCompatibleAlignedIc5.clientRootContext));return s;}
 static void restore(JSONObject s){ReplayCompatibleAlignedIc5.schemaReady=s.getBooleanValue("schemaReady");ReplayCompatibleAlignedIc5.knownTypes.clear();for(Object x:s.getJSONArray("knownTypes"))ReplayCompatibleAlignedIc5.knownTypes.add(x.toString());ReplayCompatibleAlignedIc5.clientRootContext.clear();JSONObject m=s.getJSONObject("clientRootContext");for(String k:m.keySet())ReplayCompatibleAlignedIc5.clientRootContext.put(k,m.getString(k));}
 static Map<String,Long> status(Connection c)throws Exception{
  Map<String,Long> s=new TreeMap<>();try(Statement p=c.createStatement();ResultSet r=p.executeQuery("SHOW SESSION STATUS WHERE Variable_name IN ('Questions','Queries','Com_select','Com_call_procedure','Com_stmt_execute','Com_begin','Com_commit','Bytes_received','Bytes_sent')")){while(r.next())s.put(r.getString(1),r.getLong(2));}return s;
 }
 static JSONObject delta(Map<String,Long> a,Map<String,Long>b){JSONObject d=new JSONObject();for(String k:a.keySet())d.put(k,b.get(k)-a.get(k));return d;}
 static void nativeCall(String name,Class<?>[] types,Object...a)throws Exception{try{System.class.getMethod(name,types).invoke(null,a);}catch(InvocationTargetException e){throw new RuntimeException("Original JVM native boundary "+name,e.getCause());}}
 static JSONObject info()throws Exception{
  JSONObject j=new JSONObject();j.put("alignedSource",System.getProperty("aligned.source"));j.put("alignedSourceSha256",fingerprint(Paths.get(System.getProperty("aligned.source"))));j.put("scope",scope);j.put("api",api);j.put("javaVersion",System.getProperty("java.version"));j.put("javaVm",System.getProperty("java.vm.name"));
  JSONObject origins=new JSONObject();for(String n:new String[]{"ReplayCompatibleAlignedIc5","com.mysql.jdbc.Driver","com.mysql.jdbc.PreparedStatement","webridge.wbridge.storedprocedure.invocation.SPInvokeManager","webridge.wbridge.storedprocedure.StoredProcedureManager"}){Class<?> c=Class.forName(n);origins.put(n,c.getProtectionDomain().getCodeSource()==null?"bootstrap":c.getProtectionDomain().getCodeSource().getLocation().toString());}j.put("classOrigins",origins);return j;
 }
 static String suffix(int idx){return scope+"-"+idx;}
 static List<List<Object>> request(Connection c,JSONObject x)throws Exception{return ReplayCompatibleAlignedIc5.request(c,x);}
 static void parity(List<List<Object>> r,JSONObject x){if(!JSON.toJSONString(r).equals(x.getJSONArray("expected").toJSONString()))throw new IllegalStateException("Oracle mismatch: "+JSON.toJSONString(r)+" vs "+x.getJSONArray("expected"));}
 static void paramBuffer(JSONObject x){SPInvokeManager.storeParam("REQUEST_PARAM_person_jid",x.getString("person_jid"));SPInvokeManager.storeParam("REQUEST_PARAM_min_date",x.getLong("min_date"));SPInvokeManager.storeParam("M_L_String__REQUEST_PARAM_person_jid",x.getString("person_jid"));SPInvokeManager.storeParam("M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value",x.getLong("min_date"));}
 static JSONObject report(String mode,int idx,List<List<Object>> result,double elapsed,Map<String,Long> before,Map<String,Long> after)throws Exception{
  JSONObject r=info();r.put("mode",mode);r.put("idx",idx);r.put("elapsed_ms",elapsed);r.put("source_jdbc_calls",ReplayCompatibleAlignedIc5.calls);r.put("source_categories",new LinkedHashMap<>(ReplayCompatibleAlignedIc5.kinds));r.put("session_status_delta",delta(before,after));r.put("server_questions_excluding_final_observer",after.get("Questions")-before.get("Questions")-1);r.put("result",result);r.put("oracle_ok",true);
  JSONObject unsupported=new JSONObject();for(String k:new String[]{"begin","transaction-setting","commit","rollback"})if(ReplayCompatibleAlignedIc5.kinds.containsKey(k))unsupported.put(k,ReplayCompatibleAlignedIc5.kinds.get(k));r.put("statement_commands_outside_prepared_statement_interceptor",unsupported);return r;
 }
 static void run(String[] args)throws Exception{
  Files.createDirectories(out);String mode=args[0];
  if(mode.equals("inspect")){save("inspection.json",info());System.out.println(info());return;}
  if(mode.equals("synth")){StoredProcedureManager.run(args[1],home.resolve("aligned.conf").toString());save("synthesis-returned.json",info());return;}
  SPConfig.addConfig(home.resolve("aligned.conf").toFile());System.setProperty("spDefDir",home.resolve("generated/sql").toString());
  ReplayCompatibleAlignedIc5.configure(Paths.get(System.getProperty("alignment.dir")));
  JSONArray inputs=JSON.parseArray(new String(Files.readAllBytes(Paths.get(System.getProperty("alignment.dir")).resolve("graph-fixture/inputs.json")),"UTF-8"));int idx=Integer.parseInt(args[1]);JSONObject x=inputs.getJSONObject(idx);
  final String symbolicPerson=x.getString("person_jid");final Long symbolicDate=x.getLong("min_date");
  x.put("person_jid",symbolicPerson);x.put("min_date",symbolicDate);
  if(x.getString("person_jid")!=symbolicPerson || x.getLong("min_date")!=symbolicDate)throw new IllegalStateException("Input getter does not preserve symbolized object identity");
  JSONObject symbolAudit=new JSONObject();symbolAudit.put("obtained_before_startConcolic",true);symbolAudit.put("person_getter_identity",x.getString("person_jid")==symbolicPerson);symbolAudit.put("date_getter_identity",x.getLong("min_date")==symbolicDate);symbolAudit.put("symbol_names",Arrays.asList("REQUEST_PARAM_person_jid","REQUEST_PARAM_min_date"));symbolAudit.put("sp_buffer_names",Arrays.asList("M_L_String__REQUEST_PARAM_person_jid","M_J_field_REQUEST_PARAM_min_date_java_lang_Long_value"));symbolAudit.put("service_identity_assumption","Fixed exported upstream-authenticated service context, not symbolized");save("input-symbol-audit.json",symbolAudit);
  save("invocation.json",info());
  if(mode.equals("input-audit")){
   JSONArray checks=new JSONArray();for(int j=0;j<inputs.size();j++){JSONObject v=inputs.getJSONObject(j);JSONObject row=new JSONObject();row.put("idx",j);row.put("person_raw_is_getter",v.get("person_jid")==v.getString("person_jid"));row.put("date_raw_is_getter",v.get("min_date")==v.getLong("min_date"));row.put("person_class",v.get("person_jid").getClass().getName());row.put("date_class",v.get("min_date").getClass().getName());checks.add(row);if(!row.getBooleanValue("person_raw_is_getter")||!row.getBooleanValue("date_raw_is_getter"))throw new IllegalStateException("Input identity audit failed at "+j);}save("all-input-identities.json",checks);return;
  }
  try(Connection c=DriverManager.getConnection(ReplayCompatibleAlignedIc5.url,"root","")){
   if(mode.equals("replay")){
    restore(JSON.parseObject(new String(Files.readAllBytes(home.resolve("state-before-"+suffix(idx)+".json")),"UTF-8")));
    byte[] recorded=Files.readAllBytes(home.resolve("record-"+suffix(idx)+".bin"));ResultSetHolder.initialize(recorded);ResultSetHolder.setInitialized(true);SPInvokeManager.setUsingRecordedRs(true);
    Map<String,Long> before=status(c);ReplayCompatibleAlignedIc5.calls=0;ReplayCompatibleAlignedIc5.kinds.clear();Path global=Paths.get("/tmp/webridgeMngr.tmp.sp.string");String beforeHash=fingerprint(global);boolean begun=false;long start=System.nanoTime();
    try{
     nativeCall("startConcolic",new Class<?>[]{});begun=true;
     nativeCall("symbolize",new Class<?>[]{Object.class,String.class},symbolicPerson,"REQUEST_PARAM_person_jid");
     nativeCall("symbolize",new Class<?>[]{Object.class,String.class},symbolicDate,"REQUEST_PARAM_min_date");
     List<List<Object>> result=request(c,x);
     String returned=(String)System.class.getMethod("weBridgeAnalysis",ClassLoader.class).invoke(null,CompatibleWeBridge.class.getClassLoader());
     nativeCall("endConcolic",new Class<?>[]{});begun=false;
     Files.write(out.resolve("native-analysis-return.txt"),(returned==null?"":returned).getBytes("UTF-8"));
     String afterHash=fingerprint(global);if(afterHash==null||Objects.equals(beforeHash,afterHash))throw new IllegalStateException("Original engine did not replace global graph file; refusing stale graph");
     Files.copy(global,out.resolve("graph.json"));parity(result,x);
     JSONObject r=report(mode,idx,result,(System.nanoTime()-start)/1e6,before,status(c));r.put("engine_graph_sha256",afterHash);r.put("previous_engine_graph_sha256",beforeHash);Field f=ResultSetHolder.class.getDeclaredField("nextRsId");f.setAccessible(true);r.put("recorded_results_consumed",f.getInt(null));save("report.json",r);System.out.println(r);
    }finally{if(begun)nativeCall("endConcolic",new Class<?>[]{});SPInvokeManager.setUsingRecordedRs(false);ResultSetHolder.setInitialized(false);}
    return;
   }
   if(scope.equals("warm")){request(c,x);}
   JSONObject prior=state();save("state-before.json",prior);
   if(mode.equals("record")){
    Files.write(home.resolve("state-before-"+suffix(idx)+".json"),prior.toJSONString().getBytes("UTF-8"));Map<String,Long> before=status(c);ReplayCompatibleAlignedIc5.calls=0;ReplayCompatibleAlignedIc5.kinds.clear();SPInvokeManager.startRecording();long start=System.nanoTime();
    try{
     List<List<Object>> result=request(c,x);double elapsed=(System.nanoTime()-start)/1e6;parity(result,x);List<Pair<String,Object>> rec=SPInvokeManager.getRecordedSqlAndResultSets();if(rec==null)throw new IllegalStateException("Original SQL recorder returned null; check extended driver origin/interceptor");
     Files.write(home.resolve("record-"+suffix(idx)+".bin"),SerializationUtils.serialize((Serializable)rec));JSONArray sqls=new JSONArray();for(Pair<String,Object> p:rec){JSONObject q=new JSONObject();q.put("sql",p.getLeft());q.put("valueClass",p.getRight()==null?null:p.getRight().getClass().getName());sqls.add(q);}save("recorded-sql.json",sqls);
     JSONObject r=report(mode,idx,result,elapsed,before,status(c));r.put("recorded_items",rec.size());r.put("state_before",prior);save("report.json",r);System.out.println(r);
    }finally{SPInvokeManager.endRecording();}return;
   }
   int n=args.length>2?Integer.parseInt(args[2]):1;for(int i=0;i<n;i++){
    boolean optimized=mode.equals("optimized");Map<String,Long> before=status(c);ReplayCompatibleAlignedIc5.calls=0;ReplayCompatibleAlignedIc5.kinds.clear();boolean atStart=false,atEnd=false;long start=System.nanoTime();List<List<Object>> result;
    try{if(optimized){SPInvokeManager.beginApi(api);SPInvokeManager.setInvokingSp(true);paramBuffer(x);atStart=SPInvokeManager.isInvokingSp();}result=request(c,x);atEnd=SPInvokeManager.isInvokingSp();}finally{if(optimized)SPInvokeManager.endApi();}
    double elapsed=(System.nanoTime()-start)/1e6;parity(result,x);JSONObject r=report(mode,idx,result,elapsed,before,status(c));r.put("iteration",i);r.put("sp_enabled_at_start",atStart);r.put("sp_enabled_at_end",atEnd);save("report-"+i+".json",r);System.out.println(r);
    if(mode.equals("baseline")&&r.getLongValue("server_questions_excluding_final_observer")!=ReplayCompatibleAlignedIc5.calls)throw new IllegalStateException("Independent baseline SQL-count mismatch");
   }
  }
 }
 public static void main(String[] args){try{run(args);if(args[0].equals("optimized"))System.exit(0);}catch(Throwable e){e.printStackTrace();try{JSONObject error=new JSONObject();error.put("type",e.getClass().getName());error.put("message",e.toString());save("error.json",error);}catch(Throwable ignored){}System.exit(1);}}
}
