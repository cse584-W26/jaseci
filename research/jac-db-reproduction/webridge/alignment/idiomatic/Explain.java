import java.nio.file.*;import java.nio.charset.*;import java.sql.*;import com.alibaba.fastjson2.*;
public class Explain { public static void main(String[] a)throws Exception {
Path h=Paths.get(a[0]);JSONArray inputs=JSON.parseArray(new String(Files.readAllBytes(h.resolve("../graph-fixture/inputs.json")),StandardCharsets.UTF_8));JSONObject small=JSON.parseObject(new String(Files.readAllBytes(h.resolve("../small-diagnostic/input.json")),StandardCharsets.UTF_8));
String q=new String(Files.readAllBytes(h.resolve("ic5.sql")),StandardCharsets.UTF_8);
try(Connection c=DriverManager.getConnection("jdbc:mysql://127.0.0.1:55337/jac_alignment_utf8?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false","root","")){
for(int i=0;i<2;i++){JSONObject x=i==0?small:inputs.getJSONObject(1);try(PreparedStatement s=c.prepareStatement("EXPLAIN FORMAT=JSON "+q)){s.setString(1,x.getString("person_jid"));s.setString(2,x.getString("person_jid"));s.setLong(3,x.getLongValue("min_date"));try(ResultSet r=s.executeQuery()){r.next();Files.write(h.resolve(i==0?"explain-small.json":"explain-original-idx1.json"),r.getString(1).getBytes(StandardCharsets.UTF_8));}}}}
}}
