import json,pathlib,subprocess,time,sys
p=pathlib.Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=True)
c=subprocess.Popen(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','--unbuffered','jac_snb_six_20261020','-e','SELECT CONNECTION_ID(); SELECT SLEEP(30);'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
cid=int(c.stdout.readline().strip());(p/'connection-id.json').write_text(json.dumps({'connection_id':cid}));(p/'request-active.json').write_text(json.dumps({'start_wall_ms':time.time()*1000,'phase':'selftest','iteration':0,'warmup':False}))
out,err=c.communicate();print(json.dumps({'client_returncode':c.returncode,'stderr':err}));sys.exit(c.returncode)
