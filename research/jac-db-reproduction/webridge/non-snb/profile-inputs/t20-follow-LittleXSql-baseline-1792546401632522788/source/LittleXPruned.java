import java.sql.*;import java.util.*;import com.alibaba.fastjson2.*;
public class LittleXPruned {
 public static long commands;public static List<String>sqlLog=new ArrayList<>();public static LittleXSql.Boundary boundary;public static String region;
 public static JSONObject request(Connection c,JSONObject in)throws Exception{LittleXGraph.boundary=new LittleXSql.Boundary(){public void enter(Connection c)throws Exception{commands=LittleXGraph.commands;region=LittleXGraph.region;if(boundary!=null)boundary.enter(c);}public void leave(Connection c)throws Exception{commands=LittleXGraph.commands;region=LittleXGraph.region;if(boundary!=null)boundary.leave(c);}};try{return LittleXGraph.request(c,in,false);}finally{commands=LittleXGraph.commands;sqlLog=LittleXGraph.sqlLog;}}
}
