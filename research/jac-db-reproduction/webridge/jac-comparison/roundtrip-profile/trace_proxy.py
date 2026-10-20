"""Instrumented PostgreSQL byte-stream delay proxy; separate from quiet timing."""
import asyncio,argparse,time,json,pathlib,signal,struct,os
class Parser:
 def __init__(self,conn,direction):self.c=conn;self.direction=direction;self.buf=bytearray();self.first_chunk=None
 def feed(self,data,chunk):
  if not self.buf:self.first_chunk=chunk
  self.buf.extend(data)
  while self.buf:
   extra={}
   if self.direction=='frontend'and self.c['startup']:
    if len(self.buf)<4:return
    length=struct.unpack('!I',self.buf[:4])[0]
    if length<8 or length>64*1024*1024:raise ValueError(('startup length',length))
    if len(self.buf)<length:return
    frame=bytes(self.buf[:length]);del self.buf[:length];code=struct.unpack('!I',frame[4:8])[0];kind='SSLRequest'if code==80877103 else'CancelRequest'if code==80877102 else'Startup';extra['protocol']=code
    if kind=='SSLRequest':self.c['ssl_pending']=True
    elif kind=='Startup':self.c['startup']=False
   elif self.direction=='backend'and self.c['ssl_pending']:
    frame=bytes(self.buf[:1]);del self.buf[:1];length=1;kind='SSLResponse';extra['response']=frame.decode('ascii');self.c['ssl_pending']=False
    if frame!=b'N':raise ValueError('This native-socket experiment expects TLS denial')
   else:
    if len(self.buf)<5:return
    kind=chr(self.buf[0]);length=struct.unpack('!I',self.buf[1:5])[0]+1
    if length<5 or length>64*1024*1024:raise ValueError(('frame length',kind,length))
    if len(self.buf)<length:return
    frame=bytes(self.buf[:length]);del self.buf[:length];payload=frame[5:]
    if self.direction=='frontend':
     if kind=='P':
      statement,sql,rest=payload.split(b'\0',2);extra.update(statement=statement.decode(),sql=sql.decode('utf-8'),parameter_type_count=struct.unpack('!H',rest[:2])[0])
     elif kind=='B':
      portal,statement,rest=payload.split(b'\0',2);formats=struct.unpack('!H',rest[:2])[0];rest=rest[2+2*formats:];extra.update(portal=portal.decode(),statement=statement.decode(),parameter_count=struct.unpack('!H',rest[:2])[0])
     elif kind=='D':extra.update(target=chr(payload[0]),name=payload[1:-1].decode())
     elif kind=='E':extra['portal']=payload.split(b'\0',1)[0].decode()
     elif kind=='Q':extra['sql']=payload[:-1].decode('utf-8')
    else:
     if kind=='K':self.c['backend_pid']=struct.unpack('!I',payload[:4])[0];extra['backend_pid']=self.c['backend_pid']
     elif kind=='Z':extra['transaction_status']=payload.decode()
     elif kind=='C':extra['command_tag']=payload[:-1].decode('utf-8')
     elif kind in ('T','t','D'):extra['field_count']=struct.unpack('!H',payload[:2])[0]
   emit('frame',connection=self.c['id'],direction=self.direction,type=kind,bytes=length,start_chunk=self.first_chunk,end_chunk=chunk,backend_pid=self.c.get('backend_pid'),**extra if not('backend_pid'in extra)else{k:v for k,v in extra.items()if k!='backend_pid'})
   self.first_chunk=chunk if self.buf else None

def tag():
 try:return CONTROL.read_text().strip()
 except FileNotFoundError:return'warmup'
def emit(event,**fields):
 item={'event':event,'mono_ns':time.monotonic_ns(),'wall_ns':time.time_ns(),'request_tag':tag(),**fields};LOG.write(json.dumps(item)+'\n');LOG.flush()
