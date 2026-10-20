#!/usr/bin/env python3
"""Bound one generated CALL with exact owned-connection server cleanup."""
import pathlib,json,subprocess,time,sys
H=pathlib.Path(__file__).resolve().parent;I=H.parents[1]/'integration';q=sys.argv[1];budget=float(sys.argv[2])if len(sys.argv)>2 else 15;c=I/'cases'/json.loads((H/'selected-cases.json').read_text())[q];start=time.time();out=H/('guard-'+q+'-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));out.mkdir();log=(out/'driver.log').open('w');p=subprocess.Popen([sys.executable,str(H/'webridge.py'),q,'optimized'],stdout=log,stderr=subprocess.STDOUT);cid=None;connected=None;killed=False;receipt={'query':q,'budget_after_connection_s':budget,'started_unix':start}
def sql(s):return subprocess.check_output(['docker','exec','jac-webridge-mysql57','mysql','-uroot','-N','-B','-e',s],text=True)
try:
 while p.poll()is None:
  if cid is None:
   paths=[x for x in c.glob('optimized-*/connection-id.json')if x.stat().st_mtime>=start]
   if paths:cid=int(json.loads(paths[-1].read_text()));connected=time.monotonic();receipt['connection_id']=cid;receipt['connection_receipt']=str(paths[-1])
  if cid is not None and time.monotonic()-connected>budget:
   receipt['processlist_before_kill']=sql('SELECT ID,USER,DB,COMMAND,TIME,STATE,INFO FROM information_schema.PROCESSLIST WHERE ID='+str(cid));sql('KILL CONNECTION '+str(cid));killed=True;break
  if time.time()-start>90:receipt['startup_timeout']=True;break
  time.sleep(.1)
 if killed:
  deadline=time.monotonic()+5
  while time.monotonic()<deadline and sql('SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID='+str(cid)).strip()!='0':time.sleep(.1)
  receipt['server_connection_absent']=sql('SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID='+str(cid)).strip()=='0'
 try:p.wait(timeout=10)
 except subprocess.TimeoutExpired:p.kill();p.wait()
 receipt.update({'driver_returncode':p.returncode,'server_kill_triggered':killed,'ended_unix':time.time()})
finally:log.close();(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(out)
