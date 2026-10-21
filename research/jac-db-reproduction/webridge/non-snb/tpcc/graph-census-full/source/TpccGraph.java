import java.sql.*;
import java.nio.file.*;
import java.util.*;
import com.alibaba.fastjson2.*;

/** Source-level Jac graph transaction port: dynamic hydration, mutations and eager flushes. */
public class TpccGraph {
 static final boolean PRUNED=Boolean.getBoolean("experiment.pruned");
 static JSONObject context;static long sequence;static boolean ready=false;static JSONArray ids,freshSequences;static int nextId,nextSequence;
 static void prepareIds(JSONObject x){ids=new JSONArray();int size=x.getString("kind").equals("new_order")?2*(x.getJSONArray("lines").size()+1):2;for(int i=0;i<size;i++)ids.add(UUID.randomUUID().toString());x.put("fresh_ids",ids);nextId=0;freshSequences=new JSONArray();int rows=x.getString("kind").equals("new_order")?3+3*x.getJSONArray("lines").size():5;for(int i=0;i<rows;i++)freshSequences.add(Long.valueOf(++sequence));x.put("fresh_sequences",freshSequences);nextSequence=0;}
 static String uuid(String s){return s.length()==32?s.substring(0,8)+"-"+s.substring(8,12)+"-"+s.substring(12,16)+"-"+s.substring(16,20)+"-"+s.substring(20):s;}
 static String mapped(String table,String key){String value=context.getJSONObject("maps").getJSONObject(table).getString(key);return value==null?"00000000-0000-0000-0000-000000000000":uuid(value);}
 static void configure()throws Exception{if(context==null){context=JSON.parseObject(new String(Files.readAllBytes(Paths.get(System.getProperty("experiment.graph.context"))),"UTF-8"));sequence=context.getLongValue("initial_max_seq");}}
 static void bootstrap(Connection c)throws Exception{
  configure();if(ready)return;TpccSql.command(c,"transaction.isolation.setup","SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE");if(PRUNED){ready=true;return;}
  List<String> identity=TpccSql.one(c,"identity.lookup",1,"SELECT doc FROM identity_users WHERE user_id=?",context.getString("user_id"));if(identity==null)throw new SecurityException("Unknown service identity");JSONObject doc=JSON.parseObject(identity.get(0));if(!uuid(doc.getString("root_id")).equals(context.getString("root_id")))throw new SecurityException("Service root mismatch");
  TpccSql.rows(c,"schema.version",1,"SELECT VERSION()");TpccSql.rows(c,"schema.guard",1,"SELECT value FROM kv_state WHERE `key`=? AND(expires_at IS NULL OR expires_at>CURRENT_TIMESTAMP)","schema_fingerprint");TpccSql.rows(c,"schema.registry",1,"SELECT DISTINCT type_name FROM graph_types");ready=true;
 }
 static class Node {
  String id,kind,type,module,fingerprint,root,src,dst,srcType,dstType;boolean undirected;JSONObject props,arch;
  Node(String id,String type,JSONObject props){this.id=id;this.type=type;this.props=props;this.arch=props.getJSONObject("archetype");this.root=props.getString("root");JSONObject t=context.getJSONObject("templates").getJSONObject(type);kind=t.getString("kind");module=t.getString("arch_module");fingerprint=t.getString("fingerprint");src=props.getString("source");dst=props.getString("target");undirected=props.getBooleanValue("is_undirected");}
 }
 static class Session {
  Connection c;String root=context.getString("root_id");LinkedHashMap<String,Node> mem=new LinkedHashMap<>(),dirty=new LinkedHashMap<>();Set<String> registered=new HashSet<>();
  Session(Connection c){this.c=c;}
  List<Node> load(Collection<String> ids)throws Exception{
   List<String> missing=new ArrayList<>();for(String id:ids)if(!mem.containsKey(id))missing.add(id);
   if(!missing.isEmpty()){
    String sql=PRUNED?"SELECT id,arch_type,props FROM anchors WHERE id IN(":"SELECT id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,undirected,props,row_version FROM anchors WHERE id IN(";sql+=String.join(",",Collections.nCopies(missing.size(),"?"))+")";
    for(List<String> r:TpccSql.rows(c,"hydrate.generic_anchor",PRUNED?3:11,sql,missing.toArray())){Node n=new Node(r.get(0),r.get(PRUNED?1:2),JSON.parseObject(r.get(PRUNED?2:9)));mem.put(n.id,n);}
   }
   List<Node> out=new ArrayList<>();for(String id:ids)if(mem.containsKey(id))out.add(mem.get(id));return out;
  }
  Node get(String id)throws Exception{List<Node> r=load(Arrays.asList(id));return r.isEmpty()?null:r.get(0);}
  List<Node> hop(String source,String target,String last)throws Exception{
   String sql="SELECT n.id,e.id"+(PRUNED?",n.props":"")+" FROM anchors e JOIN anchors n ON n.id=CASE WHEN e.src=? THEN e.dst ELSE e.src END AND n.kind='NodeAnchor' AND(n.arch_type=? OR n.arch_type IN(SELECT type_name FROM graph_types WHERE ancestor=?)) WHERE e.kind='EdgeAnchor' AND((e.src=? AND(e.dst_type IS NULL OR e.dst_type=? OR e.dst_type IN(SELECT type_name FROM graph_types WHERE ancestor=?)))OR(e.undirected=1 AND e.dst=? AND(e.src_type IS NULL OR e.src_type=? OR e.src_type IN(SELECT type_name FROM graph_types WHERE ancestor=?))))";
   List<Object> args=new ArrayList<>(Arrays.asList(source,target,target,source,target,target,source,target,target));if(last!=null){sql+=" AND n.arch_type=? AND n.c_last=?";args.add(target);args.add(last);}sql+=" ORDER BY e.seq,e.id";
   List<String> ids=new ArrayList<>();for(List<String> r:TpccSql.rows(c,last==null?"graph.Warehouse.hop":"graph.Customer.by_lastname_promoted",PRUNED?3:2,sql,args.toArray())){ids.add(r.get(0));if(PRUNED)mem.put(r.get(0),new Node(r.get(0),target,JSON.parseObject(r.get(2))));}
   return load(ids);
  }
  void readable(Node n)throws Exception{
   if(PRUNED||root.equals(n.root)||root.equals(n.id))return;int level=-1;JSONObject access=n.props.getJSONObject("access");if(access!=null)level=access.getIntValue("all");
   if(n.root!=null){Node owner=get(n.root);if(owner!=null){JSONObject oa=owner.props.getJSONObject("access");if(oa!=null){level=Math.max(level,oa.getIntValue("all"));JSONObject grants=oa.getJSONObject("roots").getJSONObject("anchors");if(grants.containsKey(root))level=grants.getIntValue(root);}}}
   if(access!=null){JSONObject grants=access.getJSONObject("roots").getJSONObject("anchors");if(grants.containsKey(root))level=grants.getIntValue(root);}if(level<0)throw new SecurityException("Unreadable cross-root anchor");
  }
  void mark(Node n){if(!PRUNED&&!root.equals(n.root))throw new SecurityException("Foreign write denied");dirty.put(n.id,n);}
  Node create(String type,JSONObject attrs){
   String id=ids.getString(nextId++);JSONObject template=context.getJSONObject("templates").getJSONObject(type);JSONObject props=JSON.parseObject(template.getJSONObject("props").toJSONString());props.put("id",id);props.put("root",root);props.put("persistent",true);props.put("access",TpccSql.obj("all",-1,"roots",TpccSql.obj("anchors",new JSONObject())));JSONObject arch=TpccSql.obj("__type__",type,"__module__",template.getString("arch_module"));arch.putAll(attrs);props.put("archetype",arch);return new Node(id,type,props);
  }
  Node child(Node parent,String edgeType,String nodeType,JSONObject attrs){
   Node node=create(nodeType,attrs);Node edge=create(edgeType,new JSONObject());edge.src=parent.id;edge.dst=node.id;edge.srcType=parent.type;edge.dstType=nodeType;edge.props.put("source",parent.id);edge.props.put("target",node.id);edge.props.put("is_undirected",false);mem.put(edge.id,edge);mark(edge);mem.put(node.id,node);mark(node);return node;
  }
  void flush()throws Exception{
   if(dirty.isEmpty())return;List<Node> nodes=new ArrayList<>();for(Node n:mem.values())if(dirty.containsKey(n.id))nodes.add(n);List<Object> args=new ArrayList<>();List<String> values=new ArrayList<>();LinkedHashSet<String> types=new LinkedHashSet<>();
   for(Node n:nodes){values.add("(?,?,?,?,?,?,?,?,?,?,?,?,?,?)");Collections.addAll(args,n.id,n.kind,n.type,n.module,n.fingerprint,n.root,n.src,n.dst,n.undirected,n.props.toJSONString(),"java-dirty",freshSequences.get(nextSequence++),n.srcType,n.dstType);if(!registered.contains(n.type))types.add(n.type);}
   String sql="INSERT INTO anchors(id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,undirected,props,row_version,seq,src_type,dst_type)VALUES"+String.join(",",values)+" ON DUPLICATE KEY UPDATE kind=VALUES(kind),arch_type=VALUES(arch_type),arch_module=VALUES(arch_module),fingerprint=VALUES(fingerprint),root_id=VALUES(root_id),src=VALUES(src),dst=VALUES(dst),undirected=VALUES(undirected),props=VALUES(props),row_version=VALUES(row_version),src_type=COALESCE(VALUES(src_type),src_type),dst_type=COALESCE(VALUES(dst_type),dst_type)";TpccSql.update(c,"write.anchor_batch_upsert",sql,args.toArray());
   if(!PRUNED&&!types.isEmpty()){List<Object> registry=new ArrayList<>();for(String type:types){registry.add(type);registry.add(type);}TpccSql.update(c,"write.type_registry","INSERT IGNORE INTO graph_types(type_name,ancestor)VALUES"+String.join(",",Collections.nCopies(types.size(),"(?,?)")),registry.toArray());registered.addAll(types);}
   dirty.clear();
  }
 }
 static JSONObject body(Connection c,JSONObject x)throws Exception{
  Session s=new Session(c);if(!PRUNED)s.get(s.root);Node wh=s.hop(s.root,"Warehouse",null).get(0);int d=x.getIntValue("d_id");JSONObject whmap=context.getJSONObject("maps").getJSONObject("warehouse");Node district=s.get(uuid(whmap.getJSONObject("districts").getString(Integer.toString(d))));
  if(x.getString("kind").equals("payment")){
   Node customer;int cd=x.getIntValue("c_d_id");if(x.get("c_id")!=null)customer=s.get(mapped("customers",cd+":"+x.getIntValue("c_id")));
   else{Node other=s.get(uuid(whmap.getJSONObject("districts").getString(Integer.toString(cd))));List<Node> matches=s.hop(other.id,"Customer",x.getString("c_last"));matches.sort((a,b)->a.arch.getString("c_first").compareTo(b.arch.getString("c_first")));customer=matches.isEmpty()?null:matches.get(matches.size()/2);}
   if(customer==null)return TpccSql.obj("success",false,"error","customer not found");double amount=x.getDoubleValue("amount");wh.arch.put("w_ytd",wh.arch.getDoubleValue("w_ytd")+amount);district.arch.put("d_ytd",district.arch.getDoubleValue("d_ytd")+amount);customer.arch.put("c_balance",customer.arch.getDoubleValue("c_balance")-amount);customer.arch.put("c_ytd_payment",customer.arch.getDoubleValue("c_ytd_payment")+amount);customer.arch.put("c_payment_cnt",customer.arch.getIntValue("c_payment_cnt")+1);s.mark(wh);s.mark(district);s.mark(customer);int cid=customer.arch.getIntValue("c_id");
   if(customer.arch.getString("c_credit").equals("BC")){String text=cid+","+d+","+wh.arch.getIntValue("w_id")+","+Double.toString(TpccSql.round(amount))+"|"+customer.arch.getString("c_data");customer.arch.put("c_data",text.substring(0,Math.min(500,text.length())));}
   s.child(customer,"GenericEdge","History",TpccSql.obj("h_d_id",d,"h_w_id",wh.arch.getIntValue("w_id"),"h_date",x.getString("timestamp"),"h_amount",amount,"h_data",wh.arch.getString("w_name")+"    "+district.arch.getString("d_name")));s.flush();return TpccSql.obj("success",true,"c_id",cid,"amount",amount);
  }
  Node customer=s.get(mapped("customers",d+":"+x.getIntValue("c_id")));int oid=district.arch.getIntValue("d_next_o_id");district.arch.put("d_next_o_id",oid+1);s.mark(district);JSONArray lines=x.getJSONArray("lines");int local=1;for(Object obj:lines)if(((JSONObject)obj).getIntValue("supply_w_id")!=wh.arch.getIntValue("w_id"))local=0;
  Node order=s.child(customer,"Placed","Order",TpccSql.obj("o_id",oid,"o_c_id",customer.arch.getIntValue("c_id"),"o_d_id",d,"o_entry_d",x.getString("timestamp"),"o_carrier_id",0,"o_ol_cnt",lines.size(),"o_all_local",local,"new_order",true));
  // Native compiler loop prefetch flushes the newly created Order before loading all valid IDs.
  s.flush();List<String> prefetch=new ArrayList<>();for(Object obj:lines){JSONObject line=(JSONObject)obj;int item=line.getIntValue("i_id");prefetch.add(mapped("items",Integer.toString(item)));prefetch.add(mapped("stocks",Integer.toString(item)));}s.load(prefetch);
  double total=0;for(int n=0;n<lines.size();n++){
   JSONObject line=lines.getJSONObject(n);int itemid=line.getIntValue("i_id");String itemJid=mapped("items",Integer.toString(itemid)),stockJid=mapped("stocks",Integer.toString(itemid));if(!s.mem.containsKey(itemJid)||!s.mem.containsKey(stockJid))s.flush();Node item=s.get(itemJid),stock=s.get(stockJid);if(item==null||stock==null)throw new TpccSql.Abort("item not found");s.readable(item);s.readable(stock);
   int qty=line.getIntValue("quantity"),q=stock.arch.getIntValue("s_quantity")-qty;stock.arch.put("s_quantity",q<10?q+91:q);stock.arch.put("s_ytd",stock.arch.getIntValue("s_ytd")+qty);stock.arch.put("s_order_cnt",stock.arch.getIntValue("s_order_cnt")+1);if(line.getIntValue("supply_w_id")!=wh.arch.getIntValue("w_id"))stock.arch.put("s_remote_cnt",stock.arch.getIntValue("s_remote_cnt")+1);s.mark(stock);double amount=TpccSql.round(qty*item.arch.getDoubleValue("i_price"));total+=amount;
   s.child(order,"GenericEdge","OrderLine",TpccSql.obj("ol_number",n+1,"ol_i_id",item.arch.getIntValue("i_id"),"ol_supply_w_id",line.getIntValue("supply_w_id"),"ol_delivery_d","","ol_quantity",qty,"ol_amount",amount,"ol_dist_info",stock.arch.getJSONArray("s_dist").getString(d-1)));
  }
  s.flush();return TpccSql.obj("success",true,"o_id",oid,"total",TpccSql.round(total*(1-customer.arch.getDoubleValue("c_discount"))*(1+wh.arch.getDoubleValue("w_tax")+district.arch.getDoubleValue("d_tax"))),"ol_cnt",lines.size());
 }
}
