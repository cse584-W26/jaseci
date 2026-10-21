import java.sql.*;import java.util.*;import java.nio.file.*;import java.util.regex.*;import com.alibaba.fastjson2.*;
/** Access-level Java port of the measured ad469 littleX graph request. */
public class LittleXGraph {
 static final String ROOT="00000000-0000-0000-0000-000000000000";
 static final JSONObject T=loadTemplates();
 static JSONObject loadTemplates(){try{return JSON.parseObject(new String(Files.readAllBytes(Paths.get(System.getProperty("littlex.templates","reproduction/webridge/non-snb/littlex/native-templates.json"))),"UTF-8")).getJSONObject("operations");}catch(Exception e){throw new ExceptionInInitializerError(e);}}
 static String template(String op,int n){return T.getJSONArray(op).getJSONObject(n).getString("sql");}
 static boolean currentFull;static String nodeSeq,edgeSeq;static long commands;static List<String>sqlLog=new ArrayList<>();static LittleXSql.Boundary boundary;static String region;
 static void command(Connection c,String s)throws Exception{commands++;sqlLog.add(s);try(Statement q=c.createStatement()){q.execute(s);}}
 static List<String[]> select(Connection c,String s,int width,List<Object>args)throws Exception{commands++;sqlLog.add(s);List<String[]>a=new ArrayList<>();try(PreparedStatement p=c.prepareStatement(s)){for(int i=0;i<args.size();i++){Object v=args.get(i);if(v instanceof Integer)p.setInt(i+1,(Integer)v);else p.setString(i+1,(String)v);}try(ResultSet r=p.executeQuery()){while(r.next()){String[]z=new String[width];for(int i=0;i<width;i++)z[i]=r.getString(i+1);a.add(z);}}}return a;}
 static List<String[]> sql(Connection c,String s,int width,Object...args)throws Exception{return select(c,s,width,new ArrayList<Object>(Arrays.asList(args)));}
 static List<String[]> nativeSelect(Connection c,String s,int width,Object...params)throws Exception{
  if(!currentFull)s=s.replaceAll(" AND CASE WHEN n[0-9]+\\.root_id = .*? END", "");
  // Each recorded frontier is singleton; ordinality remains explicit. Empty cached ACL arrays expand to NULL.
  s=s.replaceAll("unnest\\(CAST\\(\\$(\\d+) AS uuid\\[\\]\\)\\) WITH ORDINALITY AS f0\\(id, ord\\)","(SELECT \\$$1 AS id, 1 AS ord) AS f0");
  s=s.replaceAll("= ANY\\(CAST\\(\\$(\\d+) AS uuid\\[\\]\\)\\)","IN (\\$$1)");
  s=s.replaceAll("CAST\\(\\$(\\d+) AS (uuid|text)\\)","\\$$1");
  s=s.replace("::text","");
  s=s.replace("= ANY(ARRAY(","IN (");
  // PostgreSQL ANY(ARRAY(SELECT ...)) contributes one extra closing parenthesis.
  if(s.contains("n2.src_endpoint IN ("))s=s.replace("$5)))) AND CASE","$5))) AND CASE");
  List<Object>bind=new ArrayList<>();Matcher m=Pattern.compile("\\$(\\d+)").matcher(s);StringBuffer b=new StringBuffer();while(m.find()){Object v=params[Integer.parseInt(m.group(1))-1];if(v instanceof String&&((String)v).equals("{}")){m.appendReplacement(b,"NULL");}else{bind.add(v);m.appendReplacement(b,"?");}}m.appendTail(b);
  return select(c,b.toString(),width,bind);
 }
 static JSONObject hydrate(Connection c,String id)throws Exception{List<String[]>r=sql(c,"SELECT a.id,a.kind,a.arch_type,a.arch_module,a.fingerprint,a.root_id,a.src,a.dst,a.undirected,a.props,'0' AS row_version FROM anchors a WHERE a.id IN (?)",11,id);if(r.isEmpty())throw new IllegalStateException("Missing graph anchor "+id);JSONObject a=JSON.parseObject(r.get(0)[9]);a.put("_arch_type",r.get(0)[2]);a.put("_fingerprint",r.get(0)[4]);return a;}
 static void types(Connection c,String t)throws Exception{sql(c,"SELECT type_name FROM graph_types WHERE ancestor=?",1,t);}
 static String ROOTACL="SELECT a.id,CASE WHEN JSON_TYPE(JSON_EXTRACT(a.props,CONCAT('$.access.roots.anchors.\"',?,'\"')))='INTEGER' THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props,CONCAT('$.access.roots.anchors.\"',?,'\"'))) AS SIGNED) ELSE NULL END AS root_grant,CASE WHEN JSON_TYPE(JSON_EXTRACT(a.props,'$.access.all'))='INTEGER' THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props,'$.access.all')) AS SIGNED) ELSE -1 END AS all_grant FROM anchors a WHERE a.kind='NodeAnchor' AND a.arch_type='Root' AND (JSON_EXTRACT(a.props,CONCAT('$.access.roots.anchors.\"',?,'\"')) IS NOT NULL OR JSON_TYPE(JSON_EXTRACT(a.props,'$.access.all'))='INTEGER')";
 static void acl(Connection c,String root)throws Exception{sql(c,ROOTACL,3,root,root,root);}
 static void enter(Connection c,String r)throws Exception{region=r;if(boundary!=null)boundary.enter(c);}static void leave(Connection c)throws Exception{if(boundary!=null)boundary.leave(c);}
 static List<JSONObject>fragments(List<String[]>rows){List<JSONObject>r=new ArrayList<>();for(String[]s:rows){JSONObject a=JSON.parseObject(s[4]);a.remove("_jac_id");a.remove("_jac_type");a.remove("_jac_archetype");r.add(a);}return r;}
 static JSONObject read(Connection c,JSONObject in,boolean full)throws Exception{
  String op=in.getString("op"),root=in.getString("actor_root_id"),actor=in.getString("actor_id"),guest=in.getString("guest_root_id");if(guest==null)throw new IllegalArgumentException("guest_root_id required from cached identity metadata");boolean page=op.equals("feed_page");
  if(full){command(c,"START TRANSACTION");command(c,"SET SESSION innodb_lock_wait_timeout=10");enter(c,op+"/dispatch");hydrate(c,ROOT);hydrate(c,root);types(c,"Profile");leave(c);command(c,"COMMIT");}
  command(c,"START TRANSACTION READ ONLY");command(c,"SET SESSION innodb_lock_wait_timeout=10");enter(c,op+"/business");
  if(full)acl(c,root);
  List<String[]>p=nativeSelect(c,template(op,9),6,root,"Profile","Profile",root,guest,"{}","{}",28);if(p.size()!=1||!p.get(0)[0].equals(actor))throw new IllegalStateException("Actor graph projection mismatch");
  if(full){types(c,"Tweet");acl(c,root);}
  List<String[]>own=nativeSelect(c,template(op,12),6,actor,"Tweet","Tweet",root,guest,"{}","{}",28);
  if(full)acl(c,root);
  List<String[]>other=nativeSelect(c,template(op,14),6,actor,"Profile","Profile","Follow","Profile","Tweet","Tweet",root,guest,"{}","{}",28);
  List<JSONObject>feed=fragments(own);feed.addAll(fragments(other));Collections.sort(feed,new Comparator<JSONObject>(){public int compare(JSONObject a,JSONObject b){return b.getString("created_at").compareTo(a.getString("created_at"));}});if(page&&feed.size()>20)feed=new ArrayList<JSONObject>(feed.subList(0,20));leave(c);command(c,"COMMIT");JSONObject out=new JSONObject();out.put("feed",feed);return out;
 }

