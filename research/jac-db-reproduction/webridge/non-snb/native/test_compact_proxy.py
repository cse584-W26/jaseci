"""Offline metadata-state tests; no socket or database access."""
import compact_proxy as p,io,tempfile,pathlib,json,unittest
class Flights(unittest.TestCase):
 def setUp(self):
  p.META.clear();p.PREPARED.clear();p.SQLS.clear();p.FLIGHT_N=0;p.LOG=io.StringIO();self.t=tempfile.TemporaryDirectory();p.CONTROL=pathlib.Path(self.t.name)/'tag';p.CONTROL.write_text('request-test')
 def e(self,event,**kw):p.emit(event,connection=1,**kw)
 def front(self,kind,**kw):self.e('frame',direction='frontend',type=kind,bytes=5,start_chunk=1,end_chunk=1,backend_pid=42,**kw)
 def ready(self,chunk=2):self.e('frame',direction='backend',type='Z',bytes=6,start_chunk=chunk,end_chunk=chunk,backend_pid=42,transaction_status='I');self.e('chunk_delivered',direction='backend',chunk=chunk)
 def test_sql_and_many_rows_emit_only_one_flight(self):
  self.e('chunk_received',direction='frontend',chunk=1);self.front('P',statement='x',sql='SELECT 1');self.front('B',statement='x');self.front('E');self.front('S')
  for _ in range(10000):self.e('frame',direction='backend',type='D',bytes=100,start_chunk=2,end_chunk=2,backend_pid=42)
  self.assertEqual(p.LOG.getvalue(),'');self.ready();x=json.loads(p.LOG.getvalue());self.assertEqual(x['SQL_count'],1);self.assertEqual(x['backend_types']['D'],10000);self.assertEqual(x['backend_pid'],42);self.assertFalse(x['pipelined_before_prior_reply']);self.assertEqual(x['terminal_backend_type'],'Z')
 def test_prepare_only_and_startup(self):
  self.e('chunk_received',direction='frontend',chunk=1);self.front('Startup');self.front('P',statement='x',sql='SELECT 1');self.front('S');self.ready();x=json.loads(p.LOG.getvalue());self.assertEqual(x['SQL_count'],0);self.assertEqual(x['kind'],'prepare_only');self.assertEqual(x['frontend_types'],'PS')
 def tearDown(self):self.t.cleanup()
if __name__=='__main__':unittest.main()
