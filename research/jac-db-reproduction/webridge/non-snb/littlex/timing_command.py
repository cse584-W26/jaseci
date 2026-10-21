#!/usr/bin/env python3
"""Pure command factory for shared profiling/timing runners; creates no live processes."""
import pathlib,importlib.util,json,argparse
H=pathlib.Path(__file__).resolve().parent;W=H.parents[1];s=importlib.util.spec_from_file_location('c',W/'integration/control.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
def command(plan,out,database,port=55337,phase='baseline',implementation='LittleXSql',bundle=None):
 cp=':'.join([str(H/'classes'),str(W/'integration/recorded-bind-types/classes'),str(W/'integration/json-type-compat/classes'),str(W/'integration/numeric-width/classes'),str(W/'integration/jdbc-string/combined'),c.CP]);cmd=['taskset','-c','9,19',str(c.SERVER/'bin/java'),'-Xmx2g','-Dlittlex.implementation='+implementation,'-Dlittlex.templates='+str(H/'native-templates.json'),'-Dlittlex.url=jdbc:mysql://127.0.0.1:'+str(port)+'/'+database+'?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true&connectionCollation=utf8mb4_bin','-cp',cp,'LittleXTiming',str(pathlib.Path(plan).resolve()),str(pathlib.Path(out).resolve()),phase]
 if phase=='sp':assert bundle;cmd.append(str(pathlib.Path(bundle).resolve()))
 return cmd
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',required=True,type=pathlib.Path);p.add_argument('--out',required=True,type=pathlib.Path);p.add_argument('--database',required=True);p.add_argument('--port',type=int,default=55337);p.add_argument('--phase',default='baseline',choices=['baseline','sp']);p.add_argument('--implementation',default='LittleXSql');p.add_argument('--bundle');a=p.parse_args();print(json.dumps(command(a.plan,a.out,a.database,a.port,a.phase,a.implementation,a.bundle),indent=2))
