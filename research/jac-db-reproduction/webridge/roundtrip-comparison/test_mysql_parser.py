"""Protocol correctness cases: negotiated EOF, empty rows and multiple results."""
from mysql_proxy import Response,Frames

def check(deprecated,empty=False,multi=False):
 events=[];r=Response(lambda e,**x:events.append((e,x)),'test');r.deprecate_eof=deprecated;r.start({'id':1,'at':0})
 seq=0
 def packet(p):
  nonlocal seq
  seq+=1;r.packet(seq,p,seq/1000)
 packet(b'\x01');packet(b'column-definition')
 if not deprecated:packet(b'\xfe\x00\x00\x02\x00')
 if not empty:packet(b'\x01x')
 packet(b'\xfe\x00\x00'+(b'\x0a\x00'if multi else b'\x02\x00')+(b'\x00\x00'if deprecated else b''))
 if multi:packet(b'\x00\x00\x00\x02\x00\x00\x00')
 done=[x for e,x in events if e=='response_complete'];assert len(done)==1 and done[0]['rows']==(0 if empty else 1)and done[0]['resultsets']==1
 assert not [e for e,x in events if e.startswith(('unexpected','overlapping','unsupported'))]
for deprecated in [False,True]:
 for empty in [False,True]:
  for multi in [False,True]:check(deprecated,empty,multi)
# Frame boundaries can occur anywhere, including within the four-byte header.
out=[];f=Frames(lambda seq,p,t:out.append((seq,p)));wire=b'\x03\x00\x00\x01abc\x01\x00\x00\x02z'
for b in wire:f.feed(bytes([b]),0)
assert out==[(1,b'abc'),(2,b'z')]
print('9 parser checks passed')
