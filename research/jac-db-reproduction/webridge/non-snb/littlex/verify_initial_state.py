#!/usr/bin/env python3
"""Bind both MySQL representations to the independently derived source-fixture state."""
import pathlib,sys,json,subprocess,time
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
sys.path.insert(0,str(H.parent/'native'));from littlex_oracle import Oracle
from business_state import snapshot,expected,assert_expected
out=H/('initial-common-state-'+str(time.time_ns()));out.mkdir();receipt={}
with lease('littlex independent initial common-state validation',out/'lease.json'):
 for tier in ['t20','t50','t100','t200']:
  subprocess.run([sys.executable,str(H/'reset_relations.py'),tier,'--lease-held'],check=True,capture_output=True);fixture=H.parent/'native/littlex-oracle-fixtures'/(tier+'.json.gz');oracle=Oracle(fixture);wanted=expected(oracle);actual={label:snapshot('jac_lx_'+tier+'_20261020',graph)for label,graph in [('conventional',False),('graph',True)]}
  for value in actual.values():assert_expected(value,wanted)
  receipt[tier]={'status':'PASS','expected':wanted,'actual':actual,'fixture':str(fixture)};(out/'summary.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(out)
