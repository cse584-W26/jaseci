import java.sql.*;
import java.nio.file.*;
import java.util.*;
import java.io.*;
import java.lang.management.*;
import com.alibaba.fastjson2.*;
import webridge.wbridge.storedprocedure.SPConfig;
import webridge.wbridge.storedprocedure.invocation.SPInvokeManager;

/** Mutating representative-cell timer: fresh fixture, ten warm and thirty measured calls. */
public class TpccTiming extends AlignedWeBridge {
 static final ThreadMXBean cpu=ManagementFactory.getThreadMXBean();
 static void execute(String[]args)throws Exception{
  Files.createDirectories(out);JSONObject x=JSON.parseObject(new String(Files.readAllBytes(Paths.get(args[0])),"UTF-8"));String phase=args[1];int warm=Integer.parseInt(args[2]),measure=Integer.parseInt(args[3]);
  if(phase.equals("sp")){SPConfig.addConfig(home.resolve("aligned.conf").toFile());System.setProperty("spDefDir",home.resolve("generated/sql").toString());}
  TpccWeBridge.collect(x,"");
  try(Connection c=DriverManager.getConnection(System.getProperty("experiment.mysql.url"),"root","")){
   save("connection-id.json",TpccSql.obj("connection_id",c.getClass().getMethod("getId").invoke(c)));TpccGate.state(c,out.resolve("before"),x);
   final boolean[] enabled={false,false};
   TpccSql.boundary=new TpccSql.Boundary(){public void enter(Connection c)throws Exception{if(phase.equals("sp")){TpccWeBridge.symbols.clear();TpccWeBridge.collect(x,"");SPInvokeManager.beginApi(api);SPInvokeManager.setInvokingSp(true);TpccWeBridge.buffer();enabled[0]=SPInvokeManager.isInvokingSp();}}public void leave(Connection c)throws Exception{if(phase.equals("sp")){enabled[1]=SPInvokeManager.isInvokingSp();SPInvokeManager.endApi();}}};
   try(BufferedWriter log=Files.newBufferedWriter(out.resolve("rows.jsonl"))){
    for(int n=0;n<warm+measure;n++){
     Map<String,Long> before=status(c);save("request-active.json",TpccSql.obj("start_wall_ms",System.currentTimeMillis(),"phase",phase,"iteration",n,"warmup",n<warm,"api",api));long cpuStart=cpu.getCurrentThreadCpuTime(),start=System.nanoTime();JSONObject result=TpccSql.request(c,x);double ms=(System.nanoTime()-start)/1e6,cpuMs=(cpu.getCurrentThreadCpuTime()-cpuStart)/1e6;Files.delete(out.resolve("request-active.json"));Map<String,Long> after=status(c);long questions=after.get("Questions")-before.get("Questions")-1,call=after.get("Com_call_procedure")-before.get("Com_call_procedure");
     JSONObject row=TpccSql.obj("phase",phase,"iteration",n,"warmup",n<warm,"ms",ms,"thread_cpu_ms",cpuMs,"result",result,"jdbc_calls",TpccSql.calls,"categories",new LinkedHashMap<>(TpccSql.categories),"questions",questions,"call_procedure",call,"sp_enabled_start",enabled[0],"sp_enabled_end",enabled[1]);log.write(row.toJSONString());log.newLine();log.flush();
     if(phase.equals("sp")&&(!enabled[0]||!enabled[1]||call!=1||(n>=warm&&questions!=("graph".equals(System.getProperty("experiment.program"))?4:3))))throw new IllegalStateException("Generated procedure inactive or SQL fallback: "+row);
     if(phase.equals("baseline")&&questions!=TpccSql.calls)throw new IllegalStateException("Direct SQL count mismatch");
     if(x.getBooleanValue("invalid")==result.getBooleanValue("success"))throw new IllegalStateException("Wrong transaction outcome");
    }
   }
   TpccGate.state(c,out.resolve("after"),x);
  }
  System.exit(0);
 }
 public static void main(String[]args){try{execute(args);}catch(Throwable e){e.printStackTrace();System.exit(1);}}
}
