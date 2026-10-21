#!/usr/bin/env python3
"""Wait for bounded collectors, verify retained states, publish primary RTT indexes."""
import argparse,json,pathlib,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--matrix',type=pathlib.Path,required=True);p.add_argument('--references',type=pathlib.Path,required=True);a=p.parse_args();deadline=time.monotonic()+14400
while True:
 try:
  m=json.loads((a.matrix/'normalized-rtt-latency.json').read_text());r=json.loads((a.references/'rtt-reference-900-index.json').read_text())['rows']
  if len(m)==126 and len(r)==6:break
 except(FileNotFoundError,json.JSONDecodeError):pass
 assert time.monotonic()<deadline,'Collectors did not finish within bounded four-hour publication window';time.sleep(5)
subprocess.run([sys.executable,str(D/'verify_references.py'),str(a.references)],check=True)
subprocess.run([sys.executable,str(D/'publish.py'),'--matrix',str(a.matrix),'--references',str(a.references)],check=True)
print('TPC primary RTT publication complete',flush=True)
