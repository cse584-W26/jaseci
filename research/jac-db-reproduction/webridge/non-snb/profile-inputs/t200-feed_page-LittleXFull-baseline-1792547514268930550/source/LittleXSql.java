import java.sql.*;import java.util.*;import com.alibaba.fastjson2.*;
/** Conventional relational implementation of the original littleX operations. */
public class LittleXSql {
 public static JSONObject obj(Object...args){JSONObject x=new JSONObject();for(int i=0;i<args.length;i+=2)x.put((String)args[i],args[i+1]);return x;}
 public interface Boundary{void enter(Connection c)throws Exception;void leave(Connection c)throws Exception;}public static Boundary boundary;public static long commands=0;public static List<String>sqlLog=new ArrayList<>();
 public static JSONObject configureConnection(Connection c)throws Exception{String original,global,effective,afterGlobal;try(Statement q=c.createStatement();ResultSet r=q.executeQuery("SELECT @@session.sql_mode,@@global.sql_mode")){r.next();original=r.getString(1);global=r.getString(2);}if(!Arrays.asList(original.split(",")).contains("NO_UNSIGNED_SUBTRACTION"))try(Statement q=c.createStatement()){q.execute("SET SESSION sql_mode=CONCAT(@@session.sql_mode,',NO_UNSIGNED_SUBTRACTION')");}try(Statement q=c.createStatement();ResultSet r=q.executeQuery("SELECT @@session.sql_mode,@@global.sql_mode")){r.next();effective=r.getString(1);afterGlobal=r.getString(2);}if(!effective.contains("NO_UNSIGNED_SUBTRACTION"))throw new IllegalStateException("Signed subtraction mode missing");return obj("original_session",original,"effective_session",effective,"global_mode_before",global,"global_mode_after",afterGlobal,"global_unchanged",global.equals(afterGlobal),"scope","per JDBC connection before API/timer; all original strict flags retained","transaction_dialect","SET TRANSACTION characteristics, JDBC setAutoCommit(false/true)");}
 static void bind(PreparedStatement p,Object...args)throws Exception{for(int i=0;i<args.length;i++)p.setString(i+1,(String)args[i]);}
 static List<String[]> select(Connection c,String sql,int width,Object...args)throws Exception{commands++;sqlLog.add(sql);List<String[]>out=new ArrayList<>();try(PreparedStatement p=c.prepareStatement(sql)){bind(p,args);try(ResultSet r=p.executeQuery()){while(r.next()){String[]row=new String[width];for(int i=0;i<width;i++)row[i]=r.getString(i+1);out.add(row);}}}return out;}
 static int update(Connection c,String sql,Object...args)throws Exception{commands++;sqlLog.add(sql);try(PreparedStatement p=c.prepareStatement(sql)){bind(p,args);return p.executeUpdate();}}
 static void command(Connection c,String sql)throws Exception{commands++;sqlLog.add(sql);try(Statement s=c.createStatement()){s.execute(sql);}}
 static JSONObject tweet(String[]r){JSONObject t=new JSONObject();t.put("seed_id",r[0]);t.put("content",r[1]);t.put("author_username",r[2]);t.put("created_at",r[3]);t.put("likes",JSON.parseArray(r[4]));t.put("comments",JSON.parseArray(r[5]));return t;}
 static final String PROJECT="SELECT t.seed_id,t.content,p.username,t.created_at,t.likes,t.comments FROM lx_tweets t JOIN lx_profiles p ON p.id=t.author_id ";
 static void autoCommit(Connection c,boolean enabled)throws Exception{commands++;sqlLog.add("set autocommit="+(enabled?"1":"0"));c.setAutoCommit(enabled);}
 public static JSONObject request(Connection c,JSONObject in)throws Exception{commands=0;sqlLog.clear();boolean read=in.getString("op").startsWith("feed");command(c,"SET SESSION innodb_lock_wait_timeout=10");command(c,read?"SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY":"SET TRANSACTION ISOLATION LEVEL SERIALIZABLE, READ WRITE");try{if(boundary!=null)boundary.enter(c);autoCommit(c,false);JSONObject out=body(c,in);autoCommit(c,true);if(boundary!=null)boundary.leave(c);return out;}catch(Exception e){c.rollback();c.setAutoCommit(true);throw e;}}
 public static JSONObject body(Connection c,JSONObject in)throws Exception{
 String op=in.getString("op"),actor=in.getString("actor_id");JSONObject out=new JSONObject();
 if(op.equals("feed")||op.equals("feed_page")){
  String sql=PROJECT+"WHERE t.author_id=? OR t.author_id IN(SELECT followee_id FROM lx_follows WHERE follower_id=?) ORDER BY t.created_at DESC"+(op.equals("feed_page")?" LIMIT 20":"");List<JSONObject>feed=new ArrayList<>();for(String[]r:select(c,sql,6,actor,actor))feed.add(tweet(r));out.put("feed",feed);return out;
 }
 if(op.equals("follow")){update(c,"INSERT IGNORE INTO lx_follows(follower_id,followee_id) SELECT p.id,t.id FROM lx_profiles p JOIN lx_profiles t ON t.id=? WHERE p.id=?",in.getString("target_id"),actor);out.put("success",true);return out;}
 if(op.equals("create_tweet")){
  update(c,"INSERT INTO lx_tweets(id,seed_id,author_id,content,created_at,likes,comments) SELECT ?,?,p.id,?,?, '[]','[]' FROM lx_profiles p WHERE p.id=?",in.getString("new_id"),in.getString("seed_id"),in.getString("content"),in.getString("created_at"),actor);
  List<String[]>rs=select(c,PROJECT+"WHERE t.id=?",6,in.getString("new_id"));if(rs.isEmpty())throw new IllegalStateException("profile not found");out.put("tweet",tweet(rs.get(0)));return out;
 }
 if(op.equals("like")){
  update(c,"UPDATE lx_tweets t JOIN lx_profiles p ON p.id=? SET t.likes=JSON_ARRAY_APPEND(t.likes,'$',p.username) WHERE t.id=? AND NOT JSON_CONTAINS(t.likes,JSON_QUOTE(p.username))",actor,in.getString("tweet_id"));List<String[]>rs=select(c,"SELECT JSON_LENGTH(likes) AS likes_count FROM lx_tweets WHERE id=?",1,in.getString("tweet_id"));if(rs.isEmpty())throw new IllegalStateException("tweet not found");out.put("success",true);out.put("likes_count",Integer.valueOf(rs.get(0)[0]));return out;
 }
 throw new IllegalArgumentException("Unknown operation "+op);
 }
}
