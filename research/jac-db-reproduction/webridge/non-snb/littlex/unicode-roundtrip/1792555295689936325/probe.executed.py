import pathlib,json,sys,time,subprocess,importlib.util,shutil,hashlib
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
spec=importlib.util.spec_from_file_location('timer',H/'timing_command.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t);out=H/'unicode-roundtrip'/str(time.time_ns());out.mkdir(parents=True);shutil.copy2(H/'UnicodeRoundtrip.java',out/'UnicodeRoundtrip.java');shutil.copy2(__file__,out/'probe.executed.py')
def mysql(q):
 r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-N','-B','-uroot','jac_lx_t200_20261020'],input=q.encode(),capture_output=True);assert r.returncode==0,r.stderr;return r.stdout.decode()
with lease('littleX exact original JSON SELECT parse UPSERT Unicode byte roundtrip',out/'lease.json'):
 cp=str(H/'classes')+':'+t.c.CP;r=subprocess.run([str(t.c.SERVER/'bin/javac'),'-cp',cp,'-d',str(out),str(out/'UnicodeRoundtrip.java')],capture_output=True);assert r.returncode==0,r.stderr;summary=[]
 for mode,extra,setnames in [('collation-only','',False),('full-session-variables','&sessionVariables=character_set_client=utf8mb4,character_set_connection=utf8mb4,character_set_results=utf8mb4',False),('explicit-SET-NAMES','',True)]:
  d=out/mode;table='wb_unicode_probe_'+str(time.time_ns());url='jdbc:mysql://127.0.0.1:55337/jac_lx_t200_20261020?useSSL=false&useUnicode=true&characterEncoding=UTF-8&connectionCollation=utf8mb4_bin&useServerPrepStmts=false&useLocalSessionState=true'+extra;cmd=[str(t.c.SERVER/'bin/java'),'-cp',str(out)+':'+cp,'UnicodeRoundtrip',url,str(d),table]+(['set-names']if setnames else[]);(out/(mode+'-command.json')).write_text(json.dumps(cmd,indent=2)+'\n')
  try:
   r=subprocess.run(cmd,capture_output=True,timeout=30);(out/(mode+'-stderr.log')).write_bytes(r.stderr);assert r.returncode==0,r.stderr;j=json.loads((d/'java-receipt.json').read_text());actual=[]
   for line in mysql("SELECT JSON_OBJECT('id',id,'content',JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.content')),'content_hex',HEX(JSON_UNQUOTE(JSON_EXTRACT(props,'$.archetype.content')))) FROM "+table+" ORDER BY id").split('\n'):
    if line:actual.append(json.loads(line))
   source={x['id']:x for x in j['rows']};matches=[{'id':x['id'],'source_hex':source[x['id']]['source_content_hex'],'stored_hex':x['content_hex'],'equal':x['content_hex']==source[x['id']]['source_content_hex'],'stored_content':x['content']}for x in actual];row={'mode':mode,'effective':j['session'],'driver_encoding':j['driver_encoding'],'rows':matches,'all_original_content_bytes_equal':len(matches)==2 and all(x['equal']for x in matches),'java_receipt':str(d/'java-receipt.json')};summary.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
  finally:mysql('DROP TABLE IF EXISTS '+table)
 (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n');print(out,flush=True)
