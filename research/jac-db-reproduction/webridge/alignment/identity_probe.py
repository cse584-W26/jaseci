"""Diagnostic launcher: logs root/identity memo decisions, without modifying runtime source."""
import json,os,sys,threading,time,functools,traceback
from pathlib import Path
import jaclang
from jaclang.runtimelib.server import UserManager
from jaclang.scale.identity.user_manager import JacScaleUserManager
from jaclang.scale.identity.identity_storage import PgIdentityStorage
OUT=Path(os.environ['ALIGN_IDENTITY_TRACE']);lock=threading.Lock()
def emit(d):
 d.update(wall=time.time(),thread=threading.get_ident())
 with lock,OUT.open('a') as f:f.write(json.dumps(d,default=str)+'\n')
def wrap(cls,name):
 original=getattr(cls,name);glob=getattr(original,'__globals__',{});cache=glob.get('_root_id_request_cache')
 @functools.wraps(original)
 def call(self,*a,**kw):
  before=cache.get() if cache else None
  emit({'event':'enter','hook':cls.__name__+'.'+name,'class':type(self).__name__,'source':original.__code__.co_filename,'root_memo':getattr(self,'_root_memo_enabled',None),'cache_before':before,'callers':[x.name for x in traceback.extract_stack(limit=6)[:-1]]})
  result=original(self,*a,**kw)
  emit({'event':'exit','hook':cls.__name__+'.'+name,'cache_after':cache.get() if cache else None,'result_present':result is not None})
  return result
 setattr(cls,name,call)
for cls,name in [(JacScaleUserManager,'get_root_id'),(PgIdentityStorage,'get_user_by_id')]:wrap(cls,name)
emit({'event':'startup','jac_source':jaclang.__file__,'rootmemo_env':os.environ.get('JAC_ROOT_MEMO')})
sys.argv=['jac','start','main.jac','-p','18109','--no-client']
from jaclang.jac0core.cli_boot import start_cli
start_cli()