 static JSONObject nodeProps(String id,String root,JSONObject archetype){return LittleXSql.obj("id",id,"root",root,"access",LittleXSql.obj("all",2,"roots",LittleXSql.obj("anchors",new JSONObject())),"version",0,"__type__","NodeAnchor","archetype",archetype,"__module__","jaclang.jac0core.archetype","persistent",true);}
 static JSONObject edgeProps(String id,String root,String src,String dst,String type){return LittleXSql.obj("id",id,"root",root,"access",LittleXSql.obj("all",-1,"roots",LittleXSql.obj("anchors",new JSONObject())),"source",src,"target",dst,"__type__","EdgeAnchor","archetype",LittleXSql.obj("__type__",type,"__module__","app"),"__module__","jaclang.jac0core.archetype","persistent",true,"is_undirected",false);}
 static int update(Connection c,String s,Object...args)throws Exception{commands++;sqlLog.add(s);try(PreparedStatement p=c.prepareStatement(s)){for(int i=0;i<args.length;i++)p.setString(i+1,(String)args[i]);return p.executeUpdate();}}
 static Object[] anchor(String id,String kind,String type,String fp,String root,String src,String dst,JSONObject props,String st,String dt){return new Object[]{id,kind,type,"app",fp,root,src,dst,"0",props.toJSONString(),st,dt,kind.equals("EdgeAnchor")?edgeSeq:nodeSeq};}
 static void upsert(Connection c,Object[]...rows)throws Exception{
  StringBuilder s=new StringBuilder("INSERT INTO anchors(id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,undirected,props,src_type,dst_type,seq) VALUES ");List<Object>a=new ArrayList<>();for(int i=0;i<rows.length;i++){if(i>0)s.append(',');s.append("(?,?,?,?,?,?,?,?,?,?,?,?,?)");a.addAll(Arrays.asList(rows[i]));}s.append(" ON DUPLICATE KEY UPDATE kind=VALUES(kind),arch_type=VALUES(arch_type),arch_module=VALUES(arch_module),fingerprint=VALUES(fingerprint),root_id=VALUES(root_id),src=VALUES(src),dst=VALUES(dst),undirected=VALUES(undirected),props=VALUES(props),src_type=COALESCE(VALUES(src_type),src_type),dst_type=COALESCE(VALUES(dst_type),dst_type)");update(c,s.toString(),a.toArray());
 }
 static void register(Connection c,String...types)throws Exception{StringBuilder s=new StringBuilder("INSERT IGNORE INTO graph_types(type_name,ancestor) VALUES ");List<Object>a=new ArrayList<>();for(int i=0;i<types.length;i++){if(i>0)s.append(',');s.append("(?,?)");a.add(types[i]);a.add(types[i]);}update(c,s.toString(),a.toArray());}
 static JSONObject write(Connection c,JSONObject in,boolean full)throws Exception{
  String op=in.getString("op"),root=in.getString("actor_root_id"),actor=in.getString("actor_id");nodeSeq=in.getString("new_seq");edgeSeq=in.getString("new_edge_seq");if(nodeSeq==null||edgeSeq==null)throw new IllegalArgumentException("Deterministic new sequence inputs required");command(c,"START TRANSACTION");command(c,"SET SESSION innodb_lock_wait_timeout=10");enter(c,op);
  if(full){hydrate(c,ROOT);hydrate(c,root);}
  List<String[]> own=nativeSelect(c,full?template(op,4):template(op,4).replace("SELECT n1.id, e1.id FROM","SELECT n1.id, e1.id, n1.props FROM"),full?2:3,root,"Profile","Profile","Profile");if(own.size()!=1||!own.get(0)[0].equals(actor))throw new IllegalStateException("Actor navigation mismatch");JSONObject profile=full?hydrate(c,actor):JSON.parseObject(own.get(0)[2]);JSONObject out=new JSONObject();
  if(op.equals("like")){
   JSONObject t=hydrate(c,in.getString("tweet_id"));if(full)hydrate(c,t.getString("root"));JSONObject arch=t.getJSONObject("archetype");JSONArray likes=arch.getJSONArray("likes");String name=profile.getJSONObject("archetype").getString("username");if(!likes.contains(name)){likes.add(name);upsert(c,anchor(t.getString("id"),"NodeAnchor","Tweet",t.getString("_fingerprint"),t.getString("root"),null,null,clean(t),null,null));if(full)register(c,"Tweet");}out.put("success",true);out.put("likes_count",likes.size());
  }else if(op.equals("follow")){
   String target=in.getString("target_id");JSONObject t=hydrate(c,target);if(full)hydrate(c,t.getString("root"));List<String[]>existing=nativeSelect(c,template(op,8),2,actor,"Profile","Profile","Follow","Profile",target);if(existing.isEmpty()){String id=in.getString("new_edge_id");upsert(c,anchor(id,"EdgeAnchor","Follow","48457a3fa45ae05d",root,actor,target,edgeProps(id,root,actor,target,"Follow"),"Profile","Profile"));if(full)register(c,"Follow");}out.put("success",true);
  }else if(op.equals("create_tweet")){
   String id=in.getString("new_id"),eid=in.getString("new_edge_id");JSONObject arch=LittleXSql.obj("likes",new JSONArray(),"content",in.getString("content"),"seed_id",in.getString("seed_id"),"__type__","Tweet","comments",new JSONArray(),"__module__","app","created_at",in.getString("created_at"),"author_username",profile.getJSONObject("archetype").getString("username"));upsert(c,anchor(eid,"EdgeAnchor","Post","0257ab8108739b8f",root,actor,id,edgeProps(eid,root,actor,id,"Post"),"Profile","Tweet"),anchor(id,"NodeAnchor","Tweet","552e15e3e79578ff",root,null,null,nodeProps(id,root,arch),null,null));if(full)register(c,"Post","Tweet");JSONObject result=(JSONObject)arch.clone();result.remove("__type__");result.remove("__module__");out.put("tweet",result);
  }else throw new IllegalArgumentException(op);
  leave(c);command(c,"COMMIT");return out;
 }
 static JSONObject clean(JSONObject x){JSONObject r=(JSONObject)x.clone();r.remove("_arch_type");r.remove("_fingerprint");return r;}
 static JSONObject request(Connection c,JSONObject in,boolean full)throws Exception{commands=0;sqlLog.clear();currentFull=full;try{return in.getString("op").startsWith("feed")?read(c,in,full):write(c,in,full);}catch(Exception e){command(c,"ROLLBACK");throw e;}}
}
