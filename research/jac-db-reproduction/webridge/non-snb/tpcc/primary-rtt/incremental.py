#!/usr/bin/env python3
"""Lightweight publication only; actual measurement programs remain frozen."""
import json,pathlib,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent;p=pathlib.Path(sys.argv[1]);deadline=time.monotonic()+14400;previous=None
while time.monotonic()<deadline:
 try:
  content=p.read_bytes();rows=json.loads(content)
  if content!=previous:
   subprocess.run([sys.executable,str(D/'publish.py'),'--matrix',str(p.parent),'--allow-incomplete'],check=True);previous=content
  if len(rows)==126:break
 except(FileNotFoundError,json.JSONDecodeError):pass
 time.sleep(5)
