#!/usr/bin/env python3
"""Instrumented MySQL byte-stream proxy. Log frame metadata and SQL, not rows/auth."""
import argparse,asyncio,json,pathlib,signal,time

def lenenc(p,i=0):
 b=p[i]
 if b<251:return b,i+1
 n={252:2,253:3,254:8}[b];return int.from_bytes(p[i+1:i+1+n],'little'),i+1+n

def status(p):
 if p[0]==254 and len(p)<9:return int.from_bytes(p[3:5],'little')
 _,i=lenenc(p,1);_,i=lenenc(p,i);return int.from_bytes(p[i:i+2],'little')

class Frames:
 def __init__(self,callback):self.buffer=bytearray();self.callback=callback
 def feed(self,data,stamp):
  self.buffer.extend(data)
  while len(self.buffer)>=4:
   n=int.from_bytes(self.buffer[:3],'little')
   if len(self.buffer)<n+4:return
   seq=self.buffer[3];p=bytes(self.buffer[4:n+4]);del self.buffer[:n+4];self.callback(seq,p,stamp)

class Response:
 def __init__(self,emit,stage):self.emit=emit;self.stage=stage;self.command=None;self.deprecate_eof=False
 def start(self,cmd):
  if self.command is not None:self.emit('overlapping_command',stage=self.stage,previous=self.command['id'],next=cmd['id'])
  self.command=cmd;self.mode='first';self.left=0;self.results=0;self.rows=0;self.frames=0
 def finish(self,t,error=False):
  self.emit('response_complete',stage=self.stage,command_id=self.command['id'],at=t,elapsed_ms=(t-self.command['at'])*1000,frames=self.frames,resultsets=self.results,rows=self.rows,error=error)
  self.command=None
 def packet(self,seq,p,t):
  if self.command is None:return
  self.frames+=1;self.emit('server_frame',stage=self.stage,command_id=self.command['id'],sequence=seq,payload_bytes=len(p),state=self.mode,at=t)
  if not p:return
  if p[0]==255:self.finish(t,True);return
  if self.mode=='first':
   if p[0]==0:
    if status(p)&8:self.mode='first'
    else:self.finish(t)
   elif p[0]==251:self.emit('unsupported_local_infile',stage=self.stage,at=t)
   else:self.left,_=lenenc(p);self.results+=1;self.mode='columns'
  elif self.mode=='columns':
   self.left-=1
   if not self.left:self.mode='rows' if self.deprecate_eof else 'columns_eof'
  elif self.mode=='columns_eof':
   if not (p[0]==254 and len(p)<9):self.emit('unexpected_column_terminator',stage=self.stage,at=t)
   self.mode='rows'
  elif self.mode=='rows':
   if p[0]==254 and len(p)<9:
    if status(p)&8:self.mode='first'
    else:self.finish(t)
   else:self.rows+=1

async def main(a):
 trace=pathlib.Path(a.trace).open('w');stats={'connections':0,'client_bytes':0,'server_bytes':0,'delay_ms':a.delay_ms,'listen_port':a.port};tasks=set();stop=asyncio.Event()
 def emit(cid,event,**kw):trace.write(json.dumps({'connection':cid,'event':event,**kw})+'\n')
 async def connection(cr,cw):
  task=asyncio.current_task();tasks.add(task);stats['connections']+=1;cid=stats['connections'];sw=None;jobs=[];n=0
  emit(cid,'connection_open',at=time.monotonic())
  try:
   sr,sw=await asyncio.open_connection('127.0.0.1',a.target_port);q=asyncio.Queue()
   log=lambda event,**kw:emit(cid,event,**kw)
   rx=Response(log,'received');tx=Response(log,'delivered')
   def client(seq,p,t):
    nonlocal n
    # Handshake auth uses sequence1; JDBC text commands begin a new sequence0.
    if seq==1 and n==0 and len(p)>=4:
     capabilities=int.from_bytes(p[:4],'little');rx.deprecate_eof=tx.deprecate_eof=bool(capabilities&0x01000000);log('client_capabilities',deprecate_eof=rx.deprecate_eof,capability_flags=capabilities,at=t)
    if seq!=0 or not p:return
    if p[0]==1:log('quit',at=t);return
    if p[0]!=3:log('other_client_command',opcode=p[0],payload_bytes=len(p),at=t);return
    n+=1;cmd={'id':n,'at':t,'sql':p[1:].decode('utf-8','replace')};log('command',**cmd);rx.start(cmd);tx.start(cmd)
   cp=Frames(client);rp=Frames(rx.packet);tp=Frames(tx.packet)
   async def upstream():
    while data:=await cr.read(65536):
     t=time.monotonic();stats['client_bytes']+=len(data);log('client_chunk',at=t,bytes=len(data));cp.feed(data,t);sw.write(data);await sw.drain()
   async def receive():
    try:
     while data:=await sr.read(65536):
      t=time.monotonic();stats['server_bytes']+=len(data);log('server_chunk',at=t,bytes=len(data));rp.feed(data,t);await q.put((t+a.delay_ms/1000,data))
    finally:await q.put((0,None))
   async def deliver():
    while True:
     deadline,data=await q.get()
     if data is None:return
     await asyncio.sleep(max(0,deadline-time.monotonic()));cw.write(data);await cw.drain();t=time.monotonic();log('delivered_chunk',at=t,bytes=len(data));tp.feed(data,t)
   jobs=[asyncio.create_task(f())for f in (upstream,receive,deliver)]
   done,_=await asyncio.wait([jobs[0],jobs[2]],return_when=asyncio.FIRST_COMPLETED)
   for j in done:
    if j.exception():raise j.exception()
  except (ConnectionError,OSError)as e:log('connection_error',error=type(e).__name__,at=time.monotonic())
  finally:
   for j in jobs:j.cancel()
   await asyncio.gather(*jobs,return_exceptions=True)
   for w in (cw,sw):
    if w:w.close()
   emit(cid,'connection_close',at=time.monotonic());tasks.discard(task);trace.flush()
 loop=asyncio.get_running_loop()
 for sig in (signal.SIGTERM,signal.SIGINT):loop.add_signal_handler(sig,stop.set)
 server=await asyncio.start_server(connection,'127.0.0.1',a.port);print(json.dumps({'ready':True,**stats}),flush=True)
 try:await stop.wait()
 finally:
  server.close();await server.wait_closed()
  for t in list(tasks):t.cancel()
  await asyncio.gather(*tasks,return_exceptions=True);trace.close();pathlib.Path(a.receipt).write_text(json.dumps({**stats,'stopped':True},indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18537);p.add_argument('--target-port',type=int,default=55337);p.add_argument('--delay-ms',type=float,default=2);p.add_argument('--trace',required=True);p.add_argument('--receipt',required=True);asyncio.run(main(p.parse_args()))
