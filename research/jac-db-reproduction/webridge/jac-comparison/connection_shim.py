"""Launch-only Unix-socket URL configuration adapter, identical for both variants."""
import runpy,sys,json,os
from urllib.parse import urlparse,parse_qs
import jaclang
import jaclang.runtimelib.session as session
original=session.conninfo_from_url

def socket_conninfo(url):
 info=original(url)
 query=parse_qs(urlparse(url).query);socket=query.get('host',[''])[0]
 if socket.startswith('/'):
  info.unix_socket_dir=socket
 return info

original.__globals__['conninfo_from_url']=socket_conninfo
session.conninfo_from_url=socket_conninfo
if hasattr(session,'Session'):
 for value in vars(session.Session).values():
  if hasattr(value,'__globals__') and value.__globals__.get('conninfo_from_url')is original:value.__globals__['conninfo_from_url']=socket_conninfo
if os.environ.get('JAC_SOCKET_SHIM_CHECK'):
 info=session.conninfo_from_url(os.environ['JAC_DB_URL']);print(json.dumps({'unix_socket_dir':info.unix_socket_dir,'database':info.database,'user':info.user}));raise SystemExit()
sys.argv=['jac',*sys.argv[1:]]
runpy.run_module('jaclang',run_name='__main__')
