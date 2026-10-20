import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.sql.*;
import java.util.*;
import java.lang.management.*;
import com.alibaba.fastjson2.*;

/** Conventional typed JDBC + one SQL aggregate, over the declared directed SNB fixture. */
public class IdiomaticIc5 {
  static String query;
  static long calls;
  static void command(Connection c,String q)throws Exception {calls++;try(Statement s=c.createStatement()){s.execute(q);}}
  public static List<List<Object>> request(Connection c,JSONObject input)throws Exception {
    calls=0;
    command(c,"START TRANSACTION READ ONLY");
    command(c,"SET SESSION innodb_lock_wait_timeout=10");
    try {
      List<List<Object>> answer=new ArrayList<>();calls++;
      try(PreparedStatement s=c.prepareStatement(query)) {
        s.setString(1,input.getString("person_jid"));s.setString(2,input.getString("person_jid"));s.setLong(3,input.getLongValue("min_date"));
        try(ResultSet r=s.executeQuery()){while(r.next())answer.add(Arrays.<Object>asList(r.getLong(1),r.getString(2),r.getLong(3)));}
      }
      command(c,"COMMIT");return answer;
    }catch(Exception e){command(c,"ROLLBACK");throw e;}
  }
  static long questions(Connection c)throws Exception {try(Statement s=c.createStatement();ResultSet r=s.executeQuery("SHOW SESSION STATUS LIKE 'Questions'")){r.next();return r.getLong(2);}}
  static JSONObject statuses(Connection c)throws Exception {
    JSONObject answer=new JSONObject();try(Statement s=c.createStatement();ResultSet r=s.executeQuery("SHOW SESSION STATUS WHERE Variable_name IN('Questions','Queries','Com_select','Com_begin','Com_commit','Com_call_procedure')")){while(r.next())answer.put(r.getString(1),r.getLong(2));}return answer;
  }
  static void fixtureGate(Connection c)throws Exception {
    try(Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT COUNT(*) FROM anchors WHERE undirected<>0 AND arch_type IN('HasMember','ContainerOf','HasCreator')")){r.next();if(r.getLong(1)!=0)throw new IllegalStateException("Directed membership/container/creator fixture invariant failed");}
    try(Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT COUNT(*) FROM graph_types WHERE ancestor IN('Person','Forum','Post','Knows','HasMember','ContainerOf','HasCreator') AND type_name<>ancestor")){r.next();if(r.getLong(1)!=0)throw new IllegalStateException("Fixture contains undeclared subtypes");}
    try(Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT COUNT(*) FROM (SELECT hc.src FROM anchors hc JOIN anchors a ON a.id=hc.dst AND a.kind='NodeAnchor' AND a.arch_type='Person' WHERE hc.kind='EdgeAnchor' AND hc.arch_type='HasCreator' AND (hc.dst_type IS NULL OR hc.dst_type='Person') GROUP BY hc.src HAVING COUNT(DISTINCT hc.dst)>1) multiple_authors")){r.next();if(r.getLong(1)!=0)throw new IllegalStateException("Multiple distinct valid creators require first-creator SQL variant");}
    try(Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT COUNT(*),COUNT(DISTINCT CAST(JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.forum_id')) AS SIGNED)) FROM anchors WHERE kind='NodeAnchor' AND arch_type='Forum'")){r.next();if(r.getLong(1)!=r.getLong(2))throw new IllegalStateException("Forum external IDs must be unique and nonnull");}
  }
  public static void main(String[] args)throws Exception {
    // mode alignment-dir output-dir warm measure; target is an independent property.
    String mode=args[0];Path alignment=Paths.get(args[1]),out=Paths.get(args[2]);int warm=Integer.parseInt(args[3]),measure=Integer.parseInt(args[4]);Files.createDirectory(out);
    query=new String(Files.readAllBytes(Paths.get(System.getProperty("idiomatic.sql"))),StandardCharsets.UTF_8);
    String url=System.getProperty("idiomatic.jdbcUrl","jdbc:mysql://127.0.0.1:55337/jac_alignment_utf8?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true");
    ThreadMXBean cpu=ManagementFactory.getThreadMXBean();if(cpu.isCurrentThreadCpuTimeSupported()&&!cpu.isThreadCpuTimeEnabled())cpu.setThreadCpuTimeEnabled(true);
    List<JSONObject> records=new ArrayList<>();
    try(Connection c=DriverManager.getConnection(url,"root","")) {
      fixtureGate(c);Files.write(out.resolve("connection.json"),("{\"connection_id\":"+((Number)c.getClass().getMethod("getId").invoke(c)).longValue()+"}").getBytes(StandardCharsets.UTF_8));
      JSONArray inputs=JSON.parseArray(new String(Files.readAllBytes(alignment.resolve("graph-fixture/inputs.json")),StandardCharsets.UTF_8));
      if(mode.equals("gate"))inputs.add(JSON.parseObject(new String(Files.readAllBytes(alignment.resolve("small-diagnostic/input.json")),StandardCharsets.UTF_8)));
      else {inputs=new JSONArray();inputs.add(JSON.parseObject(new String(Files.readAllBytes(alignment.resolve("small-diagnostic/input.json")),StandardCharsets.UTF_8)));}
      int rounds=mode.equals("gate")?1:warm+measure;
      for(int round=0;round<rounds;round++)for(int i=0;i<inputs.size();i++) {
        JSONObject input=inputs.getJSONObject(i),before=statuses(c);long cp=cpu.getCurrentThreadCpuTime(),start=System.nanoTime();List<List<Object>> result=request(c,input);double ms=(System.nanoTime()-start)/1e6,cpums=(cpu.getCurrentThreadCpuTime()-cp)/1e6;JSONObject after=statuses(c);
        JSONObject row=new JSONObject();row.put("input_index",i);row.put("iteration",round);row.put("warmup",!mode.equals("gate")&&round<warm);row.put("ms",ms);row.put("thread_cpu_ms",cpums);row.put("jdbc_calls",calls);row.put("questions",after.getLongValue("Questions")-before.getLongValue("Questions")-1);row.put("result",result);row.put("expected",input.getJSONArray("expected"));row.put("oracle_ok",JSON.toJSONString(result).equals(input.getJSONArray("expected").toJSONString()));JSONObject delta=new JSONObject();for(String key:after.keySet())delta.put(key,after.getLongValue(key)-before.getLongValue(key));row.put("status_delta",delta);records.add(row);Files.write(out.resolve("rows.jsonl"),(row.toJSONString()+"\n").getBytes(StandardCharsets.UTF_8),StandardOpenOption.CREATE,StandardOpenOption.APPEND);
        if(!row.getBooleanValue("oracle_ok")||calls!=4||row.getLongValue("questions")!=4)throw new IllegalStateException("Result/independent SQL census failed at input "+i+": "+row);
      }
    }
    JSONObject receipt=new JSONObject();receipt.put("mode",mode);receipt.put("rows",records.size());receipt.put("jdbc_url",url);receipt.put("warm",mode.equals("gate")?0:warm);receipt.put("measure",mode.equals("gate")?records.size():measure);receipt.put("fixture_invariants_passed",true);Files.write(out.resolve("completed.json"),receipt.toJSONString().getBytes(StandardCharsets.UTF_8));
  }
}
