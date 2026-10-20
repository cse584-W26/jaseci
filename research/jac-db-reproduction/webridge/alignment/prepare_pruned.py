"""Create an explicit overhead-removal derivative of the full aligned port."""
import difflib,hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parent;source=(p/'AlignedIc5.java').read_text();s=source.replace('public class AlignedIc5','public class PrunedIc5')
s=s.replace(' static long calls;', ''' static final boolean REMOVE_AUTH=Boolean.getBoolean("pruned.auth");
 static final boolean REMOVE_ACL=Boolean.getBoolean("pruned.acl");
 static final boolean REMOVE_SCHEMA=Boolean.getBoolean("pruned.schema");
 static final boolean REMOVE_HYDRATION=Boolean.getBoolean("pruned.hydration");
 static long calls;''')
s=s.replace('if(!knownTypes.contains(type))','if(!REMOVE_SCHEMA&&!knownTypes.contains(type))')
s=s.replace(' static void ensure(Connection c)throws Exception{\n  if(schemaReady)return;',' static void ensure(Connection c)throws Exception{\n  if(REMOVE_SCHEMA||schemaReady)return;')
s=s.replace('  Anchor(ResultSet r)throws Exception{','  Anchor(String id,String type,JSONObject props){this.id=id;this.type=type;this.kind="NodeAnchor";this.props=props;this.arch=props==null?null:props.getJSONObject("archetype");}\n  Anchor(ResultSet r)throws Exception{')
s=s.replace('  boolean readable(Anchor a)throws Exception{','  boolean readable(Anchor a)throws Exception{\n   if(REMOVE_ACL)return true;')
s=s.replace('String sql="SELECT n.id,e.id FROM ("','String sql="SELECT n.id,e.id"+(REMOVE_HYDRATION&&target.equals("Forum")?",CAST(JSON_UNQUOTE(JSON_EXTRACT(n.props,\'$.archetype.forum_id\')) AS SIGNED) AS forum_id,JSON_UNQUOTE(JSON_EXTRACT(n.props,\'$.archetype.title\')) AS title":"")+" FROM ("')
s=s.replace('   List<Anchor> materialized=load(new ArrayList<>(ids));', '''   List<Anchor> materialized;
   if(REMOVE_HYDRATION){
    for(List<Object> row:rows){String id=row.get(0).toString();if(!mem.containsKey(id)){
     JSONObject props=null;if(target.equals("Forum")){JSONObject fields=new JSONObject();fields.put("forum_id",Long.parseLong(row.get(2).toString()));fields.put("title",row.get(3));props=new JSONObject();props.put("archetype",fields);}
     mem.put(id,new Anchor(id,target,props));
    }}
    materialized=new ArrayList<>();for(String id:ids)materialized.add(mem.get(id));
   }else materialized=load(new ArrayList<>(ids));''')
s=s.replace('row.add(r.getObject(i));','row.add(REMOVE_HYDRATION && n==4 && i==4 ? r.getString(i) : r.getObject(i));')
s=s.replace('if(!roots.isEmpty())load(new ArrayList<>(roots));','if(!REMOVE_ACL&&!roots.isEmpty())load(new ArrayList<>(roots));')
s=s.replace('String uid=context.getString("user_id");String root=clientRootContext.get(uid);','String uid=context.getString("user_id");String root=REMOVE_AUTH?uuid(context.getString("root_id")):clientRootContext.get(uid);')
s=s.replace('Session s=new Session(c,root);Anchor rootAnchor=s.get(root);if(rootAnchor==null)throw new SecurityException("Missing root anchor");Anchor person=s.get(x.getString("person_jid"));','Session s=new Session(c,root);if(!REMOVE_ACL){Anchor rootAnchor=s.get(root);if(rootAnchor==null)throw new SecurityException("Missing root anchor");}Anchor person=REMOVE_HYDRATION?new Anchor(x.getString("person_jid"),"Person",null):s.get(x.getString("person_jid"));')
s=s.replace('  Class.forName("com.mysql.jdbc.Driver");','  if(REMOVE_HYDRATION&&!REMOVE_ACL)throw new IllegalArgumentException("Hydration removal requires ACL removal: ACL reads original object permissions");\n  Class.forName("com.mysql.jdbc.Driver");')
s=s.replace('row.put("round",round);','row.put("removals",Arrays.asList(REMOVE_AUTH,REMOVE_ACL,REMOVE_SCHEMA,REMOVE_HYDRATION));row.put("round",round);')
(p/'PrunedIc5.java').write_text(s);(p/'pruned-vs-full.diff').write_text(''.join(difflib.unified_diff(source.splitlines(True),s.splitlines(True),fromfile='AlignedIc5.java',tofile='PrunedIc5.java')))
ledger={'base_source':'AlignedIc5.java','base_sha256':hashlib.sha256(source.encode()).hexdigest(),'derivative':'PrunedIc5.java','derivative_sha256':hashlib.sha256(s.encode()).hexdigest(),'default':'All removal flags false: derivative follows full port','execution_status':'Prepared offline; validation awaits dedicated live window','removals':[
 {'flag':'-Dpruned.auth=true','removes':'Identity lookup/root-context establishment','replacement':'Previously validated service user/root supplied by declared fixture context','keeps':'Same logical service root and input UUIDs'},
 {'flag':'-Dpruned.acl=true','removes':'Owner-root initialization/prefetch and object permission evaluation','replacement':'Benchmark fixture has one service-account owner for the social graph','keeps':'Graph relation predicates, type tests and traversal ordering'},
 {'flag':'-Dpruned.schema=true','removes':'Cold VERSION/schema-fingerprint/type-registry initialization','replacement':'Preloaded declared experiment fixture/schema','keeps':'Type-inheritance predicates inside actual domain hop SQL'},
 {'flag':'-Dpruned.hydration=true','requires':'pruned.acl=true','removes':'Session batch_get full-anchor object loads and entry object reconstruction','replacement':'Lightweight UUID/type records; Only forum_id/title scalar fields project from the existing Forum traversal, constructing lightweight typed fields','keeps':'Same number/order of Knows, HasMember, ContainerOf and per-post HasCreator traversal calls, plus request-local identity deduplication'}],
 'retained':['Read-only repeatable-read transaction and lock-wait setting','Every original friend/forum/post/creator traversal loop','UUID and edge sequence identity','Membership date predicate','Per-forum joined-friend sets and per-post creator membership test','Final sort and top20','Original generic graph storage and joins; no relational count aggregation'],
 'validation_required':['All20 result oracles','Independent MySQL Questions count equals executed JDBC count','Per-input per-domain-hop counts exactly equal full port','Stepwise flags report actual removed categories; no prescribed count padding']}
(p/'removal-ledger.json').write_text(json.dumps(ledger,indent=2))
print('Prepared derivative',ledger['base_sha256'])
