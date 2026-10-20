#!/usr/bin/env python3
"""Capture actual prepared EXPLAIN plans from retained generic pilot source; diagnostics only."""
import pathlib,subprocess,hashlib,json
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];G=H/'gates-20261020T215618Z';O=H/'selected-plans';O.mkdir(exist_ok=False);C=O/'classes';C.mkdir();source=(G/'SnbSetSql.java').read_text()
source=source.replace('static long calls;', 'static int planNo=0;static long calls;')
source=source.replace('try(ResultSet r=s.executeQuery()){while(r.next())', '''try(PreparedStatement ex=c.prepareStatement("EXPLAIN FORMAT=JSON "+q)){for(int i=0;i<args.length;i++){Object x=args[i];if(x instanceof Long)ex.setLong(i+1,(Long)x);else if(x instanceof Integer)ex.setInt(i+1,(Integer)x);else ex.setString(i+1,(String)x);}try(ResultSet er=ex.executeQuery()){er.next();JSONObject detail=new JSONObject();detail.put("sql",q);detail.put("parameters",Arrays.asList(args));detail.put("plan",JSON.parse(er.getString(1)));Files.write(Paths.get(System.getProperty("snb.planDir"),"plan-"+(planNo++)+".json"),detail.toJSONString().getBytes("UTF-8"));}}try(ResultSet r=s.executeQuery()){while(r.next())''')
source=source.replace('for(Object value:inputs){','for(Object value:inputs.subList(0,1)){')
(O/'SnbSetSql.java').write_text(source);cp=':'.join(map(str,[C,B/'deps/mysql-connector-java-5.1.46.jar',B/'deps/fastjson2-2.0.9.jar']));subprocess.run([str(B/'boot-jdk8/bin/javac'),'-cp',cp,'-d',str(C),str(O/'SnbSetSql.java')],check=True)
java=B.parents[1]/'webridge/SourceCode/openjdk8-webridge/build/linux-x86_64-normal-server-release/images/j2sdk-image/bin/java'
for q in ['is1','is2','is3','ic1','ic2','ic13']:
 p=O/q;p.mkdir();subprocess.run(['taskset','-c','9,19',str(java),*(['-Dsnb.finiteDepth=true']if q=='ic13'else[]),*(['-Dsnb.branchTopk=true']if q=='ic2'else[]),'-Dsnb.planDir='+str(p),'-cp',cp,'SnbSetSql',q,str(B/'snb-extension/inputs-all20.json'),str(p/'run')],check=True)
(O/'receipt.json').write_text(json.dumps({'pilot_sha256':hashlib.sha256((G/'SnbSetSql.java').read_bytes()).hexdigest(),'instrumented_sha256':hashlib.sha256((O/'SnbSetSql.java').read_bytes()).hexdigest(),'purpose':'Prepared EXPLAIN FORMAT=JSON using exact idx0 parameters, selected shared-auxiliary algorithm, after uniformUTF8 migration; diagnostic timing only'},indent=2)+'\n')
