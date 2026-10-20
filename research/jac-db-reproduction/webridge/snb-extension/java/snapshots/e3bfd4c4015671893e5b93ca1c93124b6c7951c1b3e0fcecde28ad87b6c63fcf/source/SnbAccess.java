import java.sql.*;
import java.nio.file.*;
import java.util.*;
import com.alibaba.fastjson2.*;

/** IC5 over original UUID anchors: request-local hydration, ordered graph hops and ACL. */
public class SnbAccess {
 static Path home=Paths.get(System.getProperty("alignment.dir","."));
 static String url="jdbc:mysql://127.0.0.1:55337/jac_alignment?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true";
 static String uuid(String s){if(s==null||s.length()!=32)return s;return s.substring(0,8)+"-"+s.substring(8,12)+"-"+s.substring(12,16)+"-"+s.substring(16,20)+"-"+s.substring(20);}
 static final boolean REMOVE_AUTH=Boolean.getBoolean("pruned.auth");
 static final boolean REMOVE_ACL=Boolean.getBoolean("pruned.acl");
 static final boolean REMOVE_SCHEMA=Boolean.getBoolean("pruned.schema");
 static final boolean REMOVE_HYDRATION=Boolean.getBoolean("pruned.hydration");
 static long calls; static Map<String,Long> kinds=new LinkedHashMap<>();
 static boolean schemaReady=false; static Set<String> knownTypes=new HashSet<>();
 static JSONObject context; static JSONObject input; static String activeQuery; static boolean guestResolved; static Set<String> requestTypes=new HashSet<>();
 static Map<String,String> clientRootContext=new HashMap<>();
 public interface RegionBoundary {void enter(Connection c)throws Exception;void leave(Connection c)throws Exception;}
 static RegionBoundary regionBoundary=new RegionBoundary(){public void enter(Connection c){}public void leave(Connection c){}};

