#!/usr/bin/env python3
"""Compact top-level command RTT, frozen TPC-C sources, atomic short pair leases."""
import argparse,datetime,hashlib,importlib.util,json,pathlib,signal,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent;H=D.parent;N=H.parent
sys.path.insert(0,str(D));import helpers as h;from extract import extract
PROXY=N/'littlex/primary-rtt/compact_proxy.py'
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run_case(c,delay,out,port):
 out.mkdir(parents=True,exist_ok=False);summary=[]
 with h.lease('TPC-C compact primary RTT '+c['workload']+' '+c['program']+' '+c['variant']+' '+str(delay),out/'lease.json'):
  before=h.settings();assert before['logging'].split('\t')[0]=='0';(out/'instrumentation-before.json').write_text(json.dumps(before,indent=2));h.sql("UPDATE performance_schema.setup_instruments SET ENABLED='NO',TIMED='NO' WHERE NAME LIKE 'statement/sp/%'")
  log=(out/'proxy.log').open('w');argv=[sys.executable,str(PROXY),'--port',str(port),'--target-port','55337','--delay-ms',str(delay),'--trace',str(out/'compact.jsonl'),'--receipt',str(out/'proxy-cleanup.json')];proxy=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);(out/'proxy-command.json').write_text(json.dumps({'argv':argv,'sha256':hashlib.sha256(PROXY.read_bytes()).hexdigest(),'start_utc':stamp()},indent=2))
  try:
   for _ in range(200):
    if '"ready": true'in(out/'proxy.log').read_text():break
    assert proxy.poll()is None;time.sleep(.05)
   else:raise RuntimeError('Proxy not ready')
   for phase in ['baseline','sp']:
    base={'family':'tpcc','workload':c['workload'],'arm':('java_'if phase=='baseline'else'webridge_')+('conventional'if c['program']=='conventional'else c['variant']),'phase':phase,'delay_ms':delay,'case':c['case'],'metric':'per-request sum of outer SQL command-to-complete-response delivery RTT','scope':'Compact parser; no per-frame/row trace. Fresh initial state; ten mutating warmups plus thirty measured requests.'}
    if phase=='sp'and not c['sp_ready']:
     summary.append(dict(base,status='failed_with_stage_evidence',median_ms=None,n=0,failure=c['failure'],pipeline=c['pipeline']));continue
    p=out/phase;p.mkdir();reset=[sys.executable,str(H/'reset_cell.py'),'--case',c['case'],'--phase',phase,'--receipt',str(p/'reset.json')];subprocess.run(reset,check=True)
    command=h.t.command(c['case'],p,phase,10,30,'127.0.0.1:'+str(port));meta=json.loads((pathlib.Path(c['case'])/'metadata.json').read_text());(p/'command.json').write_text(json.dumps(command,indent=2));guard=h.w.run(command,p,timeout=900,request_limit=15,db=meta['database']);h.absence(p,meta['database']);assert not guard['timed_out'],'Incomplete request sequence'
    rows=[json.loads(x)for x in(p/'rows.jsonl').read_text().splitlines()];assert len(rows)==40
    if phase=='sp':h.compare(out/'baseline',p,out)
    summary.append(dict(base,status='pending_compact_extraction',n=30,sample_n=30,warmup_n=10,timer='per-request sum SQL round-trip RTT',raw_rows=str(p/'rows.jsonl'),correctness=str(out/'correctness.json')if phase=='sp'else str(p/'after/manifest.json')))
  finally:
   if proxy.poll()is None:proxy.send_signal(signal.SIGTERM)
   try:proxy.wait(timeout=5)
   except subprocess.TimeoutExpired:proxy.kill();proxy.wait()
   log.close();h.restore(before,out);(out/'proxy-process.json').write_text(json.dumps({'pid':proxy.pid,'returncode':proxy.returncode,'stopped':proxy.poll()is not None,'end_utc':stamp()},indent=2))
  for row in summary:
   if row['status']=='pending_compact_extraction':
    r=extract(out/'compact.jsonl',out/row['phase'],out/row['phase']/'rtt');row.update(status='accepted',median_ms=r['median_ms'],n=r['n'],rtt_summary=str(out/row['phase']/'rtt/summary.json'),rows_path=r['rows_path'],command_counts=r['command_counts'],sql_command_count_distribution=r['command_counts'],response_exchange_count_distribution=r['command_counts'],requests_artifact=r['rows_path'],call_requests=r['call_requests'])
  (out/'summary.json').write_text(json.dumps(summary,indent=2))
 return summary
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--pilot',action='store_true');p.add_argument('--port',type=int,default=18637);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False);cases=json.loads((H/'case-status.json').read_text());rows=[]
 if a.pilot:cases=[c for c in cases if c['program']=='conventional'and c['workload']=='payment_name_GC']
 for delay in([0]if a.pilot else[0,2,10]):
  for c in cases:
   cell=a.out/f'delay-{delay}ms'/(c['program']+'-'+c['variant'])/c['workload']
   rows+=run_case(c,delay,cell,a.port);(a.out/'normalized-rtt-latency.json').write_text(json.dumps(rows,indent=2));print(stamp(),delay,c['program'],c['variant'],c['workload'],'complete',flush=True)
