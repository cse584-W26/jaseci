import pathlib,importlib.util
H=pathlib.Path(__file__).resolve().parent;I=H.parents[1]/'integration';s=importlib.util.spec_from_file_location('profile',H/'profile_command.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
def command(q,out,port=55337,warm=0,measure=1,phases='sp'):
 out=pathlib.Path(out).resolve();cmd=p.command(q,out/'requests',port,warm,measure,phases);idx=cmd.index('-cp');case=I/'cases'/p.json.loads((H/'selected-cases.json').read_text())[q];cmd[idx+1]=str(case/'guarded-timer/classes')+':'+cmd[idx+1];cmd[cmd.index('SetTiming')]='GuardSetTiming';cmd.insert(1,'-Dsnb.watchdogDir='+str(out));return cmd
