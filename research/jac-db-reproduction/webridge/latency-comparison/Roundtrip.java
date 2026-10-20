import java.sql.*;import java.util.*;import java.nio.file.*;
public class Roundtrip {
 public static void main(String[] args)throws Exception{
 Class.forName("com.mysql.jdbc.Driver");String url="jdbc:mysql://127.0.0.1:"+args[0]+"/jac_alignment_utf8?useSSL=false&useLocalSessionState=true";List<Double>ms=new ArrayList<>();try(Connection c=DriverManager.getConnection(url,"root","");Statement s=c.createStatement()){
 for(int i=0;i<40;i++){long t=System.nanoTime();try(ResultSet r=s.executeQuery("SELECT 1")){r.next();if(r.getInt(1)!=1)throw new Exception("bad result");}if(i>=10)ms.add((System.nanoTime()-t)/1e6);}}
 Files.write(Paths.get(args[1]),ms.toString().getBytes("UTF-8"));
 }
}
