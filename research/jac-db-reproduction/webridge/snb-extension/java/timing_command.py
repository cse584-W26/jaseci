#!/usr/bin/env python3
"""Emit/run the frozen same-program paired timer for quiet timing or wire profiling."""
import argparse,importlib.util,json,pathlib
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];I=B/'integration'
spec=importlib.util.spec_from_file_location('ctl',I/'control.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def command(case,out,warm=10,measured=30,phases='baseline,sp',endpoint='127.0.0.1:18537',delay=0):
 case=pathlib.Path(case).resolve();out=pathlib.Path(out).resolve();meta=json.loads((case/'metadata.json').read_text());snapshot=pathlib.Path(meta['snapshot']);variant=meta['variant'];cp=meta['classpath']
 if(H/'timer-overlay-current.json').exists():
  overlay=json.loads((H/'timer-overlay-current.json').read_text());cp=overlay['classes']+':'+cp;out.mkdir(parents=True,exist_ok=True);(out/'timer-overlay.json').write_text(json.dumps(overlay,indent=2))
 flags=['-Dpruned.'+x+'=true'for x in ['auth','acl','schema','hydration']]if variant=='pruned'else[]
 return [str(m.SERVER/'bin/java'),'-Xmx8g','-Dorg.slf4j.simpleLogger.defaultLogLevel=error',*flags,'-Dexperiment.inputs='+str(snapshot/'inputs.json'),'-Dexperiment.mysql.url=jdbc:mysql://'+endpoint+'/'+meta['database']+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true','-Dexperiment.variant='+variant,'-Dexperiment.delay.ms='+str(delay),'-Dalignment.dir='+str(B/'alignment'),'-Dintegration.dir='+str(case),'-Dexecution.dir='+str(out),'-Dintegration.api='+meta['api'],'-cp',cp,'SnbTiming',str(out/'requests/rows.jsonl'),str(warm),str(measured),phases]
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--case',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--warmup',type=int,default=10);p.add_argument('--measured',type=int,default=30);p.add_argument('--phases',default='baseline,sp');p.add_argument('--endpoint',default='127.0.0.1:18537');p.add_argument('--delay-ms',type=float,default=0);p.add_argument('--emit-only',action='store_true');p.add_argument('--timeout',type=int,default=300);a=p.parse_args();cmd=command(a.case,a.out,a.warmup,a.measured,a.phases,a.endpoint,a.delay_ms)
 if a.emit_only:print(json.dumps(cmd));raise SystemExit()
 m.command(cmd,a.out,a.timeout)
