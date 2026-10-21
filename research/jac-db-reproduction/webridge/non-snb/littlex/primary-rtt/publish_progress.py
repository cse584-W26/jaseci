#!/usr/bin/env python3
"""Publish completed primary groups without touching active request files."""
import json,pathlib,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;root=H/'complete-final';summary=root/'matrix/summary.json';last=None
while True:
 status=json.loads((root/'status.json').read_text())
 if summary.exists()and summary.stat().st_mtime_ns!=last:
  before=summary.stat().st_mtime_ns
  r=subprocess.run([sys.executable,str(H/'finish.py'),'--summary',str(summary),'--allow-incomplete'],capture_output=True,text=True)
  (root/'publication.json').write_text(json.dumps({'wall_ns':time.time_ns(),'source_summary':str(summary),'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2)+'\n')
  if r.returncode:raise SystemExit(r.returncode)
  last=before
 if status['status']!='running':break
 time.sleep(30)
