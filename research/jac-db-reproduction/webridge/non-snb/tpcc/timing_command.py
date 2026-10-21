#!/usr/bin/env python3
"""Emit exact timer argv from one immutable genuine compiler case."""
import argparse,importlib.util,json,pathlib
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1]
s=importlib.util.spec_from_file_location('original',B/'integration/control.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def command(case,out,phase,warm=10,measure=30,endpoint='127.0.0.1:55337'):
 case=pathlib.Path(case);meta=json.loads((case/'metadata.json').read_text());snapshot=pathlib.Path(meta['snapshot']);out=pathlib.Path(out)
 return ['taskset','-c','9,19',str(m.SERVER/'bin/java'),'-Xmx2g','-Dintegration.dir='+str(case),'-Dexecution.dir='+str(out),'-Dintegration.api='+meta['api'],'-Dexperiment.program='+meta['program'],'-Dexperiment.pruned='+str(meta['variant']=='pruned').lower(),'-Dexperiment.graph.context='+str(snapshot/'graph-context.json'),'-Dexperiment.mysql.url=jdbc:mysql://'+endpoint+'/'+meta['database']+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true','-cp',meta['classpath'],'TpccTiming',str(snapshot/'input.json'),phase,str(warm),str(measure)]
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('case',type=pathlib.Path);p.add_argument('--out',default='{profile_output}');p.add_argument('--endpoint',default='{endpoint}');p.add_argument('--phase',choices=['baseline','sp'],default='sp');p.add_argument('--warm',type=int,default=10);p.add_argument('--measure',type=int,default=3);p.add_argument('--save',type=pathlib.Path,required=True);a=p.parse_args();a.save.write_text(json.dumps(command(a.case,a.out,a.phase,a.warm,a.measure,a.endpoint),indent=2))
