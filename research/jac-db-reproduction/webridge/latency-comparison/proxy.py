#!/usr/bin/env python3
"""Byte-stream response latency: independent receive and deadline delivery tasks."""
import argparse,asyncio,json,time,signal,pathlib
async def main(a):
 stats={'connections':0,'client_bytes':0,'server_bytes':0,'delay_ms':a.delay_ms,'listen_port':a.port,'target':a.unix or f'{a.host}:{a.target_port}'}
 tasks=set(); stop=asyncio.Event()
 async def connection(cr,cw):
  task=asyncio.current_task();tasks.add(task);stats['connections']+=1
  sw=None
  try:
   sr,sw=await asyncio.open_unix_connection(a.unix) if a.unix else await asyncio.open_connection(a.host,a.target_port)
   q=asyncio.Queue()
   async def upstream():
    while data:=await cr.read(65536):
     stats['client_bytes']+=len(data);sw.write(data);await sw.drain()
   async def receive():
    try:
     while data:=await sr.read(65536):
      stats['server_bytes']+=len(data);await q.put((time.monotonic()+a.delay_ms/1000,data))
    finally:await q.put((0,None))
   async def deliver():
    while True:
     deadline,data=await q.get()
     if data is None:return
     await asyncio.sleep(max(0,deadline-time.monotonic()));cw.write(data);await cw.drain()
   jobs=[asyncio.create_task(f()) for f in (upstream,receive,deliver)]
   await asyncio.wait([jobs[0],jobs[2]],return_when=asyncio.FIRST_COMPLETED)
   for j in jobs:j.cancel()
   await asyncio.gather(*jobs,return_exceptions=True)
  except (ConnectionError,OSError):stats['connection_errors']=stats.get('connection_errors',0)+1
  finally:
   for writer in (cw,sw):
    if writer:writer.close()
   tasks.discard(task)
 loop=asyncio.get_running_loop()
 for sig in (signal.SIGTERM,signal.SIGINT):loop.add_signal_handler(sig,stop.set)
 server=await asyncio.start_server(connection,'127.0.0.1',a.port)
 print(json.dumps({'ready':True,**stats}),flush=True)
 try:await stop.wait()
 finally:
  server.close();await server.wait_closed()
  for task in list(tasks):task.cancel()
  await asyncio.gather(*tasks,return_exceptions=True)
  pathlib.Path(a.receipt).write_text(json.dumps({**stats,'stopped':True},indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,required=True);p.add_argument('--delay-ms',type=float,required=True);p.add_argument('--unix');p.add_argument('--host',default='127.0.0.1');p.add_argument('--target-port',type=int);p.add_argument('--receipt',required=True);asyncio.run(main(p.parse_args()))
