#!/usr/bin/env python3
"""Emit frozen-case original-driver argv for the coordinator's diagnostic/latency runner."""
import pathlib,importlib.util,sys,json
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];I=B/'integration';s=importlib.util.spec_from_file_location('ctl',I/'control.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def command(q,out,port=18547,warm=10,measure=3,phases='baseline,sp'):
 c=I/'cases'/json.loads((H/'selected-cases.json').read_text())[q];cp=':'.join([str(c/'source/classes'),str(I/'recorded-bind-types/classes'),str(I/'json-type-compat/classes'),str(I/'numeric-width/classes'),str(I/'jdbc-string/combined'),m.CP]);return [str(m.SERVER/'bin/java'),'-Xmx8g',*(['-Dsnb.finiteDepth=true']if q=='ic13'else[]),*(['-Dsnb.branchTopk=true']if q=='ic2'else[]),'-Dsnb.query='+q,'-Dsnb.url=jdbc:mysql://127.0.0.1:'+str(port)+'/jac_snb_six_20261020?useSSL=false&useUnicode=true&characterEncoding=UTF-8&useServerPrepStmts=false&useLocalSessionState=true','-Dorg.slf4j.simpleLogger.defaultLogLevel=error','-cp',cp,'SetTiming',str(H/'runtime-data'/q),str(c),str(pathlib.Path(out).resolve()),str(warm),str(measure),phases]
if __name__=='__main__':print(json.dumps(command(sys.argv[1],sys.argv[2],*(map(int,sys.argv[3:]))),indent=2))