 static class Anchor {String id,kind,type,root,src,dst; JSONObject props,arch,access;
  Anchor(String id,String type,JSONObject props){this.id=id;this.type=type;this.kind="NodeAnchor";this.props=props;this.arch=props==null?null:props.getJSONObject("archetype");}
  Anchor(ResultSet r)throws Exception{id=r.getString(1);kind=r.getString(2);type=r.getString(3);root=r.getString(6);src=r.getString(7);dst=r.getString(8);if(!REMOVE_SCHEMA&&!knownTypes.contains(type))throw new IllegalStateException("Unregistered anchor type:"+type);props=JSON.parseObject(r.getString(10));arch=props.getJSONObject("archetype");access=props.getJSONObject("access");}}
 static void count(String kind){calls++;kinds.put(kind,kinds.getOrDefault(kind,0L)+1);}
 static List<List<Object>> query(Connection c,String kind,String sql,Object...args)throws Exception{
  int n;if(kind.startsWith("hop:"))n=sql.startsWith("SELECT n.id,e.id,n.props,n.root_id")?4:sql.startsWith("SELECT n.id,e.id,JSON_EXTRACT(")?3:2;else if(kind.equals("root-acl"))n=3;else n=1;return rows(c,kind,n,sql,args);
 }
 static List<List<Object>> rows(Connection c,String kind,int n,String sql,Object...args)throws Exception{
  count(kind);try(PreparedStatement p=c.prepareStatement(sql)){for(int i=0;i<args.length;i++)p.setObject(i+1,args[i]);try(ResultSet r=p.executeQuery()){List<List<Object>> out=new ArrayList<>();while(r.next()){List<Object> row=new ArrayList<>();for(int i=1;i<=n;i++)row.add(r.getString(i));out.add(row);}return out;}}
 }
 static void command(Connection c,String kind,String sql)throws Exception{count(kind);try(Statement s=c.createStatement()){s.execute(sql);}}
 static void ensure(Connection c)throws Exception{
  if(REMOVE_SCHEMA||schemaReady)return;
  List<List<Object>> version=query(c,"server-version","SELECT VERSION()");if(!version.get(0).get(0).toString().startsWith("5.7."))throw new IllegalStateException("Wrong MySQL version");
  List<List<Object>> fingerprint=query(c,"schema-fingerprint","SELECT value FROM kv_state WHERE `key`=? AND (expires_at IS NULL OR expires_at>CURRENT_TIMESTAMP)","schema_fingerprint");if(fingerprint.isEmpty())throw new IllegalStateException("Missing original schema fingerprint");
  String expectedFingerprint=new String(Files.readAllBytes(home.resolve("graph-fixture/kv_state.tsv")),"UTF-8").split("\t")[1];if(!expectedFingerprint.equals(fingerprint.get(0).get(0).toString()))throw new IllegalStateException("Schema fingerprint differs from exported source");
  for(List<Object> r:query(c,"type-registry","SELECT DISTINCT type_name FROM graph_types"))knownTypes.add(r.get(0).toString());
  schemaReady=true;
 }
 static class Session {
  Connection c; Map<String,Anchor> mem=new HashMap<>();String root;
  Session(Connection c,String root){this.c=c;this.root=root;}
  List<Anchor> load(List<String> ids)throws Exception{
   List<String> missing=new ArrayList<>();for(String id:ids)if(!mem.containsKey(id))missing.add(id);
   if(!missing.isEmpty()){
    String marks=String.join(",",Collections.nCopies(missing.size(),"?"));count("anchor-load");
    try(PreparedStatement p=c.prepareStatement("SELECT a.id,a.kind,a.arch_type,a.arch_module,a.fingerprint,a.root_id,a.src,a.dst,a.undirected,a.props,a.row_version FROM anchors a WHERE a.id IN ("+marks+")")){
     for(int i=0;i<missing.size();i++)p.setString(i+1,missing.get(i));try(ResultSet r=p.executeQuery()){while(r.next()){Anchor a=new Anchor(r);mem.put(a.id,a);}}
    }
   }
   List<Anchor> out=new ArrayList<>();for(String id:ids){Anchor a=mem.get(id);if(a!=null)out.add(a);}return out;
  }
  Anchor get(String id)throws Exception{List<Anchor> a=load(Arrays.asList(id));return a.isEmpty()?null:a.get(0);}
  int all(Anchor a){if(a.access==null)return -1;Object v=a.access.get("all");return v instanceof Number?((Number)v).intValue():-1;}
  Integer grant(Anchor a){if(a.access==null)return null;JSONObject rs=a.access.getJSONObject("roots");if(rs==null)return null;JSONObject grants=rs.getJSONObject("anchors");if(grants==null)return null;Object x=grants.get(root);return x instanceof Number?((Number)x).intValue():null;}
  boolean readable(Anchor a)throws Exception{
   if(REMOVE_ACL)return true;
   if(root.equals(a.root)||root.equals(a.id))return true;
   int level=all(a);if(a.root!=null){Anchor owner=get(a.root);if(owner!=null){level=Math.max(level,all(owner));Integer x=grant(owner);if(x!=null)level=x;}}
   Integer x=grant(a);if(x!=null)level=x;return level>=0;
  }
  void guest()throws Exception{if(REMOVE_AUTH||guestResolved)return;query(c,"guest-identity","SELECT doc FROM identity_users WHERE user_id=?","__guest__");query(c,"guest-lookup","SELECT t.doc FROM identity_users t JOIN identity_lookups lk ON t.user_id=lk.user_id WHERE lk.value_normalized=? AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(t.doc,'$.status')),'active')<>'disabled'","__guest__");guestResolved=true;}
  Anchor fields(String id,String type)throws Exception{List<List<Object>> r=rows(c,"field-load",1,"SELECT JSON_EXTRACT(props,'$.archetype') FROM anchors WHERE id=?",id);if(r.isEmpty())return null;JSONObject p=new JSONObject();p.put("archetype",JSON.parseObject(r.get(0).get(0).toString()));Anchor a=new Anchor(id,type,p);mem.put(id,a);return a;}
  List<Anchor> projected(Collection<String> ids,String type)throws Exception{List<Anchor> out=new ArrayList<>();if(ids.isEmpty())return out;String sql="SELECT id,props,root_id FROM anchors WHERE id IN("+String.join(",",Collections.nCopies(ids.size(),"?"))+")";for(List<Object> r:rows(c,"projection:"+type,3,sql,ids.toArray())){Anchor a=new Anchor(r.get(0).toString(),type,JSON.parseObject(r.get(1).toString()));a.root=r.get(2)==null?null:r.get(2).toString();a.access=a.props.getJSONObject("access");mem.put(a.id,a);out.add(a);}if(!REMOVE_AUTH){guest();mem.remove(root);get(root);}return out;}
  LinkedHashMap<String,Integer> closure(Anchor start,Set<String> candidates,int maxDepth,int enough)throws Exception{LinkedHashMap<String,Integer> dist=new LinkedHashMap<>();Set<String> seen=new HashSet<>();seen.add(start.id);List<String> frontier=new ArrayList<>(Arrays.asList(start.id));for(int d=1;d<=maxDepth&&!frontier.isEmpty();d++){List<List<Object>> rs=rows(c,"adjacency.frontier",1,"SELECT DISTINCT nb.dst FROM adj_knows nb WHERE nb.src IN("+String.join(",",Collections.nCopies(frontier.size(),"?"))+")",frontier.toArray());List<String> next=new ArrayList<>();for(List<Object> r:rs){String id=r.get(0).toString();if(seen.add(id)){next.add(id);if(candidates.contains(id))dist.put(id,d);}}frontier=next;if(enough>0&&dist.size()>=enough)break;}return dist;}
  void rootAcl()throws Exception{query(c,"root-acl","SELECT a.id,CASE WHEN JSON_TYPE(JSON_EXTRACT(a.props,CONCAT('$.access.roots.anchors.\"',?,'\"'))) IN('INTEGER','DOUBLE') THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props,CONCAT('$.access.roots.anchors.\"',?,'\"'))) AS SIGNED) END,CASE WHEN JSON_TYPE(JSON_EXTRACT(a.props,'$.access.all')) IN('INTEGER','DOUBLE') THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(a.props,'$.access.all')) AS SIGNED) ELSE -1 END FROM anchors a WHERE a.kind='NodeAnchor' AND a.arch_type='Root' AND (JSON_EXTRACT(a.props,CONCAT('$.access.roots.anchors.\"',?,'\"')) IS NOT NULL OR JSON_TYPE(JSON_EXTRACT(a.props,'$.access.all')) IN('INTEGER','DOUBLE'))",root,root,root);}
  List<Anchor> hop(Anchor origin,String edge,String target,boolean incoming,Long minDate)throws Exception{
   // A single relational statement returns ordered node/edge pairs, matching Jac compile_query.
   // UNION branches implement the original directed-or-undirected predicate without an OR join scan.
   String primary=incoming?"dst":"src",reverse=incoming?"src":"dst";
   String endpoint=incoming?"src_type":"dst_type",other=incoming?"dst_type":"src_type";
   String filter="e.kind='EdgeAnchor' AND (e.arch_type=? OR e.arch_type IN(SELECT type_name FROM graph_types WHERE ancestor=?))";
   String branch1="SELECT e.* FROM anchors e WHERE e."+primary+"=? AND "+filter+" AND (e."+endpoint+" IS NULL OR e."+endpoint+"=? OR e."+endpoint+" IN(SELECT type_name FROM graph_types WHERE ancestor=?))";
   String branch2="SELECT e.* FROM anchors e WHERE e."+reverse+"=? AND e.undirected=1 AND e.src<>e.dst AND "+filter+" AND (e."+other+" IS NULL OR e."+other+"=? OR e."+other+" IN(SELECT type_name FROM graph_types WHERE ancestor=?))";
   boolean projected=REMOVE_HYDRATION||"is3".equals(activeQuery);
   if(("is3".equals(activeQuery)||"ic2".equals(activeQuery))&&!REMOVE_SCHEMA&&requestTypes.add(target))query(c,"type-descendant","SELECT type_name FROM graph_types WHERE ancestor=?",target);
   if("is3".equals(activeQuery)&&!REMOVE_ACL){rootAcl();guest();}
   String sql="SELECT n.id,e.id"+(projected?(REMOVE_HYDRATION?",JSON_EXTRACT(n.props,'$.archetype')":",n.props,n.root_id"):"")+" FROM ("+branch1+" UNION ALL "+branch2+") e JOIN anchors n ON n.id=CASE WHEN e.src=? THEN e.dst ELSE e.src END AND n.kind='NodeAnchor' AND (n.arch_type=? OR n.arch_type IN(SELECT type_name FROM graph_types WHERE ancestor=?))";
   List<Object> params=new ArrayList<>();for(int i=0;i<2;i++)Collections.addAll(params,origin.id,edge,edge,target,target);Collections.addAll(params,origin.id,target,target);
   if(minDate!=null){sql+=" WHERE CAST(JSON_UNQUOTE(JSON_EXTRACT(e.props,'$.archetype.joinDate')) AS SIGNED)>?";params.add(minDate);}
   sql+=" ORDER BY e.seq,e.id";
   List<List<Object>> rows=query(c,"hop:"+edge+":"+(incoming?"in":"out"),sql,params.toArray());
   LinkedHashSet<String> ids=new LinkedHashSet<>();for(List<Object> r:rows)if(r.get(0)!=null)ids.add(r.get(0).toString());
   List<Anchor> materialized;
   if("ic2".equals(activeQuery)&&edge.equals("Knows")){materialized=new ArrayList<>();for(String id:ids)materialized.add(new Anchor(id,target,null));return materialized;}
   if(projected){
    for(List<Object> row:rows){String id=row.get(0).toString();if(!mem.containsKey(id)){
     JSONObject props;if(REMOVE_HYDRATION){props=new JSONObject();props.put("archetype",JSON.parseObject(row.get(2).toString()));}else props=JSON.parseObject(row.get(2).toString());
     Anchor a=new Anchor(id,target,props);if(!REMOVE_HYDRATION){a.root=row.get(3)==null?null:row.get(3).toString();a.access=props.getJSONObject("access");}mem.put(id,a);
    }}
    materialized=new ArrayList<>();for(String id:ids)materialized.add(mem.get(id));
   }else materialized=load(new ArrayList<>(ids));LinkedHashSet<String> roots=new LinkedHashSet<>();for(Anchor a:materialized)if(a.root!=null&&!mem.containsKey(a.root))roots.add(a.root);if(!REMOVE_ACL&&!roots.isEmpty())load(new ArrayList<>(roots));
   List<Anchor> out=new ArrayList<>();for(Anchor a:materialized)if(readable(a))out.add(a);return out;
  }
 }
 public static JSONObject request(Connection c,JSONObject x)throws Exception{
  String uid=context.getString("user_id");String root=REMOVE_AUTH?uuid(context.getString("root_id")):clientRootContext.get(uid);
  if(root==null){List<List<Object>> identities=query(c,"identity","SELECT doc FROM identity_users WHERE user_id=?",uid);if(identities.size()!=1)throw new SecurityException("Unknown identity");JSONObject identity=JSON.parseObject(identities.get(0).get(0).toString());if("disabled".equals(identity.getString("status")))throw new SecurityException("Disabled identity");root=uuid(identity.getString("root_id"));clientRootContext.put(uid,root);}
  activeQuery=x.getString("query");guestResolved=false;requestTypes.clear();ensure(c);command(c,"begin","START TRANSACTION READ ONLY");command(c,"transaction-setting","SET SESSION innodb_lock_wait_timeout=10");
  try{regionBoundary.enter(c);Session s=new Session(c,root);if(!REMOVE_ACL&&s.get(root)==null)throw new SecurityException("Missing root");String pid=x.getString("person_jid");if(pid==null)pid=x.getString("person1_jid");Anchor p="is2".equals(activeQuery)&&!REMOVE_HYDRATION?s.projected(Arrays.asList(pid),"Person").get(0):REMOVE_HYDRATION?(("is1".equals(activeQuery)||"is2".equals(activeQuery))?s.fields(pid,"Person"):new Anchor(pid,"Person",null)):s.get(pid);if(p==null||!s.readable(p))throw new SecurityException("Unreadable person");
   JSONObject out=body(s,p,x);regionBoundary.leave(c);command(c,"commit","COMMIT");return out;
  }catch(Exception e){command(c,"rollback","ROLLBACK");throw e;}
 }
 static JSONObject object(Object... kv){JSONObject o=new JSONObject();for(int i=0;i<kv.length;i+=2)o.put(kv[i].toString(),kv[i+1]);return o;}
 static List<Anchor> friends(Session s,Anchor p)throws Exception{List<Anchor> f=new ArrayList<>(s.hop(p,"Knows","Person",false,null));f.addAll(s.hop(p,"Knows","Person",true,null));if("ic2".equals(activeQuery)&&!REMOVE_HYDRATION){List<String> ids=new ArrayList<>();for(Anchor a:f)ids.add(a.id);s.load(ids);}return f;}
 static JSONObject body(Session s,Anchor p,JSONObject x)throws Exception{
  String q=x.getString("query");
  if("is1".equals(q)){List<Anchor> cities=s.hop(p,"IsLocatedIn","Place",false,null);JSONObject a=p.arch;return object("firstName",a.getString("firstName"),"lastName",a.getString("lastName"),"birthday",a.getLong("birthday"),"locationIP",a.getString("locationIP"),"browserUsed",a.getString("browserUsed"),"cityId",cities.isEmpty()?-1L:cities.get(0).arch.getLong("place_id"),"gender",a.getString("gender"),"creationDate",a.getLong("creationDate"));}
  if("is3".equals(q)){List<JSONObject> out=new ArrayList<>();for(Anchor f:friends(s,p))out.add(object("personId",f.arch.getLong("person_id"),"firstName",f.arch.getString("firstName"),"lastName",f.arch.getString("lastName")));out.sort((a,b)->Long.compare(a.getLongValue("personId"),b.getLongValue("personId")));return object("friends",out,"count",out.size());}
  if("ic1".equals(q)){Set<String> candidates=new HashSet<>();for(List<Object> r:rows(s.c,"endpoint.predicate",1,"SELECT m.id FROM jac_snb_person_mirror m WHERE m.first_name=?",x.getString("first_name")))candidates.add(r.get(0).toString());LinkedHashMap<String,Integer> dist=s.closure(p,candidates,3,20);List<JSONObject> out=new ArrayList<>();for(Anchor a:s.projected(dist.keySet(),"Person"))out.add(object("personId",a.arch.getLong("person_id"),"lastName",a.arch.getString("lastName"),"distance",dist.get(a.id)));out.sort((a,b)->{int n=Integer.compare(a.getIntValue("distance"),b.getIntValue("distance"));if(n==0)n=a.getString("lastName").compareTo(b.getString("lastName"));if(n==0)n=Long.compare(a.getLongValue("personId"),b.getLongValue("personId"));return n;});return object("people",new ArrayList<>(out.subList(0,Math.min(20,out.size()))));}
  if("ic13".equals(q)){String target=x.getString("person2_jid");List<Anchor> targets=s.projected(Arrays.asList(target),"Person");if(targets.isEmpty())throw new IllegalArgumentException("Missing target");Anchor b=targets.get(0);if(p.id.equals(target))return object("length",0);Set<String> candidates=new HashSet<>();for(List<Object> r:rows(s.c,"endpoint.predicate",1,"SELECT m.id FROM jac_snb_person_mirror m WHERE m.person_id=?",b.arch.getLong("person_id")))candidates.add(r.get(0).toString());LinkedHashMap<String,Integer> dist=s.closure(p,candidates,6,1);if(!dist.isEmpty()&&!REMOVE_HYDRATION){s.mem.remove(target);s.get(target);}return object("length",dist.isEmpty()?-1:dist.values().iterator().next());}
  if("is2".equals(q)||"ic2".equals(q))return messages(s,p,x);
  throw new UnsupportedOperationException("Exact native SQL port pending census for "+q);
 }
 static List<Anchor> topk(Session s,List<Anchor> authors,long maxDate,int limit)throws Exception{
  List<Anchor> out=new ArrayList<>();if(authors.isEmpty())return out;List<String> arms=new ArrayList<>();List<Object> args=new ArrayList<>();
  for(Anchor author:authors)for(String type:Arrays.asList("Post","Comment")){arms.add("(SELECT m.id,m.creation_date AS ord,m.tie_id AS tie"+(REMOVE_HYDRATION?",m.arch_type,m.props":"")+" FROM jac_snb_message_mirror m WHERE m.creator_id=? AND m.arch_type=? AND m.creation_date<=? ORDER BY m.creation_date DESC,m.tie_id ASC LIMIT "+limit+")");Collections.addAll(args,author.id,type,Long.valueOf(maxDate));}
  String sql="SELECT id"+(REMOVE_HYDRATION?",arch_type,props":"")+" FROM ("+String.join(" UNION ALL ",arms)+") u ORDER BY ord DESC,tie ASC LIMIT "+limit;
  for(List<Object> r:rows(s.c,"topk.inbound",REMOVE_HYDRATION?3:1,sql,args.toArray())){String id=r.get(0).toString();Anchor a;if(REMOVE_HYDRATION){a=new Anchor(id,r.get(1).toString(),JSON.parseObject(r.get(2).toString()));s.mem.put(id,a);}else a=s.get(id);if(a!=null)out.add(a);}return out;
 }
 static Map<String,Anchor> authorEdges(Session s,Collection<Anchor> nodes)throws Exception{
  Map<String,Anchor> out=new LinkedHashMap<>();if(nodes.isEmpty())return out;List<String> ids=new ArrayList<>();for(Anchor a:nodes)ids.add(a.id);String marks=String.join(",",Collections.nCopies(ids.size(),"?"));
  String sql=REMOVE_HYDRATION?"SELECT e.src,n.props FROM anchors e JOIN anchors n ON n.id=e.dst AND n.kind='NodeAnchor' WHERE e.kind='EdgeAnchor' AND e.arch_type='HasCreator' AND e.src IN("+marks+") ORDER BY e.seq,e.id":"SELECT n.id,e.id FROM anchors e JOIN anchors n ON n.id=CASE WHEN e.src IN("+marks+") THEN e.dst ELSE e.src END AND n.kind='NodeAnchor' WHERE e.kind='EdgeAnchor' AND (e.arch_type='HasCreator' OR e.arch_type IN(SELECT type_name FROM graph_types WHERE ancestor='HasCreator')) AND (e.src IN("+marks+") OR(e.undirected=1 AND e.dst IN("+marks+"))) ORDER BY e.seq,e.id";
  List<Object> args=new ArrayList<>();args.addAll(ids);if(!REMOVE_HYDRATION){args.addAll(ids);args.addAll(ids);}List<List<Object>> rs=rows(s.c,"edge-pairs:HasCreator",2,sql,args.toArray());
  if(REMOVE_HYDRATION){for(List<Object> r:rs)out.put(r.get(0).toString(),new Anchor("projected-author","Person",JSON.parseObject(r.get(1).toString())));return out;}
  List<String> edges=new ArrayList<>(),targets=new ArrayList<>();for(List<Object> r:rs){targets.add(r.get(0).toString());edges.add(r.get(1).toString());}s.load(edges);for(String id:targets)s.mem.remove(id);s.load(targets);for(String edge:edges){Anchor e=s.mem.get(edge);if(e!=null){Anchor target=s.mem.get(e.dst);if(target!=null&&s.readable(target))out.put(e.src,target);}}return out;
 }
 static JSONObject messages(Session s,Anchor p,JSONObject x)throws Exception{
  boolean recent="is2".equals(activeQuery);List<Anchor> authors=recent?new ArrayList<>(Arrays.asList(p)):friends(s,p);List<Anchor> top=topk(s,authors,recent?Long.MAX_VALUE:x.getLongValue("max_date"),recent?10:20);
  top.sort((a,b)->{int n=Long.compare(b.arch.getLongValue("creationDate"),a.arch.getLongValue("creationDate"));long ai=a.arch.getLongValue(a.type.equals("Post")?"post_id":"comment_id"),bi=b.arch.getLongValue(b.type.equals("Post")?"post_id":"comment_id");return n!=0?n:recent?Long.compare(bi,ai):Long.compare(ai,bi);});
  Map<String,String> roots=new LinkedHashMap<>();Map<String,Anchor> rootPosts=new LinkedHashMap<>();Map<String,Anchor> authorOf;
  if(recent){List<String> comments=new ArrayList<>();for(Anchor a:top)if(a.type.equals("Comment"))comments.add(a.id);if(!comments.isEmpty()){String sql="SELECT m.id,m.root_of_replyof"+(REMOVE_HYDRATION?",p.props":"")+" FROM jac_snb_message_mirror m"+(REMOVE_HYDRATION?" JOIN anchors p ON p.id=m.root_of_replyof":"")+" WHERE m.id IN("+String.join(",",Collections.nCopies(comments.size(),"?"))+") AND m.root_of_replyof IS NOT NULL";for(List<Object> r:rows(s.c,"reply-root.promoted-column",REMOVE_HYDRATION?3:2,sql,comments.toArray())){String root=r.get(1).toString();roots.put(r.get(0).toString(),root);if(REMOVE_HYDRATION){Anchor a=new Anchor(root,"Post",JSON.parseObject(r.get(2).toString()));s.mem.put(root,a);}}}
   if(!REMOVE_HYDRATION)s.load(new ArrayList<>(new LinkedHashSet<>(roots.values())));for(String id:roots.values())if(!rootPosts.containsKey(id))rootPosts.put(id,s.get(id));authorOf=authorEdges(s,rootPosts.values());
  }else authorOf=authorEdges(s,top);
  List<JSONObject> out=new ArrayList<>();for(Anchor a:top){boolean post=a.type.equals("Post");long id=a.arch.getLongValue(post?"post_id":"comment_id");String content=a.arch.getString("content");if(post&&(content==null||content.isEmpty()))content=a.arch.getString("imageFile");JSONObject row=object("id",id,"creationDate",a.arch.getLong("creationDate"),"content",content);
   if(recent){row.put("kind",post?"post":"comment");if(post){row.put("origPostId",id);row.put("origAuthorId",p.arch.getLong("person_id"));}else{String root=roots.get(a.id);Anchor rp=rootPosts.get(root);if(rp!=null){row.put("origPostId",rp.arch.getLong("post_id"));Anchor author=authorOf.get(root);if(author!=null)row.put("origAuthorId",author.arch.getLong("person_id"));}}}
   else{Anchor author=authorOf.get(a.id);row.put("authorId",author==null?null:author.arch.getLong("person_id"));row.put("authorFirst",author==null?null:author.arch.getString("firstName"));row.put("authorLast",author==null?null:author.arch.getString("lastName"));}out.add(row);
  }return object("messages",out);
 }
 static String pyString(String v){StringBuilder b=new StringBuilder();b.append((char)34);for(int i=0;i<v.length();i++){char c=v.charAt(i);if(c==34||c==92)b.append((char)92).append(c);else if(c==8)b.append((char)92).append('b');else if(c==12)b.append((char)92).append('f');else if(c==10)b.append((char)92).append('n');else if(c==13)b.append((char)92).append('r');else if(c==9)b.append((char)92).append('t');else if(c<32||c>126)b.append((char)92).append('u').append(String.format("%04x",(int)c));else b.append(c);}return b.append((char)34).toString();}
 static String canonical(Object value){if(value==null)return "null";if(value instanceof String)return pyString((String)value);if(value instanceof Map){Map<String,Object> m=new TreeMap<>();for(Object key:((Map)value).keySet())m.put(key.toString(),((Map)value).get(key));List<String> pairs=new ArrayList<>();for(Map.Entry<String,Object> e:m.entrySet())pairs.add(pyString(e.getKey())+": "+canonical(e.getValue()));return "{"+String.join(", ",pairs)+"}";}if(value instanceof Iterable){List<String> out=new ArrayList<>();for(Object v:(Iterable)value)out.add(canonical(v));return "["+String.join(", ",out)+"]";}return value.toString();}
 static boolean parity(JSONObject result,JSONObject x)throws Exception{if(x.getJSONObject("expected")!=null)return canonical(result).equals(canonical(x.getJSONObject("expected")));String expected=x.getString("expected_canonical_sha256");if(expected==null)throw new IllegalStateException("Missing result oracle");byte[] hash=java.security.MessageDigest.getInstance("SHA-256").digest(canonical(result).getBytes("UTF-8"));StringBuilder h=new StringBuilder();for(byte b:hash)h.append(String.format("%02x",b&255));return expected.equals(h.toString());}
 static long questions(Connection c)throws Exception{try(Statement s=c.createStatement();ResultSet r=s.executeQuery("SHOW SESSION STATUS LIKE 'Questions'")){r.next();return r.getLong(2);}}
 public static void configure(Path directory)throws Exception{home=directory;context=JSON.parseObject(new String(Files.readAllBytes(home.resolve("graph-fixture/request-context.json")),"UTF-8"));}
 public static void main(String[]args)throws Exception{
  url=System.getProperty("experiment.mysql.url",url);configure(Paths.get(System.getProperty("alignment.dir")));JSONArray inputs=JSON.parseArray(new String(Files.readAllBytes(Paths.get(args[0])),"UTF-8"));
  try(Connection c=DriverManager.getConnection(url,"root","")){if(Boolean.getBoolean("snb.warmup"))request(c,inputs.getJSONObject(0));for(int round=0;round<Integer.parseInt(args[1]);round++)for(int idx=0;idx<inputs.size();idx++){JSONObject x=inputs.getJSONObject(idx);long before=questions(c);calls=0;kinds.clear();long start=System.nanoTime();JSONObject result=request(c,x);double ms=(System.nanoTime()-start)/1e6;long server=questions(c)-before-1;boolean ok=parity(result,x);JSONObject row=object("query",x.getString("query"),"idx",idx,"round",round,"client_ms",ms,"jdbc_calls",calls,"server_questions",server,"categories",new LinkedHashMap<>(kinds),"result",result,"parity",ok);System.out.println(row.toJSONString());if(!ok||server!=calls)throw new IllegalStateException("Result/count gate failed");}}
 }
}
