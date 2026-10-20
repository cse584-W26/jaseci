#!/usr/bin/env python3
"""Read the original engine graph without modifying it; audit inputs and row dependencies."""
import argparse,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('graph',type=pathlib.Path);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();raw=a.graph.read_bytes();nodes=json.loads(raw)
def leaves(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if k=='_exp' and isinstance(v,str):yield v
   else:yield from leaves(v)
 elif isinstance(x,list):
  for v in x:yield from leaves(v)
report=dict(graph=str(a.graph.resolve()),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),sql_nodes=len(nodes),nodes=[])
for n in nodes:
 params=list(leaves(n.get('parameterExprs',[])));pcs=list(leaves(n.get('pathCondition',[])))
 report['nodes'].append(dict(sql_id=n['sqlId'],connection=n.get('connNo'),sql=n['sqlTemplate'],txn=n.get('isTxnControl'),rows=n.get('rowCount'),parameter_symbols=sorted(set(v for v in params if not v.startswith('Y_'))),parameter_constants=sorted(set(v for v in params if v.startswith('Y_'))),row_derived_parameter_symbols=sorted(set(v for v in params if 'RS_' in v)),request_parameter_symbols=sorted(set(v for v in params if 'REQUEST_PARAM_' in v)),path_condition_count=len(n.get('pathCondition',[])),path_symbols=sorted(set(v for v in pcs if 'REQUEST_PARAM_' in v or 'RS_' in v))))
report['request_symbols_in_params']=sorted(set(v for n in report['nodes'] for v in n['request_parameter_symbols']))
report['row_symbols_in_params']=sorted(set(v for n in report['nodes'] for v in n['row_derived_parameter_symbols']))
report['connection_numbers']=sorted(set(n['connection'] for n in report['nodes']))
a.out.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('nodes','row_symbols_in_params')},indent=2))
