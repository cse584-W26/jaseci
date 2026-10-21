"""Separate diagnostic sampling of active backends in the owned native work database."""
import threading,time,json,gzip,pathlib
import psycopg
class WaitMonitor:
 def __init__(self,path,control,database):self.path=pathlib.Path(path);self.control=pathlib.Path(control);self.database=database;self.done=threading.Event();self.conn=None;self.error=None;self.samples=0;self.thread=threading.Thread(target=self.run,daemon=True)
 def start(self):self.thread.start();return self
 def run(self):
  try:
   with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname=self.database,autocommit=True,options='-c statement_timeout=1000 -c default_transaction_read_only=on -c log_min_duration_statement=-1 -c log_statement=none -c log_duration=off')as conn,gzip.open(self.path,'wt')as stream:
    self.conn=conn;pid=conn.info.backend_pid
    while not self.done.is_set():
     t=time.monotonic_ns();rows=conn.execute("SELECT pid,state,wait_event_type,wait_event,left(query,1024) FROM pg_stat_activity WHERE datname=%s AND backend_type='client backend' AND pid<>pg_backend_pid() AND state='active'",(self.database,)).fetchall()
     try:tag=self.control.read_text().strip()
     except FileNotFoundError:tag='idle'
     for row in rows:stream.write(json.dumps({'mono_ns':t,'wall_ns':time.time_ns(),'request_tag':tag,'pid':row[0],'state':row[1],'wait_event_type':row[2],'wait_event':row[3],'query_prefix':row[4]})+'\n');self.samples+=1
     self.done.wait(max(0,.002-(time.monotonic_ns()-t)/1e9))
  except Exception as e:self.error=repr(e)
 def stop(self):
  self.done.set();self.thread.join(2)
  if self.thread.is_alive()and self.conn:
   try:self.conn.cancel()
   except Exception:pass
   self.thread.join(2)
  receipt={'stopped':not self.thread.is_alive(),'active_backend_samples':self.samples,'target_database':self.database,'target_interval_ms':2,'observer_session_readonly':True,'observer_session_duration_logging':'off; application diagnostic logging unchanged','error':self.error,'scope':'Diagnostic sampling only; pg_stat_activity observer connects directly to Unix socket and is excluded from traced application PID SQL counts; sample frequencies describe observed wait occupancy, not exact duration.'};self.path.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2));return receipt
