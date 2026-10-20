import java.util.*;import java.nio.file.*;import java.sql.*;import org.apache.commons.lang3.SerializationUtils;import org.apache.commons.lang3.tuple.Pair;import webridge.wbridge.sql.result.MultipleRowResultSetImpl;
public class RecordedTest {
 public static void main(String[] args)throws Exception{
 List<Pair<String,Object>> data=SerializationUtils.deserialize(Files.readAllBytes(Paths.get(args[0])));long cells=0,rows=0;Map<String,Long> types=new TreeMap<>();int forum=0;
 for(Pair<String,Object> p:data){Object v=p.getRight();if(!(v instanceof MultipleRowResultSetImpl))continue;MultipleRowResultSetImpl rs=(MultipleRowResultSetImpl)v;int n=rs.getColumnNameList().size();while(rs.next()){List<Object> raw=rs.getColumnValueList().get((int)rowsFor(rs)); for(int i=1;i<=n;i++){Object x=raw.get(i-1);String k=i+":"+(x==null?"null":x.getClass().getName());types.put(k,types.getOrDefault(k,0L)+1);if(n==4&&i==3){long z=rs.getLong(i);if(x!=null&&z!=((Number)x).longValue())throw new AssertionError();}else{String y=rs.getString(i);String expected=x instanceof byte[]?new String((byte[])x,"UTF-8"):x==null?null:x.toString();if(!Objects.equals(y,expected))throw new AssertionError();}if(rs.wasNull()!=(x==null))throw new AssertionError();cells++;}rows++;if(n==4)forum++;}}
 MultipleRowResultSetImpl nullable=new MultipleRowResultSetImpl(Arrays.asList("a","b","c"),Arrays.asList("","",""),Arrays.asList(Arrays.asList(null,123L,"é".getBytes("UTF-8"))));nullable.next();if(nullable.getString(1)!=null||!nullable.wasNull()||!nullable.getString(2).equals("123")||!nullable.getString(3).equals("é"))throw new AssertionError();
 System.out.println("PASS rows="+rows+" cells="+cells+" forumRows="+forum+" types="+types);
 }
 static long rowsFor(MultipleRowResultSetImpl r)throws Exception{java.lang.reflect.Field f=r.getClass().getDeclaredField("curIndex");f.setAccessible(true);return f.getInt(r);}
}