async def main(a):
 global CONTROL,LOG
 out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);CONTROL=pathlib.Path(a.control);path=out/'events.jsonl';fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);LOG=os.fdopen(fd,'w');stats={'connections':0,'client_received_bytes':0,'client_forwarded_bytes':0,'server_received_bytes':0,'server_delivered_bytes':0,'peak_pending_payload_bytes':0,'delay_ms':a.delay_ms};tasks=set();stop=asyncio.Event()
 async def connection(cr,cw):
  tasks.add(asyncio.current_task());stats['connections']+=1;c={'id':stats['connections'],'startup':True,'ssl_pending':False};sw=None;pending=0;jobs=[]
  def raw(direction,data):
   t=tag()
   if not t.startswith('request-'):return
   path=out/(t+'-c'+str(c['id'])+'-'+direction+'.bin');fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
   with os.fdopen(fd,'ab')as f:f.write(data)
  try:
   sr,sw=await asyncio.open_unix_connection(a.unix);q=asyncio.Queue();fp=Parser(c,'frontend');bp=Parser(c,'backend');emit('connect',connection=c['id'])
   async def upstream():
    chunk=0
    while data:=await cr.read(65536):
     chunk+=1;stats['client_received_bytes']+=len(data);raw('frontend',data);emit('chunk_received',connection=c['id'],direction='frontend',chunk=chunk,bytes=len(data));fp.feed(data,chunk);sw.write(data);await sw.drain();stats['client_forwarded_bytes']+=len(data);emit('chunk_forwarded',connection=c['id'],direction='frontend',chunk=chunk,bytes=len(data))
   async def receive():
    nonlocal pending
    chunk=0
    try:
     while data:=await sr.read(65536):
      chunk+=1;deadline=time.monotonic()+a.delay_ms/1000;stats['server_received_bytes']+=len(data);pending+=len(data);stats['peak_pending_payload_bytes']=max(stats['peak_pending_payload_bytes'],pending);raw('backend',data);emit('chunk_received',connection=c['id'],direction='backend',chunk=chunk,bytes=len(data),deadline_mono_ns=int(deadline*1e9));bp.feed(data,chunk);await q.put((deadline,data,chunk))
    finally:await q.put((0,None,0))
   async def deliver():
    nonlocal pending
    while True:
     deadline,data,chunk=await q.get()
     if data is None:return
     await asyncio.sleep(max(0,deadline-time.monotonic()));cw.write(data);await cw.drain();pending-=len(data);stats['server_delivered_bytes']+=len(data);emit('chunk_delivered',connection=c['id'],direction='backend',chunk=chunk,bytes=len(data),deadline_mono_ns=int(deadline*1e9))
   jobs=[asyncio.create_task(f())for f in(upstream,receive,deliver)];done,_=await asyncio.wait(jobs,return_when=asyncio.FIRST_COMPLETED)
   for job in done:
    if job.exception():raise job.exception()
  except asyncio.CancelledError:raise
  except Exception as e:emit('connection_error',connection=c['id'],error=repr(e));stats['errors']=stats.get('errors',0)+1
  finally:
   for job in jobs:job.cancel()
   await asyncio.gather(*jobs,return_exceptions=True)
   for writer in(cw,sw):
    if writer:writer.close()
   emit('disconnect',connection=c['id'],backend_pid=c.get('backend_pid'),pending_payload_bytes=pending);tasks.discard(asyncio.current_task())
 loop=asyncio.get_running_loop()
 for s in(signal.SIGTERM,signal.SIGINT):loop.add_signal_handler(s,stop.set)
 server=await asyncio.start_server(connection,'127.0.0.1',a.port);print(json.dumps({'ready':True,'port':a.port}),flush=True)
 try:await stop.wait()
 finally:
  server.close();await server.wait_closed()
  for t in list(tasks):t.cancel()
  await asyncio.gather(*tasks,return_exceptions=True);LOG.close();(out/'receipt.json').write_text(json.dumps(stats|{'stopped':True},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18532);p.add_argument('--delay-ms',type=float,required=True);p.add_argument('--unix',default='/tmp/jacpg-d6275e76eb/.s.PGSQL.5432');p.add_argument('--out',required=True);p.add_argument('--control',required=True);asyncio.run(main(p.parse_args()))
